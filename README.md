# ☁️ AI-Powered Cloud Resource Optimization & Auto-Scaling System

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-1.3+-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![SQLite](https://img.shields.io/badge/SQLite-SQLAlchemy-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

An enterprise-grade, full-stack cloud infrastructure monitoring, machine learning demand forecasting, and cost optimization web application. The system monitors multi-cloud virtual machine resources (CPU, Memory, Disk, Network I/O), predicts future resource demand using Scikit-Learn time-series models, detects compute anomalies, and recommends or automatically scales instances across **AWS**, **Azure**, and **GCP** to minimize cloud waste while maintaining high availability.

---

## 🎯 Objectives & Features

- **Real-Time Telemetry Stream**: Harvests live machine metrics (`psutil`) alongside simulated multi-cloud cluster nodes (AWS EC2, Azure VMs, GCP Compute Engine).
- **Machine Learning Demand Forecasting**:
  - `RandomForestRegressor` & `Ridge` regression models forecasting CPU & RAM demand across **+15m**, **+1h**, **+6h**, and **+24h** horizons.
  - `IsolationForest` anomaly detector flagging DDoS traffic, runaway processes, or memory leaks.
- **Cloud Rightsizing & Cost Optimization**:
  - AWS, Azure, and GCP instance pricing catalog.
  - Heuristics engine generating **Downsizing** (eliminating idle compute waste) and **Upsizing** recommendations.
  - Real-time monthly cloud burn & potential savings calculations.
- **Automated Auto-Scaler**: Auto-scales instance tiers when CPU utilization breaches 88% and logs event history.
- **Glassmorphic Interactive Dashboard**: Dark theme UI built with HTML5, CSS3, Chart.js, and an embedded **CloudOpt AI Assistant Chatbot**.

---

## 🏗️ System Architecture

```
 ┌────────────────────────────────────────────────────────┐
 │            Cloud Telemetry & Monitor Daemon            │
 │ (psutil live host metrics + Multi-Cloud VM simulator)  │
 └──────────────────────────┬─────────────────────────────┘
                            │ (3s Telemetry Ingestion)
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │           SQLite Database (SQLAlchemy ORM)             │
 │   - ResourceData, ServerInstance, ScalerLogs, Users    │
 └──────────────────────────┬─────────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
 ┌───────────────────────────┐ ┌───────────────────────────┐
 │ Machine Learning Pipeline │ │   Optimization Engine     │
 │  - RandomForestForecaster │ │  - Rightsizing Heuristics │
 │  - IsolationForest Anom   │ │  - Cloud Pricing Matrix   │
 └─────────────┬─────────────┘ └─────────────┬─────────────┘
               │                             │
               └────────────┬────────────────┘
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │                 Flask RESTful API                      │
 └──────────────────────────┬─────────────────────────────┘
                            │
                            ▼
 ┌────────────────────────────────────────────────────────┐
 │        Interactive Glassmorphic Web Dashboard          │
 └────────────────────────────────────────────────────────┘
```

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11+, Flask, Flask-CORS, SQLAlchemy ORM, Werkzeug
- **Machine Learning**: Scikit-Learn, Pandas, NumPy, Joblib
- **System Monitoring**: `psutil`
- **Frontend**: HTML5, CSS3 (Vanilla Glassmorphism, CSS Custom Variables), JavaScript ES6+
- **Visualization**: Chart.js

---

## 🚀 Getting Started

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/cloud-resource-optimizer.git
cd cloud-resource-optimizer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
python app.py
```

### 4. Open in Web Browser
Navigate to `http://127.0.0.1:5000` to access the interactive dashboard.

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/metrics/live` | Live telemetry snapshot for all cluster nodes + cost summary |
| `GET` | `/api/metrics/history/<id>` | Historical telemetry points for streaming charts |
| `GET` | `/api/ml/forecast/<id>` | Multi-horizon ML demand predictions (+15m, +1h, +6h, +24h) |
| `POST` | `/api/ml/train` | Retrain Scikit-Learn ML models on historical telemetry |
| `GET` | `/api/recommendations` | List rightsizing recommendations & savings matrix |
| `POST` | `/api/recommendations/apply/<id>` | Execute rightsizing recommendation |
| `GET` | `/api/scaling/logs` | Chronological audit trail of scaling events |
| `POST` | `/api/simulate-spike/<id>` | Inject artificial workload spike for auto-scaler demo |
| `POST` | `/api/chatbot/query` | AI Cloud Assistant chatbot endpoint |

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
