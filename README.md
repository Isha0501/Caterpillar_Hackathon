# 🚜 Caterpillar Machine Health Monitoring System

> A real-time predictive maintenance dashboard built during a **24-hour hackathon hosted by Caterpillar Inc.** in 2024.

---

## 🏆 About This Project

This project was built by a **team of 4** during a 24-hour hackathon organised by **Caterpillar Inc.** while we were pursuing our B.Tech at **VIT Vellore** (2024).

Our solution monitors the health of Caterpillar heavy construction equipment in real time — detecting anomalies across 14 sensor parameters, predicting risk levels using machine learning, and triggering SMS alerts when thresholds are breached.

We were among the **recognised teams at the end of the hackathon**, which earned us an opportunity to interview with Caterpillar for potential internship and full-time roles.

---

## 📸 Screenshots

<table>
  <tr>
    <td align="center"><b>Live Dashboard</b></td>
    <td align="center"><b>SMS Alerts</b></td>
    <td align="center"><b>Synthetic Data Sample</b></td>
  </tr>
  <tr>
    <td><img src="assets/Dashboard.jpg" width="320"/></td>
    <td><img src="assets/SMS_Alerts.jpg" width="320"/></td>
    <td><img src="assets/Synthetic_Data_Example.jpg" width="320"/></td>
  </tr>
</table>

---

## 🧩 System Architecture

```
┌─────────────────────────┐
│   data_generation.py    │  ← Simulates live sensor data every second
│   (Sensor Simulator)    │    for 5 machines × 14 parameters
└────────────┬────────────┘
             │  synthetic_machine_data.csv
             ▼
┌─────────────────────────┐
│       model.py          │  ← XGBoost classifier predicts risk level
│   (Prediction Engine)   │    per data point; fires SMS alerts
└────────────┬────────────┘
             │  ml_predictions.csv
             ▼
┌─────────────────────────┐
│     dashboard.py        │  ← Streamlit dashboard — live charts,
│   (Monitoring UI)       │    threshold overlays, breach alerts
└─────────────────────────┘
```

---

## ✅ What the System Does Well

### Sensor Simulation
The data generator produces realistic, continuous sensor streams using a **bounded random walk** — values drift naturally within safe ranges and are nudged back when they approach a limit. Every 15 seconds an **intentional fault event** is injected (forcing a value past its threshold), giving the model real examples of failures to learn from.

### Machine Learning — 99.61% Accuracy
The XGBoost classifier was evaluated on a held-out 30% test split and achieved **99.61% overall accuracy** across four risk classes:

| Risk Class | Precision | Recall | F1-Score | Support |
|---|---|---|---|---|
| Normal | 98% | 97% | 98% | 396 |
| 🟡 Low Risk | 100% | 100% | 100% | 876 |
| 🟠 Medium Risk | 100% | 100% | 100% | 1,322 |
| 🔴 High Risk | 100% | 100% | 100% | 1,795 |
| **Overall** | **100%** | **100%** | **100%** | **4,389** |

The strong performance reflects the deterministic nature of the risk labels (derived directly from threshold comparisons), which gives the model clean, well-separated decision boundaries. The small number of misclassified rows (~17) are all "Normal" readings sitting right at a threshold edge.

### Real-Time Dashboard
- Separate live line chart per sensor parameter, updated every 5 seconds
- Dashed threshold overlay lines (yellow = Low, red = High) on every chart
- Colour-coded sidebar alerts grouped by machine, showing exactly which parameters are out of range and at what risk level
- Per-machine filtering — switch between all 5 machines with one click
- Auto-refreshes without any page reload using `st.rerun()`

### Graceful Degradation
If Twilio credentials are not configured, the system **does not crash** — it prints alert messages to the console instead, so the full pipeline (data generation → prediction → dashboard) continues to run normally.

---

## ⚙️ Key Features

| Feature | Details |
|---|---|
| **Real-time sensor simulation** | 5 machine types, 14 parameters, 4 component groups |
| **Intentional fault injection** | Every 15 s a threshold breach is injected to stress-test the model |
| **ML-based risk prediction** | XGBoost classifier, 99.61% accuracy, 4 risk classes |
| **Threshold reference table** | `Threshold.csv` defines safe operating ranges for every parameter |
| **SMS alerting** | Optional Twilio integration — gracefully skipped if not configured |
| **Live Streamlit dashboard** | Auto-refreshes every 5 s; interactive Plotly charts per parameter |
| **Per-machine filtering** | Sidebar navigation to switch between the 5 machines |

