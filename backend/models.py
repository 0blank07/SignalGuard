from sqlalchemy import Column, Integer, Float, DateTime, String
from datetime import datetime

from database import Base

class Metric(Base):
     __tablename__ = "metrics"

     id = Column(Integer, primary_key=True, index=True)
     cpu = Column(Float, nullable=False)
     memory = Column(Float, nullable=False)
     date = Column(DateTime, default=datetime.utcnow)

class Incident(Base):
    __tablename__ = "incident"

    id = Column(Integer, primary_key=True, index=True)
    metric_id = Column(Integer)
    type = Column(String, nullable=False)
    status = Column(String, default="open")
    created_at = Column(Date, default=datetime.utcnow)
    last_seen_at = Column(Date, default=datetime.utcnow)
