"""Quick end-to-end smoke test of the core pipeline (not a pytest suite)."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dqi_core.ingestion import load_file
from dqi_core.profiling import profile_dataset
from dqi_core.quality.pillars import assess_all_pillars
from dqi_core.issues.detection import detect_all_issues
from dqi_core.impact.scoring import score_issues
from dqi_core.impact.ranking import build_rankings
from dqi_core.impact.stats import compute_rank_correlation
from dqi_core.health import compute_health_index
from dqi_core.rca import analyze_all
from dqi_core.business_impact import estimate_exposure, total_exposure
from dqi_core.governance.pii import detect_pii
from dqi_core.governance.contracts import load_contract, validate_against_contract
from dqi_core.remediation.engine import RemediationSession
from dqi_core.remediation.validation import build_validation_report

path = "data/sample/retail_sample.csv"
result = load_file(path)
assert result.ok, result.error
df = result.dataframe
print(f"Loaded {df.shape[0]} rows, {df.shape[1]} cols. Warnings: {result.warnings}")

profile = profile_dataset(df, filename="retail_sample.csv")
print(f"Profile: missing_pct={profile.missing_pct}, duplicate_rows={profile.duplicate_rows}")

issues = detect_all_issues(df, profile)
print(f"Detected {len(issues)} issues")

pillars = assess_all_pillars(df, profile, issues)
for name, p in pillars.items():
    print(f"  Pillar {name}: score={p.score} severity={p.severity} limitation={p.limitation}")

health = compute_health_index(pillars)
print(f"Health index: {health.overall} ({health.band}) weakest={health.weakest}")

issues = score_issues(issues, total_rows=len(df), critical_columns=["unit_price", "quantity", "order_id"],
                       revenue_per_record=0.0)
ranking_df = build_rankings(issues)
print(ranking_df[["issue_type", "column", "affected_records", "frequency_rank", "impact_rank", "rank_change", "impact_score"]].head(10).to_string())

corr = compute_rank_correlation(ranking_df)
print(f"Spearman rs={corr.spearman_rs} p={corr.spearman_p}  Kendall tau={corr.kendall_tau} p={corr.kendall_p}")
print(corr.interpretation)

rca_results = analyze_all(issues[:3])
for r in rca_results:
    print(f"RCA {r.issue_id}: probable_source={r.probable_source}")

exposures = estimate_exposure(issues, total_rows=len(df), revenue_per_record=25.0)
print("Total exposure:", total_exposure(exposures))

pii = detect_pii(df)
for p in pii:
    print(f"PII: column={p.column} pattern={p.pattern} count={p.match_count}")

contract = load_contract("contracts/retail_sample_contract.yaml")
contract_result = validate_against_contract(df, contract, "retail_sample_contract")
print(f"Contract status: {contract_result.deployment_status}, {len(contract_result.violations)} violations")

session = RemediationSession(df)
session.remove_duplicate_rows()
session.handle_missing("customer_email", "constant", constant="unknown@example.com")
session.handle_invalid_numeric("unit_price", "zero", "replace")
print(f"Remediation audit entries: {len(session.audit_trail)}")

profile_after = profile_dataset(session.current_df, filename="retail_sample_remediated.csv")
issues_after = detect_all_issues(session.current_df, profile_after)
pillars_after = assess_all_pillars(session.current_df, profile_after, issues_after)
health_after = compute_health_index(pillars_after)
print(f"Health after remediation: {health_after.overall} (was {health.overall})")

val_report = build_validation_report(df, session.current_df, health.overall, health_after.overall,
                                      len(issues), len(issues_after), profile.numeric_columns)
for ks in val_report.ks_results:
    print(f"KS test {ks.column}: stat={ks.statistic} p={ks.p_value} -> {ks.interpretation}")

print("SMOKE TEST PASSED")
