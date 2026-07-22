import os
import time
import threading
import datetime
import random
import psutil
from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
from database import (
    init_db, get_db, SessionLocal, User, ServerInstance, 
    ResourceData, OptimizationRecommendation, ScalingLog
)
from ml_engine import CloudMLEngine
from optimizer import CloudOptimizerEngine, get_adjacent_tier, get_tier_info

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = "cloud-optimizer-super-secret-key-2026"
CORS(app)

# Initialize database schema and seed data on startup
init_db()
CloudMLEngine.seed_historical_telemetry_if_needed()
# Train initial ML models
try:
    CloudMLEngine.train_models()
except Exception as e:
    print(f"[ML Init Warning] {e}")

# Global flag for artificial workload spikes
SPIKE_NODES = {}

def background_telemetry_daemon():
    """Runs every 3 seconds to harvest host telemetry and simulate cloud node activity."""
    print("[Telemetry Daemon] Started live cloud monitoring daemon...")
    while True:
        try:
            db = SessionLocal()
            instances = db.query(ServerInstance).all()
            now = datetime.datetime.utcnow()

            # Read live host metrics for local node
            host_cpu = psutil.cpu_percent(interval=None)
            host_mem = psutil.virtual_memory().percent
            try:
                host_disk = psutil.disk_usage('/').percent
            except Exception:
                host_disk = 45.0
            
            net_io = psutil.net_io_counters()
            host_rx = round((net_io.bytes_recv / (1024 * 1024)) % 1000, 2)
            host_tx = round((net_io.bytes_sent / (1024 * 1024)) % 1000, 2)
            procs = len(psutil.pids())

            for inst in instances:
                if inst.is_local_host:
                    cpu = host_cpu
                    mem = host_mem
                    disk = host_disk
                    rx = host_rx
                    tx = host_tx
                    active_proc = procs
                else:
                    # Check if node has active simulated spike
                    spike_active = SPIKE_NODES.get(inst.id, False)
                    if spike_active:
                        cpu = min(99.5, random.uniform(88.0, 98.0))
                        mem = min(98.0, random.uniform(82.0, 94.0))
                        rx = random.uniform(45.0, 120.0)
                        tx = random.uniform(30.0, 80.0)
                    else:
                        base = 35.0 if "web" in inst.id else (50.0 if "db" in inst.id else 20.0)
                        cpu = max(4.0, min(95.0, base + random.uniform(-12.0, 12.0)))
                        mem = max(10.0, min(92.0, 40.0 + random.uniform(-8.0, 8.0)))
                        rx = max(0.5, random.uniform(2.0, 18.0))
                        tx = max(0.2, random.uniform(1.0, 12.0))
                    
                    disk = 48.2 + random.uniform(-0.1, 0.1)
                    active_proc = int(35 + (cpu * 0.3))

                is_anom = CloudMLEngine.detect_anomaly(cpu, mem, rx, tx)

                r = ResourceData(
                    instance_id=inst.id,
                    timestamp=now,
                    cpu_percent=round(cpu, 2),
                    memory_percent=round(mem, 2),
                    disk_percent=round(disk, 2),
                    network_rx_mb=round(rx, 2),
                    network_tx_mb=round(tx, 2),
                    active_processes=active_proc,
                    is_anomaly=is_anom
                )
                db.add(r)

                # Check auto-scaling policies
                if inst.auto_scale and not inst.is_local_host:
                    if cpu > 88.0:
                        # Auto scale up
                        next_tier = get_adjacent_tier(inst.provider, inst.tier, direction="up")
                        if next_tier["tier"] != inst.tier:
                            prev = inst.tier
                            inst.tier = next_tier["tier"]
                            inst.hourly_cost = next_tier["cost"]
                            log = ScalingLog(
                                instance_id=inst.id,
                                action="AUTO_SCALE_UP",
                                previous_tier=prev,
                                new_tier=inst.tier,
                                trigger_reason=f"Auto-scaler triggered: CPU spike ({cpu:.1f}% > 88.0 threshold).",
                                cost_impact_monthly=round((next_tier["cost"] - get_tier_info(inst.provider, prev)["cost"]) * 730, 2)
                            )
                            db.add(log)
                            SPIKE_NODES[inst.id] = False # Resolve spike
                    elif cpu < 12.0:
                        # Auto scale down
                        lower_tier = get_adjacent_tier(inst.provider, inst.tier, direction="down")
                        if lower_tier["tier"] != inst.tier:
                            prev = inst.tier
                            inst.tier = lower_tier["tier"]
                            inst.hourly_cost = lower_tier["cost"]
                            log = ScalingLog(
                                instance_id=inst.id,
                                action="AUTO_SCALE_DOWN",
                                previous_tier=prev,
                                new_tier=inst.tier,
                                trigger_reason=f"Auto-scaler triggered: Underutilized CPU ({cpu:.1f}% < 12.0 threshold).",
                                cost_impact_monthly=round((get_tier_info(inst.provider, prev)["cost"] - lower_tier["cost"]) * 730, 2)
                            )
                            db.add(log)

                # Periodically evaluate optimization recommendations
                if random.random() < 0.15:
                    CloudOptimizerEngine.evaluate_instance_recommendations(inst.id)

            db.commit()
            db.close()
        except Exception as e:
            print(f"[Telemetry Error] {e}")
        time.sleep(3)

