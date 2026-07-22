# AI-Powered Cloud Resource Optimization

## Project Summary
Cloud providers often allocate more computing resources than applications actually need, leading to unnecessary costs and inefficient resource usage. This project develops a cloud-based system that monitors resource utilization (CPU, memory, storage, and network), analyzes usage patterns, and uses machine learning to predict future demand. Based on these predictions, the system recommends or automatically scales cloud resources to improve performance while minimizing costs.

The project demonstrates how artificial intelligence can make cloud infrastructure more efficient, reducing waste and ensuring applications continue to run smoothly even during changes in demand.

---

## Objectives
- Monitor cloud resource usage in real time.
- Collect and store performance metrics.
- Predict future resource requirements using machine learning.
- Recommend or automate resource scaling.
- Reduce cloud infrastructure costs.
- Display usage statistics through an interactive dashboard.

---

## Technologies Used
- **Cloud Platform**: AWS / Azure / GCP / Local Host Simulation
- **Programming Language**: Python
- **Backend**: Flask
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite / PostgreSQL / MySQL (SQLAlchemy ORM)
- **Machine Learning**: Scikit-learn, Pandas, NumPy
- **Visualization**: Chart.js
- **System Telemetry**: `psutil`

---

## System Architecture

```
Cloud Server
     │
     ▼
Resource Monitoring (CPU, RAM, Storage, Network)
     │
     ▼
Database (Telemetry & History)
     │
     ▼
Machine Learning Model (Predict Future Demand)
     │
     ▼
Optimization Engine (Cost Savings & Scaling Rules)
     │
     ▼
Dashboard + Scaling Recommendation
```

---

## Project Modules

1. **User Login**: Secure authentication with role-based access.
2. **Resource Monitoring**: Live tracking of CPU utilization, memory usage, disk usage, and network traffic.
3. **Data Storage**: Historical metric storage and logging daemon.
4. **Machine Learning Prediction**: Scikit-learn time-series forecasting models predicting future compute requirements.
5. **Optimization Module**: Recommends resource downsizing/upsizing and estimates monthly cloud savings.
6. **Dashboard**: Interactive graphs, server status cards, prediction charts, auto-scaling logs, and optimization recommendations.

---

## How to Build & Run

### Step 1: Set Up the Environment
Install required Python packages:
```bash
pip install -r requirements.txt
```

### Step 2: Run the Application
Start the Flask web server:
```bash
python app.py
```

### Step 3: Open the Dashboard
Open your web browser and navigate to:
`http://127.0.0.1:5000`
