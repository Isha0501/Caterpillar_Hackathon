"""
dashboard.py
------------
Streamlit real-time monitoring dashboard for Caterpillar machine health.

Reads predictions from `ml_predictions.csv` and `threshold_limits_clean.csv`,
displays a live line chart per sensor parameter (2 charts per row), and
shows colour-coded threshold breach alerts in the sidebar.

The page auto-refreshes every 5 seconds to reflect the latest predictions.

Run with:
    streamlit run dashboard.py
"""

import time

import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="CAT Machine Risk Monitor",
    page_icon="🚜",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

@st.cache_data(ttl=5)   # re-read CSVs at most every 5 s
def load_data():
    df       = pd.read_csv("ml_predictions.csv")
    df_thresh = pd.read_csv("threshold_limits_clean.csv")
    df["Time"] = pd.to_datetime(df["Time"], utc=True)
    return df, df_thresh


df, df_thresh = load_data()

# ---------------------------------------------------------------------------
# Sidebar — machine selector
# ---------------------------------------------------------------------------
st.sidebar.title("🚜 CAT Risk Monitor")
st.sidebar.markdown("---")
st.sidebar.markdown("### Select Machine")

machines = list(pd.unique(df["Machine"]))

if "selected_machine" not in st.session_state:
    st.session_state.selected_machine = machines[0]

for machine in machines:
    if st.sidebar.button(machine, key=f"btn_{machine}"):
        st.session_state.selected_machine = machine

st.sidebar.markdown("---")
alert_placeholder = st.sidebar.container()

# ---------------------------------------------------------------------------
# Main content header
# ---------------------------------------------------------------------------
st.title(f"📊 Machine: {st.session_state.selected_machine}")
st.caption("Charts show the latest 10 sensor readings. Dashed lines mark safe-range thresholds.")
st.markdown("---")

# ---------------------------------------------------------------------------
# Filter data for selected machine
# ---------------------------------------------------------------------------
filtered_df = df[df["Machine"] == st.session_state.selected_machine].sort_values("Time")
parameters  = list(pd.unique(filtered_df["Parameter"]))

# ---------------------------------------------------------------------------
# Risk-level helpers
# ---------------------------------------------------------------------------

def get_risk_display(risk_level: int) -> tuple[str, str]:
    """Return (label, hex-colour) for a numeric risk level."""
    return {
        2: ("Low",    "#f0c040"),
        3: ("Medium", "#f08030"),
        4: ("High",   "#e03030"),
    }.get(risk_level, ("Normal", "#40c080"))


def get_thresholds(param: str) -> tuple:
    """Return (low_thresh, high_thresh, risk_level) for a parameter, or (None, None, None)."""
    row = df_thresh[df_thresh["Parameter"] == param]
    if row.empty:
        return None, None, None
    low  = row["Low Threshold"].values[0]
    high = row["High Threshold"].values[0]
    risk = row["Probability of Failure"].values[0]
    return (
        float(low)  if pd.notna(low)  else None,
        float(high) if pd.notna(high) else None,
        int(risk)   if pd.notna(risk) else None,
    )


# ---------------------------------------------------------------------------
# Build charts (pairs of parameters per row)
# ---------------------------------------------------------------------------
alerts: dict[str, str] = {}

num_rows = (len(parameters) + 1) // 2   # ceiling division

for row_idx in range(num_rows):
    col1, col2 = st.columns(2)

    for col_idx, col in enumerate([col1, col2]):
        param_idx = row_idx * 2 + col_idx
        if param_idx >= len(parameters):
            break

        param = parameters[param_idx]
        param_df = filtered_df[filtered_df["Parameter"] == param].tail(10)

        with col:
            if param_df.empty:
                st.info(f"No data yet for **{param}**.")
                continue

            low_thresh, high_thresh, risk_level = get_thresholds(param)

            fig = px.line(
                param_df, x="Time", y="Value",
                title=f"{param}",
                height=300,
                color_discrete_sequence=["#1f77b4"],
            )
            fig.update_xaxes(tickformat="%H:%M:%S", tickangle=45, title=None)
            fig.update_yaxes(title="Value")
            fig.update_layout(margin=dict(t=40, b=10, l=10, r=10))

            # Dynamic y-axis so threshold lines are always visible
            values = param_df["Value"]
            y_min = min(low_thresh  if low_thresh  is not None else values.min(), values.min())
            y_max = max(high_thresh if high_thresh is not None else values.max(), values.max())
            padding = max(0.05 * abs(y_max - y_min), 1.0)
            fig.update_yaxes(range=[y_min - padding, y_max + padding])

            if low_thresh is not None:
                fig.add_hline(
                    y=low_thresh, line_dash="dash", line_color="gold",
                    annotation_text="Low Threshold", annotation_position="top left",
                )
            if high_thresh is not None:
                fig.add_hline(
                    y=high_thresh, line_dash="dash", line_color="tomato",
                    annotation_text="High Threshold", annotation_position="bottom left",
                )

            st.plotly_chart(fig, use_container_width=True)

            # Build sidebar alerts
            if risk_level is not None:
                risk_label, color = get_risk_display(risk_level)
                if low_thresh is not None and values.min() < low_thresh:
                    alerts[param] = (
                        f"<span style='color:{color}; font-weight:bold;'>"
                        f"⚠️ {param}: below Low Threshold — {risk_label} Risk"
                        f"</span>"
                    )
                elif high_thresh is not None and values.max() > high_thresh:
                    alerts[param] = (
                        f"<span style='color:{color}; font-weight:bold;'>"
                        f"🚨 {param}: above High Threshold — {risk_label} Risk"
                        f"</span>"
                    )

# ---------------------------------------------------------------------------
# Sidebar alerts (newest first)
# ---------------------------------------------------------------------------
with alert_placeholder:
    if alerts:
        st.markdown("### ⚠️ Active Alerts")
        for msg in reversed(list(alerts.values())):
            st.markdown(msg, unsafe_allow_html=True)
    else:
        st.markdown("### ✅ All Parameters Normal")

# ---------------------------------------------------------------------------
# Auto-refresh every 5 seconds
# ---------------------------------------------------------------------------
time.sleep(5)
st.rerun()