# Start background thread
telemetry_thread = threading.Thread(target=background_telemetry_daemon, daemon=True)
telemetry_thread.start()

# --- ROUTES ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=username).first()
        if not user and username == "admin" and password == "admin123":
            # Auto-create default admin
            user = User(username="admin", email="admin@cloudopt.io", role="Admin")
            user.set_password("admin123")
            db.add(user)
            db.commit()

        if user and user.check_password(password):
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            return jsonify({"status": "success", "username": user.username, "role": user.role})
        return jsonify({"status": "error", "message": "Invalid username or password"}), 401
    finally:
        db.close()

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})

@app.route("/api/instances", methods=["GET"])
def get_instances():
    db = SessionLocal()
    try:
        instances = db.query(ServerInstance).all()
        res = []
        for i in instances:
            # get latest metric
            latest = db.query(ResourceData).filter_by(instance_id=i.id)\
                        .order_by(ResourceData.timestamp.desc()).first()
            res.append({
                "id": i.id,
                "name": i.name,
                "provider": i.provider,
                "region": i.region,
                "tier": i.tier,
                "hourly_cost": i.hourly_cost,
                "status": i.status,
                "auto_scale": i.auto_scale,
                "is_local_host": i.is_local_host,
                "latest_cpu": latest.cpu_percent if latest else 0.0,
                "latest_mem": latest.memory_percent if latest else 0.0,
                "latest_disk": latest.disk_percent if latest else 0.0,
                "is_anomaly": latest.is_anomaly if latest else False,
            })
        return jsonify(res)
    finally:
        db.close()

@app.route("/api/metrics/live", methods=["GET"])
def get_live_metrics():
    db = SessionLocal()
    try:
        instances = db.query(ServerInstance).all()
        data = {}
        for inst in instances:
            latest = db.query(ResourceData).filter_by(instance_id=inst.id)\
                        .order_by(ResourceData.timestamp.desc()).first()
            if latest:
                data[inst.id] = {
                    "timestamp": latest.timestamp.strftime("%H:%M:%S"),
                    "cpu": latest.cpu_percent,
                    "memory": latest.memory_percent,
                    "disk": latest.disk_percent,
                    "network_rx": latest.network_rx_mb,
                    "network_tx": latest.network_tx_mb,
                    "processes": latest.active_processes,
                    "is_anomaly": latest.is_anomaly
                }
        summary = CloudOptimizerEngine.calculate_cluster_savings_summary()
        return jsonify({"live_data": data, "summary": summary})
    finally:
        db.close()

@app.route("/api/metrics/history/<instance_id>", methods=["GET"])
def get_metrics_history(instance_id):
    db = SessionLocal()
    try:
        limit = int(request.args.get("limit", 40))
        records = db.query(ResourceData).filter_by(instance_id=instance_id)\
                    .order_by(ResourceData.timestamp.desc()).limit(limit).all()
        records.reverse()
        return jsonify([{
            "timestamp": r.timestamp.strftime("%H:%M:%S"),
            "cpu": r.cpu_percent,
            "memory": r.memory_percent,
            "disk": r.disk_percent,
            "network_rx": r.network_rx_mb,
            "network_tx": r.network_tx_mb,
            "is_anomaly": r.is_anomaly
        } for r in records])
    finally:
        db.close()

@app.route("/api/ml/forecast/<instance_id>", methods=["GET"])
def get_forecast(instance_id):
    forecasts = CloudMLEngine.forecast_instance_demand(instance_id)
    return jsonify(forecasts)

@app.route("/api/ml/train", methods=["POST"])
def retrain_ml_model():
    result = CloudMLEngine.train_models()
    return jsonify(result)

@app.route("/api/recommendations", methods=["GET"])
def get_recommendations():
    db = SessionLocal()
    try:
        recs = db.query(OptimizationRecommendation).filter_by(status="PENDING").all()
        res = []
        for r in recs:
            inst = db.query(ServerInstance).filter_by(id=r.instance_id).first()
            res.append({
                "id": r.id,
                "instance_id": r.instance_id,
                "instance_name": inst.name if inst else r.instance_id,
                "provider": inst.provider if inst else "Cloud",
                "recommendation_type": r.recommendation_type,
                "current_tier": r.current_tier,
                "suggested_tier": r.suggested_tier,
                "current_hourly_cost": r.current_hourly_cost,
                "new_hourly_cost": r.new_hourly_cost,
                "estimated_monthly_savings": r.estimated_monthly_savings,
                "reason": r.reason,
                "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M")
            })
        summary = CloudOptimizerEngine.calculate_cluster_savings_summary()
        return jsonify({"recommendations": res, "summary": summary})
    finally:
        db.close()

