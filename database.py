import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cloud_optimizer.db")
ENGINE = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ENGINE)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(20), default="Admin")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ServerInstance(Base):
    __tablename__ = "server_instances"

    id = Column(String(50), primary_key=True) # e.g. "inst-aws-web-01"
    name = Column(String(100), nullable=False)
    provider = Column(String(20), default="AWS") # AWS, Azure, GCP, Local
    region = Column(String(50), default="us-east-1")
    tier = Column(String(50), default="t3.large") # Current VM size
    hourly_cost = Column(Float, default=0.0832) # USD/hr
    status = Column(String(20), default="Running") # Running, Idle, Scaled Down, Stopped
    auto_scale = Column(Boolean, default=True)
    is_local_host = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    telemetry = relationship("ResourceData", back_populates="instance", cascade="all, delete-orphan")
    recommendations = relationship("OptimizationRecommendation", back_populates="instance", cascade="all, delete-orphan")
    scaling_logs = relationship("ScalingLog", back_populates="instance", cascade="all, delete-orphan")

class ResourceData(Base):
    __tablename__ = "resource_data"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(50), ForeignKey("server_instances.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    cpu_percent = Column(Float, nullable=False)
    memory_percent = Column(Float, nullable=False)
    disk_percent = Column(Float, nullable=False)
    network_rx_mb = Column(Float, default=0.0) # Received MB
    network_tx_mb = Column(Float, default=0.0) # Transmitted MB
    active_processes = Column(Integer, default=50)
    is_anomaly = Column(Boolean, default=False)

    instance = relationship("ServerInstance", back_populates="telemetry")

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(50), ForeignKey("server_instances.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    recommendation_type = Column(String(50), nullable=False) # DOWNSIZE, UPSIZE, TERMINATE_IDLE
    current_tier = Column(String(50), nullable=False)
    suggested_tier = Column(String(50), nullable=False)
    current_hourly_cost = Column(Float, nullable=False)
    new_hourly_cost = Column(Float, nullable=False)
    estimated_monthly_savings = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="PENDING") # PENDING, APPLIED, DISMISSED

    instance = relationship("ServerInstance", back_populates="recommendations")

class ScalingLog(Base):
    __tablename__ = "scaling_logs"

    id = Column(Integer, primary_key=True, index=True)
    instance_id = Column(String(50), ForeignKey("server_instances.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    action = Column(String(50), nullable=False) # SCALE_UP, SCALE_DOWN, AUTO_SCALED
    previous_tier = Column(String(50), nullable=False)
    new_tier = Column(String(50), nullable=False)
    trigger_reason = Column(Text, nullable=False)
    cost_impact_monthly = Column(Float, default=0.0)

    instance = relationship("ServerInstance", back_populates="scaling_logs")

def init_db():
    Base.metadata.create_all(bind=ENGINE)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()
