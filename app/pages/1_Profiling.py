import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pandas as pd
import streamlit as st

from app.state import init_session, require_active_dataset
from app.theme import init_page, page_header, kpi_card_html, kpi_row

init_page("Profiling", icon="🔍")
init_session()
state = require_active_dataset()

page_header(f"Data Profiling — {state.filename}", "Dataset- and column-level statistics.", icon="🔍")

p = state.profile
kpi_row([
    kpi_card_html("Rows", f"{p.rows:,}"),
    kpi_card_html("Columns", str(p.columns)),
    kpi_card_html("Memory", f"{p.memory_bytes / 1024:.1f} KB"),
    kpi_card_html("Duplicate Rows", str(p.duplicate_rows), "flag" if p.duplicate_rows else "none",
                  "warning" if p.duplicate_rows else "good"),
    kpi_card_html("Missing Cells", f"{p.missing_cells:,}", f"{p.missing_pct}% of cells",
                  "warning" if p.missing_pct > 5 else "good"),
])

with st.container(border=True):
    st.markdown("**Column type breakdown**")
    type_counts = {
        "Numeric": len(p.numeric_columns), "Categorical/Text": len(p.categorical_columns),
        "Datetime": len(p.datetime_columns), "Boolean": len(p.boolean_columns),
        "Identifier": len(p.identifier_columns),
    }
    st.bar_chart(pd.Series(type_counts))

st.subheader("Column-level profile")
rows = []
for name, cp in p.column_profiles.items():
    rows.append({
        "Column": name, "Type": cp.inferred_type, "Dtype": cp.dtype,
        "Nulls": cp.null_count, "Null %": cp.null_pct, "Unique": cp.unique_count,
        "Uniqueness Ratio": cp.uniqueness_ratio, "Cardinality": cp.cardinality,
        "Min": str(cp.min) if cp.min is not None else None,
        "Max": str(cp.max) if cp.max is not None else None,
        "Mean": cp.mean, "Median": cp.median, "Std": cp.std,
        "Outliers": cp.outlier_count, "Suspicious Values": cp.suspicious_value_count,
    })
df_profile = pd.DataFrame(rows)
st.dataframe(df_profile, use_container_width=True, hide_index=True)

st.subheader("Raw data preview")
st.dataframe(state.current_df.head(100), use_container_width=True)

selected_col = st.selectbox("Inspect a column's top values (categorical only)",
                             ["—"] + p.categorical_columns)
if selected_col != "—":
    cp = p.column_profiles[selected_col]
    if cp.top_values:
        with st.container(border=True):
            st.bar_chart(pd.Series(cp.top_values))
    else:
        st.write("No top-value summary available for this column.")