@app.route("/api/recommendations/apply/<int:rec_id>", methods=["POST"])
def apply_rec(rec_id):
    success, msg = CloudOptimizerEngine.apply_recommendation(rec_id)
    if success:
        return jsonify({"status": "success", "message": msg})
    return jsonify({"status": "error", "message": msg}), 400

@app.route("/api/scaling/logs", methods=["GET"])
def get_scaling_logs():
    db = SessionLocal()
    try:
        logs = db.query(ScalingLog).order_by(ScalingLog.timestamp.desc()).limit(30).all()
        res = []
        for l in logs:
            inst = db.query(ServerInstance).filter_by(id=l.instance_id).first()
            res.append({
                "id": l.id,
                "instance_name": inst.name if inst else l.instance_id,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "action": l.action,
                "previous_tier": l.previous_tier,
                "new_tier": l.new_tier,
                "trigger_reason": l.trigger_reason,
                "cost_impact_monthly": l.cost_impact_monthly
            })
        return jsonify(res)
    finally:
        db.close()

@app.route("/api/scaling/toggle-autoscale/<instance_id>", methods=["POST"])
def toggle_autoscale(instance_id):
    db = SessionLocal()
    try:
        inst = db.query(ServerInstance).filter_by(id=instance_id).first()
        if inst:
            inst.auto_scale = not inst.auto_scale
            db.commit()
            return jsonify({"status": "success", "auto_scale": inst.auto_scale})
        return jsonify({"status": "error", "message": "Instance not found"}), 404
    finally:
        db.close()

@app.route("/api/simulate-spike/<instance_id>", methods=["POST"])
def simulate_spike(instance_id):
    SPIKE_NODES[instance_id] = True
    return jsonify({"status": "success", "message": f"Workload spike initiated on {instance_id}. Observe ML forecast and auto-scaler."})

@app.route("/api/chatbot/query", methods=["POST"])
def chatbot_query():
    data = request.json or {}
    query = data.get("query", "").lower()

    db = SessionLocal()
    try:
        summary = CloudOptimizerEngine.calculate_cluster_savings_summary()
        instances = db.query(ServerInstance).all()
        recs = db.query(OptimizationRecommendation).filter_by(status="PENDING").all()

        if "cost" in query or "saving" in query or "price" in query:
            reply = f"💰 **Cloud Cost Optimization Summary**:\n- Your current estimated monthly cloud burn is **${summary['monthly_cloud_burn']}** across {summary['total_instances']} servers.\n- We have identified **{summary['pending_recommendations_count']} pending rightsizing recommendations** that can save **${summary['potential_monthly_savings']}/month**."
        elif "spike" in query or "high" in query or "cpu" in query:
            high_cpu_instances = []
            for i in instances:
                latest = db.query(ResourceData).filter_by(instance_id=i.id).order_by(ResourceData.timestamp.desc()).first()
                if latest and latest.cpu_percent > 70.0:
                    high_cpu_instances.append(f"{i.name} ({latest.cpu_percent}%)")
            if high_cpu_instances:
                reply = f"⚠️ High CPU usage detected on: {', '.join(high_cpu_instances)}. Recommend enabling auto-scaling or upgrading instance tiers."
            else:
                reply = "✅ All cloud instances are currently operating within healthy CPU thresholds (< 70%)."
        elif "ml" in query or "model" in query or "predict" in query:
            reply = "🤖 **Machine Learning Forecaster**: Uses a Random Forest Regressor trained on historical 15-minute telemetry intervals. It models diurnal business-hour patterns to forecast CPU and Memory demand for +15m, +1h, +6h, and +24h horizons with confidence intervals."
        elif "auto" in query or "scale" in query:
            reply = "⚡ **Auto-Scaling Policy**: If CPU utilization breaches 88% on auto-scaled instances, the system automatically provisions the next tier up. Conversely, if CPU stays below 12%, it scales down to eliminate idle compute costs."
        else:
            reply = f"👋 I'm **CloudOpt AI Assistant**. I can help you monitor your cluster of {len(instances)} cloud nodes, review ML demand forecasts, analyze rightsizing recommendations, and automate scaling!"

        return jsonify({"reply": reply})
    finally:
        db.close()

if __name__ == "__main__":
    print("[Server] Starting AI-Powered Cloud Resource Optimizer Server on http://127.0.0.1:5000 ...")
    app.run(host="0.0.0.0", port=5000, debug=False)

