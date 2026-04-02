"""
data_generation.py
------------------
Continuously generates synthetic real-time sensor data for 5 Caterpillar
machine types (Excavator, Articulated Truck, Backhoe Loader, Dozer,
Crawler Loader), simulating 14 parameters across 4 component groups.

Data is appended to `synthetic_machine_data.csv` every second.
Every 15 seconds an intentional threshold breach is injected to simulate
a real fault event for the ML model to learn from.

Run with:
    python data_generation.py
Stop with Ctrl+C.
"""

import time
from datetime import datetime

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MACHINES = [
    "Excavator",
    "Articulated_Truck",
    "Backhoe_Loader",
    "Dozer",
    "Crawler_Loader",
]

COMPONENTS = {
    "Engine": ["Engine Oil Pressure", "Engine Temperature", "Engine Speed"],
    "Fuel": ["Water Fuel", "Fuel Temperature", "Fuel Level", "Fuel Pressure"],
    "Drive": ["Brake Control", "Pedal Sensor", "Transmission Pressure"],
    "Misc": [
        "Air Filter Pressure Drop",
        "System Voltage",
        "Exhaust Gas Temperature",
        "Hydraulic Pump Rate",
    ],
}

# Normal operating thresholds  (keys match parameter names exactly)
THRESHOLDS = {
    "Engine Oil Pressure":    {"low": 25,   "high": 65},
    "Engine Temperature":     {"high": 105},
    "Engine Speed":           {"high": 1800},
    "Brake Control":          {"low": 1},
    "Transmission Pressure":  {"low": 200,  "high": 450},
    "Pedal Sensor":           {"high": 4.7},
    "Water Fuel":             {"high": 1800},
    "Fuel Level":             {"low": 1},
    "Fuel Pressure":          {"low": 35,   "high": 65},
    "Fuel Temperature":       {"high": 400},
    "System Voltage":         {"low": 12.0, "high": 15.0},
    "Exhaust Gas Temperature":{"high": 365},
    "Hydraulic Pump Rate":    {"high": 125},
    "Air Filter Pressure Drop":{"low": 20},
}

# Starting values for each parameter
INITIAL_VALUES = {
    "Engine Oil Pressure":     50.0,
    "Engine Temperature":      90.0,
    "Engine Speed":          1200.0,
    "Brake Control":            2.0,
    "Transmission Pressure":  300.0,
    "Pedal Sensor":             3.5,
    "Water Fuel":              10.0,
    "Fuel Level":              50.0,
    "Fuel Pressure":           50.0,
    "Fuel Temperature":       100.0,
    "System Voltage":          13.5,
    "Exhaust Gas Temperature": 200.0,
    "Hydraulic Pump Rate":    100.0,
    "Air Filter Pressure Drop": 25.0,
}

# Maximum random-walk step size per second for each parameter
RATE_OF_CHANGE = {
    "Engine Oil Pressure":      0.1,
    "Engine Temperature":       0.5,
    "Engine Speed":            10.0,
    "Brake Control":            0.05,
    "Transmission Pressure":    2.0,
    "Pedal Sensor":             0.02,
    "Water Fuel":               5.0,
    "Fuel Level":              -0.1,   # Fuel decreases over time
    "Fuel Pressure":            0.1,
    "Fuel Temperature":         0.5,
    "System Voltage":           0.01,
    "Exhaust Gas Temperature":  1.0,
    "Hydraulic Pump Rate":      1.0,
    "Air Filter Pressure Drop": 0.1,
}

OUTPUT_FILE = "synthetic_machine_data.csv"


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def generate_value(parameter: str, current_value: float,
                   rate: float, intentional_failure: bool) -> float:
    """
    Compute the next sensor reading.

    Normal mode  → bounded random walk (stays within safe range).
    Failure mode → forces the value past a threshold boundary.
    """
    thresh = THRESHOLDS.get(parameter, {})

    if intentional_failure and thresh:
        if "high" in thresh and current_value < thresh["high"]:
            return thresh["high"] + np.random.uniform(0.1, 10)
        if "low" in thresh and current_value > thresh["low"]:
            return thresh["low"] - np.random.uniform(0.1, 10)

    # Bounded random walk — bounce back if a limit is reached
    if "low" in thresh and current_value <= thresh["low"]:
        current_value += abs(rate) * np.random.rand()
    elif "high" in thresh and current_value >= thresh["high"]:
        current_value -= abs(rate) * np.random.rand()
    else:
        current_value += rate * (np.random.rand() - 0.5)

    return max(current_value, 0.0)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    start_time = datetime.utcnow()
    id_counter = 1

    # Write CSV header once
    pd.DataFrame(columns=["Id", "Time", "Machine", "Component", "Parameter", "Value"]).to_csv(
        OUTPUT_FILE, index=False
    )
    print(f"Data generation started. Writing to '{OUTPUT_FILE}'. Press Ctrl+C to stop.")

    try:
        while True:
            current_time = datetime.utcnow()
            elapsed_seconds = int((current_time - start_time).total_seconds())
            intentional_failure = (elapsed_seconds % 15 == 0)

            batch = []
            for machine in MACHINES:
                for component, params in COMPONENTS.items():
                    for param in params:
                        new_value = generate_value(
                            param, INITIAL_VALUES[param],
                            RATE_OF_CHANGE[param], intentional_failure
                        )
                        INITIAL_VALUES[param] = new_value
                        batch.append({
                            "Id":        id_counter,
                            "Time":      current_time.isoformat() + "Z",
                            "Machine":   machine + "_1",
                            "Component": component,
                            "Parameter": param,
                            "Value":     round(new_value, 2),
                        })
                        id_counter += 1

            pd.DataFrame(batch).to_csv(OUTPUT_FILE, mode="a", header=False, index=False)
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\nData generation stopped. {id_counter - 1} records written to '{OUTPUT_FILE}'.")


if __name__ == "__main__":
    main()