---

## 🏗️ Machine & Parameter Coverage

**Machines:** Excavator · Articulated Truck · Backhoe Loader · Dozer · Crawler Loader

| Component | Parameters |
|---|---|
| **Engine** | Engine Oil Pressure · Engine Temperature · Engine Speed |
| **Fuel** | Water Fuel · Fuel Temperature · Fuel Level · Fuel Pressure |
| **Drive** | Brake Control · Pedal Sensor · Transmission Pressure |
| **Misc** | Air Filter Pressure Drop · System Voltage · Exhaust Gas Temperature · Hydraulic Pump Rate |

**Risk Levels:**

| Level | Encoded Value | Meaning |
|---|---|---|
| Normal | 1 | All parameters within safe range |
| 🟡 Low | 2 | Minor threshold breach |
| 🟠 Medium | 3 | Moderate threshold breach |
| 🔴 High | 4 | Critical threshold breach — immediate attention required |

---

## 🚀 Setup & Running

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the data simulator (Terminal 1)

```bash
python data_generation.py
```

Writes sensor readings to `synthetic_machine_data.csv` every second.
Press `Ctrl+C` to stop.

### 3. Run the prediction engine (Terminal 2)

```bash
python model.py
```

Reads the sensor CSV, trains XGBoost, writes predictions to `ml_predictions.csv` every 5 seconds.

### 4. Launch the dashboard (Terminal 3)

```bash
streamlit run dashboard.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

> **Tip:** Pre-generated sample data (`synthetic_machine_data.csv` and `ml_predictions.csv`) is already committed to this repo so you can launch the dashboard immediately without running the other two scripts first.

---

## 📲 SMS Alerts (Twilio) — Optional

The system can send SMS alerts when risk breach counts exceed defined limits. This requires a [Twilio](https://www.twilio.com/) account.

> **⚠️ Disclaimer:** Twilio is a third-party paid SMS service. Free trial accounts come with usage restrictions (e.g. you can only send messages to verified phone numbers and a Twilio trial message prefix is added). Real-world deployment would require a paid Twilio plan. The system is fully functional without Twilio configured — alerts are printed to the terminal instead.

To enable SMS alerts, set the following environment variables before running `model.py`:

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token"
export TWILIO_NUMBER="+1xxxxxxxxxx"       # your Twilio phone number
export RECIPIENT_NUMBER="+91xxxxxxxxxx"   # destination number
```

If any of these are missing, `model.py` will log the alert to the console and continue running — **no crash, no configuration required** for the rest of the pipeline.

---

## 📁 File Structure

```
Caterpillar_Hackathon/
├── data_generation.py         # Sensor data simulator
├── model.py                   # XGBoost risk prediction + optional SMS alerts
├── dashboard.py               # Streamlit monitoring dashboard
│
├── Threshold.csv              # Safe operating ranges for each parameter
├── threshold_limits_clean.csv # Parsed threshold table (auto-generated by model.py)
├── synthetic_machine_data.csv # Sample generated sensor data
├── ml_predictions.csv         # Sample model predictions
├── Data.csv                   # Additional reference data
│
├── assets/
│   ├── Dashboard.jpg
│   ├── SMS_Alerts.jpg
│   └── Synthetic_Data_Example.jpg
│
├── requirements.txt
└── .gitignore
```

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **pandas & NumPy** — data processing and sensor simulation
- **scikit-learn** — train/test split and evaluation metrics
- **XGBoost** — gradient-boosted risk classification (99.61% accuracy)
- **Streamlit** — real-time monitoring dashboard with auto-refresh
- **Plotly** — interactive sensor charts with threshold overlays
- **Twilio** *(optional)* — SMS alerting for threshold breaches

---

## 👥 Team

Built by a team of 4 B.Tech students from **VIT Vellore** during the Caterpillar Inc. hackathon, 2024.

---

## 📄 License

This project was created for hackathon purposes and is shared here for portfolio and educational use.
