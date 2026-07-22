import datetime
from database import SessionLocal, ServerInstance, ResourceData, OptimizationRecommendation, ScalingLog

# Cloud Instance Pricing Catalog (USD / hour)
CLOUD_TIERS = {
    "AWS": [
        {"tier": "t3.nano", "vcpu": 2, "ram_gb": 0.5, "cost": 0.0052},
        {"tier": "t3.micro", "vcpu": 2, "ram_gb": 1.0, "cost": 0.0104},
        {"tier": "t3.small", "vcpu": 2, "ram_gb": 2.0, "cost": 0.0208},
        {"tier": "t3.medium", "vcpu": 2, "ram_gb": 4.0, "cost": 0.0416},
        {"tier": "t3.large", "vcpu": 2, "ram_gb": 8.0, "cost": 0.0832},
        {"tier": "t3.xlarge", "vcpu": 4, "ram_gb": 16.0, "cost": 0.1664},
        {"tier": "c5.2xlarge", "vcpu": 8, "ram_gb": 16.0, "cost": 0.3400},
    ],
    "Azure": [
        {"tier": "Standard_B1ls", "vcpu": 1, "ram_gb": 0.5, "cost": 0.0052},
        {"tier": "Standard_B1s", "vcpu": 1, "ram_gb": 1.0, "cost": 0.0120},
        {"tier": "Standard_B2s", "vcpu": 2, "ram_gb": 4.0, "cost": 0.0416},
        {"tier": "Standard_D2s_v3", "vcpu": 2, "ram_gb": 8.0, "cost": 0.0960},
        {"tier": "Standard_D4s_v3", "vcpu": 4, "ram_gb": 16.0, "cost": 0.1920},
    ],
    "GCP": [
        {"tier": "e2-micro", "vcpu": 2, "ram_gb": 1.0, "cost": 0.0084},
        {"tier": "e2-small", "vcpu": 2, "ram_gb": 2.0, "cost": 0.0168},
        {"tier": "e2-medium", "vcpu": 2, "ram_gb": 4.0, "cost": 0.0335},
        {"tier": "e2-standard-4", "vcpu": 4, "ram_gb": 16.0, "cost": 0.1340},
    ]
}

def get_tier_info(provider, tier_name):
    catalog = CLOUD_TIERS.get(provider, CLOUD_TIERS["AWS"])
    for t in catalog:
        if t["tier"].lower() == tier_name.lower():
            return t
    return catalog[0]

def get_adjacent_tier(provider, current_tier, direction="down"):
    catalog = CLOUD_TIERS.get(provider, CLOUD_TIERS["AWS"])
    idx = -1
    for i, t in enumerate(catalog):
        if t["tier"].lower() == current_tier.lower():
            idx = i
            break
    if idx == -1:
        return current_tier
    
    if direction == "down" and idx > 0:
        return catalog[idx - 1]
    elif direction == "up" and idx < len(catalog) - 1:
        return catalog[idx + 1]
    return catalog[idx]

