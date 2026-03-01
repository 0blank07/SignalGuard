from fastapi import FastAPI
from pydantic import BaseModel
from database import engine, Base
import models
from database import SessionLocal
from sqlalchemy.orm import Session
from models import Incident

app = FastAPI()
Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message": "SignalGuard API running"}

class Metric(BaseModel):
     cpu: float
     memory: float

@app.post("/api/metrics", status_code=201)
def create_metric(metric: Metric):
    db: Session = SessionLocal()

    db_metric = models.Metric(cpu=metric.cpu, memory=metric.memory)
    db.add(db_metric)
    db.refresh(db_metric)


    if metric.cpu > 90:
       incident = Incident(
           metric_id=db_metric.id,
           type="cpu_high"
       )
       db.add(incident)
       db.refresh(incident)

    if metric.memory > 90:
       incident = Incident(
           metric_id = db_metric.id,
           type="memory_high"
       )

       db.add(incident)
       db.refresh(incident)

    db.commit
    db.close()

    return {
        "message": "Metric stored"
        "id": db_metric.id
    }

@app.get("/api/incidents")
def get_incidents():
    db = SessionLocal()
    incidents = db.query(Incident).all()
    return incidents

@app.patch("/api/incidents/{incident_id}")
def resolved_incident(incident_id: int):
    db = SessionLocal()
    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if not incident:
       return {"error": "Incident not found"}

    incident.status = "resolved"
    db.commit()

    return {"message": "Incident resolved"}






















