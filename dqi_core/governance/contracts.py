"""Local data-contract (schema) validation against a YAML/JSON contract file.

No external CI/CD or GitHub dependency — this validates a dataframe against
a contract spec entirely locally, as required by the project rules.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import yaml

def _is_integer_like(s: pd.Series) -> bool:
    numeric = pd.to_numeric(s, errors="coerce").dropna()
    if numeric.empty:
        return False
    return bool((numeric % 1 == 0).all())


_TYPE_CHECKS = {
    "string": lambda s: True,  # anything can be a string
    "integer": _is_integer_like,
    "float": lambda s: pd.to_numeric(s, errors="coerce").notna().any(),
    "boolean": lambda s: s.dropna().isin([True, False, "true", "false", "True", "False", 0, 1]).all(),
    "date": lambda s: pd.to_datetime(s, errors="coerce").notna().mean() > 0.9,
}


@dataclass
class ContractViolation:
    column: Optional[str]
    rule: str
    severity: str
    affected_rows: int
    message: str
    blocking: bool


@dataclass
class ContractValidationResult:
    contract_name: str
    passed: bool
    violations: list = field(default_factory=list)
    deployment_status: str = "PASS"

    def to_dict(self) -> dict:
        return {
            "contract_name": self.contract_name, "passed": self.passed,
            "deployment_status": self.deployment_status,
            "violations": [v.__dict__ for v in self.violations],
        }


def load_contract(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)
    if not contract or "columns" not in contract:
        raise ValueError("Contract file must define a top-level 'columns' mapping.")
    return contract


def validate_against_contract(df: pd.DataFrame, contract: dict, contract_name: str = "contract") -> ContractValidationResult:
    violations = []
    n = len(df)
    columns_spec = contract.get("columns", {})

    for col_name, spec in columns_spec.items():
        if col_name not in df.columns:
            if not spec.get("nullable", True):
                violations.append(ContractViolation(
                    column=col_name, rule="required_column_missing", severity="Critical",
                    affected_rows=n, message=f"Required column '{col_name}' is missing from the dataset.",
                    blocking=True,
                ))
            continue

        s = df[col_name]

        if not spec.get("nullable", True):
            null_count = int(s.isna().sum())
            if null_count > 0:
                violations.append(ContractViolation(
                    column=col_name, rule="not_nullable", severity="High", affected_rows=null_count,
                    message=f"Column '{col_name}' is marked non-nullable but has {null_count} nulls.",
                    blocking=True,
                ))

        expected_type = spec.get("type")
        if expected_type and expected_type in _TYPE_CHECKS:
            non_null = s.dropna()
            if len(non_null) > 0:
                try:
                    ok = _TYPE_CHECKS[expected_type](non_null)
                except Exception:
                    ok = False
                if not ok:
                    violations.append(ContractViolation(
                        column=col_name, rule="type_mismatch", severity="High", affected_rows=len(non_null),
                        message=f"Column '{col_name}' does not consistently match expected type '{expected_type}'.",
                        blocking=False,
                    ))

        if "min" in spec or "max" in spec:
            numeric = pd.to_numeric(s, errors="coerce")
            lo, hi = spec.get("min"), spec.get("max")
            mask = pd.Series(False, index=s.index)
            if lo is not None:
                mask |= numeric < lo
            if hi is not None:
                mask |= numeric > hi
            bad = int(mask.sum())
            if bad > 0:
                violations.append(ContractViolation(
                    column=col_name, rule="range_violation", severity="Medium", affected_rows=bad,
                    message=f"Column '{col_name}' has {bad} values outside [{lo}, {hi}].",
                    blocking=False,
                ))

        if "allowed_values" in spec:
            allowed = set(spec["allowed_values"])
            non_null = s.dropna()
            bad_mask = ~non_null.isin(allowed)
            bad = int(bad_mask.sum())
            if bad > 0:
                violations.append(ContractViolation(
                    column=col_name, rule="invalid_category", severity="Medium", affected_rows=bad,
                    message=f"Column '{col_name}' has {bad} values outside the allowed set {sorted(allowed)}.",
                    blocking=False,
                ))

    blocking = any(v.blocking for v in violations)
    return ContractValidationResult(
        contract_name=contract_name, passed=len(violations) == 0, violations=violations,
        deployment_status="BLOCKED" if blocking else ("WARN" if violations else "PASS"),
    )