class CloudOptimizerEngine:

    @staticmethod
    def evaluate_instance_recommendations(instance_id):
        db = SessionLocal()
        try:
            instance = db.query(ServerInstance).filter_by(id=instance_id).first()
            if not instance:
                return None
            
            # Fetch recent 50 telemetry points
            records = db.query(ResourceData).filter_by(instance_id=instance_id)\
                        .order_by(ResourceData.timestamp.desc()).limit(50).all()
            
            if not records:
                return None

            avg_cpu = sum(r.cpu_percent for r in records) / len(records)
            avg_mem = sum(r.memory_percent for r in records) / len(records)
            max_cpu = max(r.cpu_percent for r in records)

            # Clear old pending recommendations for this instance
            db.query(OptimizationRecommendation).filter_by(
                instance_id=instance_id, status="PENDING"
            ).delete()

            rec = None
            curr_info = get_tier_info(instance.provider, instance.tier)
            curr_cost = curr_info["cost"]

            if avg_cpu < 18.0 and avg_mem < 35.0:
                # Recommend Downsizing
                lower_tier = get_adjacent_tier(instance.provider, instance.tier, direction="down")
                if lower_tier["tier"] != instance.tier:
                    savings_hr = curr_cost - lower_tier["cost"]
                    monthly_savings = savings_hr * 730.0
                    rec = OptimizationRecommendation(
                        instance_id=instance.id,
                        recommendation_type="RIGHTSIZE_DOWN",
                        current_tier=instance.tier,
                        suggested_tier=lower_tier["tier"],
                        current_hourly_cost=curr_cost,
                        new_hourly_cost=lower_tier["cost"],
                        estimated_monthly_savings=round(monthly_savings, 2),
                        reason=f"Average CPU ({avg_cpu:.1f}%) and RAM ({avg_mem:.1f}%) are underutilized. Downgrade to {lower_tier['tier']} to eliminate cloud waste.",
                        status="PENDING"
                    )

            elif avg_cpu > 75.0 or avg_mem > 85.0 or max_cpu > 92.0:
                # Recommend Upsizing to prevent performance bottleneck
                higher_tier = get_adjacent_tier(instance.provider, instance.tier, direction="up")
                if higher_tier["tier"] != instance.tier:
                    cost_increase_hr = higher_tier["cost"] - curr_cost
                    monthly_cost_delta = -(cost_increase_hr * 730.0)
                    rec = OptimizationRecommendation(
                        instance_id=instance.id,
                        recommendation_type="RIGHTSIZE_UP",
                        current_tier=instance.tier,
                        suggested_tier=higher_tier["tier"],
                        current_hourly_cost=curr_cost,
                        new_hourly_cost=higher_tier["cost"],
                        estimated_monthly_savings=round(monthly_cost_delta, 2),
                        reason=f"High compute utilization (Avg CPU {avg_cpu:.1f}%, Peak {max_cpu:.1f}%). Scale up to {higher_tier['tier']} to maintain high availability and SLA.",
                        status="PENDING"
                    )

            if rec:
                db.add(rec)
                db.commit()
                return rec.id
            return None
        finally:
            db.close()

    @staticmethod
    def apply_recommendation(rec_id):
        db = SessionLocal()
        try:
            rec = db.query(OptimizationRecommendation).filter_by(id=rec_id).first()
            if not rec or rec.status == "APPLIED":
                return False, "Recommendation invalid or already applied"

            instance = db.query(ServerInstance).filter_by(id=rec.instance_id).first()
            if not instance:
                return False, "Instance not found"

            prev_tier = instance.tier
            instance.tier = rec.suggested_tier
            instance.hourly_cost = rec.new_hourly_cost
            rec.status = "APPLIED"

            # Create scaling audit log
            action_type = "SCALE_DOWN" if rec.recommendation_type == "RIGHTSIZE_DOWN" else "SCALE_UP"
            log = ScalingLog(
                instance_id=instance.id,
                action=action_type,
                previous_tier=prev_tier,
                new_tier=rec.suggested_tier,
                trigger_reason=f"Recommendation #{rec.id} applied: {rec.reason}",
                cost_impact_monthly=rec.estimated_monthly_savings
            )
            db.add(log)
            db.commit()
            return True, f"Successfully scaled {instance.name} from {prev_tier} to {rec.suggested_tier}."
        finally:
            db.close()

    @staticmethod
    def calculate_cluster_savings_summary():
        db = SessionLocal()
        try:
            recs = db.query(OptimizationRecommendation).filter_by(status="PENDING").all()
            applied_recs = db.query(OptimizationRecommendation).filter_by(status="APPLIED").all()
            
            pending_savings = sum(r.estimated_monthly_savings for r in recs if r.estimated_monthly_savings > 0)
            realized_savings = sum(r.estimated_monthly_savings for r in applied_recs if r.estimated_monthly_savings > 0)
            
            instances = db.query(ServerInstance).all()
            monthly_burn = sum(i.hourly_cost * 730 for i in instances)
            
            return {
                "total_instances": len(instances),
                "monthly_cloud_burn": round(monthly_burn, 2),
                "potential_monthly_savings": round(pending_savings, 2),
                "realized_monthly_savings": round(realized_savings, 2),
                "pending_recommendations_count": len(recs)
            }
        finally:
            db.close()
