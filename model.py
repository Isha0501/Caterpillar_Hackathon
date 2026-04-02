"""
model.py
--------
Reads live sensor data from `synthetic_machine_data.csv`, trains an
XGBoost classifier to predict risk levels (Low / Medium / High), and
optionally sends SMS alerts via Twilio when breach counts exceed limits.

Risk encoding:
    1 → Normal (within all thresholds)
    2 → Low risk
    3 → Medium risk
    4 → High risk

Predictions are written to `ml_predictions.csv` every cycle.

Run with:
    python model.py
Stop with Ctrl+C.

SMS alerts (optional):
    Set the environment variables below (or a .env file) before running:
        TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN,
        TWILIO_NUMBER, RECIPIENT_NUMBER
"""

import os
import re
import time

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Twilio SMS (optional) — set env vars; alerts are skipped if not configured
# ---------------------------------------------------------------------------
try:
    from twilio.rest import Client as TwilioClient
    _TWILIO_AVAILABLE = True
except ImportError:
    _TWILIO_AVAILABLE = False

ACCOUNT_SID      = os.getenv("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN       = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_NUMBER    = os.getenv("TWILIO_NUMBER", "")
RECIPIENT_NUMBER = os.getenv("RECIPIENT_NUMBER", "")

# ---------------------------------------------------------------------------
# File paths
# ---------------------------------------------------------------------------
THRESHOLD_FILE   = "Threshold.csv"
SENSOR_DATA_FILE = "synthetic_machine_data.csv"
PREDICTIONS_FILE = "ml_predictions.csv"

# Risk encoding applied to Probability of Failure labels
RISK_ENCODING = {"Low": 2, "Medium": 3, "High": 4}

# ---------------------------------------------------------------------------
# Threshold helpers
# ---------------------------------------------------------------------------

def extract_thresholds(threshold_str: str):
    """
    Parse a human-readable threshold string such as:
        "Low 25, High 65"  →  ('25', '65')
        "High 105"         →  (None, '105')
        "Low 1"            →  ('1',  None)
    """
    low_threshold = high_threshold = None

    if "Low" in threshold_str:
        low_part = threshold_str.split("Low")[1].split(",")[0].strip()
        m = re.match(r"[\d.]+", low_part)
        if m:
            low_threshold = m.group(0)

    if "High" in threshold_str:
        high_part = threshold_str.split("High")[1].strip()
        m = re.match(r"[\d.]+", high_part)
        if m:
            high_threshold = m.group(0)

    return low_threshold, high_threshold


def load_thresholds(path: str) -> pd.DataFrame:
    """Load and parse the threshold reference table."""
    df = pd.read_csv(path)
    df[["Low Threshold", "High Threshold"]] = df["Treshold"].apply(
        lambda x: pd.Series(extract_thresholds(x))
    )
    df = df.drop(columns=["Treshold"])
    df["Probability of Failure"] = df["Probability of Failure"].map(RISK_ENCODING)
    return df


# ---------------------------------------------------------------------------
# Risk calculation
# ---------------------------------------------------------------------------

def calculate_risk(row) -> int:
    """
    Return the encoded risk level when the sensor value is outside its
    safe range, or 1 (Normal) otherwise.
    """
    value = row["Value"]

    try:
        low  = float(row["Low Threshold"])  if pd.notna(row["Low Threshold"])  else float("inf")
    except (ValueError, TypeError):
        low  = float("inf")

    try:
        high = float(row["High Threshold"]) if pd.notna(row["High Threshold"]) else float("-inf")
    except (ValueError, TypeError):
        high = float("-inf")

    if value < low or value > high:
        return int(row["Probability of Failure"])
    return 1


# ---------------------------------------------------------------------------
# SMS alert
# ---------------------------------------------------------------------------

def send_sms(message: str) -> None:
    """Send an SMS alert. Silently skips if Twilio is not configured."""
    if not _TWILIO_AVAILABLE:
        print(f"[SMS SKIPPED — twilio not installed]: {message}")
        return
    if not all([ACCOUNT_SID, AUTH_TOKEN, TWILIO_NUMBER, RECIPIENT_NUMBER]):
        print(f"[SMS SKIPPED — Twilio env vars not set]: {message}")
        return
    try:
        client = TwilioClient(ACCOUNT_SID, AUTH_TOKEN)
        client.messages.create(body=message, from_=TWILIO_NUMBER, to=RECIPIENT_NUMBER)
        print(f"SMS sent to {RECIPIENT_NUMBER}")
    except Exception as exc:
        print(f"[SMS ERROR]: {exc}")


# ---------------------------------------------------------------------------
# Main prediction pipeline
# ---------------------------------------------------------------------------

def process_data_and_predict(threshold_limits: pd.DataFrame) -> None:
    """
    1. Load latest sensor data.
    2. Assign risk labels via threshold lookup.
    3. Train XGBoost on 70 % of data.
    4. Predict risk for the remaining 30 %.
    5. Trigger SMS alerts if breach counts exceed limits.
    6. Write predictions to CSV.
    """
    dataset = pd.read_csv(SENSOR_DATA_FILE)

    # Use the raw Parameter name — matches Threshold.csv exactly
    dataset["New_Parameter"] = dataset["Parameter"]

    df_train, df_test = train_test_split(dataset, test_size=0.3, random_state=42)

    # --- Build training labels via threshold lookup ---
    df_train = df_train.drop(columns=["Component", "Parameter"])
    merged = pd.merge(
        df_train, threshold_limits,
        left_on="New_Parameter", right_on="Parameter",
        how="left",
    )
    merged["Risk"] = merged.apply(calculate_risk, axis=1)
    df_train = merged.drop(columns=["Parameter", "Probability of Failure",
                                    "Low Threshold", "High Threshold"])

    X_train = df_train.drop(columns=["Risk"])
    y_train = df_train["Risk"].fillna(1).astype(int)   # default to Normal if unmatched

    # --- Prepare test features (same column drops as training) ---
    X_test = df_test.drop(columns=["Component", "Parameter"]).copy()

    # Convert timestamps
    X_train["Time"] = pd.to_datetime(X_train["Time"])
    X_test["Time"]  = pd.to_datetime(X_test["Time"])

    # One-hot encode categorical columns
    X_train = pd.get_dummies(X_train, columns=["Machine", "New_Parameter"])
    X_test  = pd.get_dummies(X_test,  columns=["Machine", "New_Parameter"])

    # Align feature sets (test gets exactly the same columns as train)
    X_train, X_test = X_train.align(X_test, join="left", axis=1, fill_value=0)

    # --- Train & predict ---
    # XGBoost requires 0-indexed labels; shift 1-4 → 0-3 before fit, restore after
    y_train_xgb = y_train - 1
    model = XGBClassifier(n_estimators=100, random_state=42, eval_metric="mlogloss")
    model.fit(X_train.drop(columns=["Time"]), y_train_xgb)

    predictions = model.predict(X_test.drop(columns=["Time"])) + 1  # restore 0-3 → 1-4
    df_test = df_test.copy()
    df_test["Risk"] = predictions
    df_test = df_test.sort_values(by="Time")

    # --- SMS alerts based on risk distribution ---
    count_high   = (df_test["Risk"] == 4).sum()
    count_medium = (df_test["Risk"] == 3).sum()
    count_low    = (df_test["Risk"] == 2).sum()

    if count_low >= 200:
        send_sms(
            "⚠️ Caterpillar Alert — Low-Level Risk Detected! "
            "Details: https://www.youtube.com/watch?v=QNzaDCCyTGE"
        )
    if count_medium >= 350:
        send_sms(
            "⚠️ Caterpillar Alert — Medium-Level Risk Detected! "
            "Contact support: 000-800-100-1647"
        )
    if count_high > 150:
        send_sms(
            "🚨 Caterpillar Alert — High-Level Risk Detected! "
            "Schedule service: https://www.cat.com/en_IN/support/contact-us.html"
        )

    df_test.to_csv(PREDICTIONS_FILE, index=False)
    print(
        f"Predictions updated → {PREDICTIONS_FILE}  "
        f"[High: {count_high}, Medium: {count_medium}, Low: {count_low}]"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Loading threshold configuration...")
    threshold_limits = load_thresholds(THRESHOLD_FILE)
    # Persist cleaned thresholds for dashboard use
    threshold_limits.to_csv("threshold_limits_clean.csv", index=False)

    print("Starting prediction loop. Press Ctrl+C to stop.\n")
    try:
        while True:
            process_data_and_predict(threshold_limits)
            print("Waiting for new data...")
            time.sleep(5)
    except KeyboardInterrupt:
        print("\nPrediction stopped.")


if __name__ == "__main__":
    main()
