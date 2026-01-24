from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client
import os

from scraper import COURSES, get_available_times
from models import SessionLocal, Alert

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "https://www.denvertts303.com",
        "https://denvertts303.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

def send_sms(to: str, body: str):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
        print("Twilio not configured")
        return
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    client.messages.create(
        messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
        body=body,
        to=to
    )

async def check_alerts():
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.active == True, Alert.notified_at == None).all()
        for alert in alerts:
            course = next((c for c in COURSES if c["club_id"] == alert.club_id), None)
            if not course:
                continue
            times = await get_available_times(
                alert.club_id, 
                course["course_id"], 
                alert.course_name, 
                alert.date
            )
            matching = [t for t in times if alert.time_start <= t["time_minutes"] <= alert.time_end]
            if matching:
                time_list = ", ".join([t["time_display"] for t in matching[:5]])
                msg = f"⛳ Tee times available at {alert.course_name} on {alert.date}: {time_list}"
                send_sms(alert.phone, msg)
                alert.notified_at = datetime.utcnow()
                db.commit()
    finally:
        db.close()

# Background scheduler
scheduler = BackgroundScheduler()

@app.on_event("startup")
def start_scheduler():
    import asyncio
    def run_check():
        asyncio.run(check_alerts())
    scheduler.add_job(run_check, 'interval', minutes=5)
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    scheduler.shutdown()

# Pydantic models
class AlertCreate(BaseModel):
    phone: str
    club_id: int
    course_name: str
    date: str
    time_start: int
    time_end: int

class AlertResponse(BaseModel):
    id: int
    phone: str
    course_name: str
    date: str
    time_start: int
    time_end: int
    active: bool

# Routes
@app.get("/api/courses")
async def get_courses():
    return COURSES

@app.get("/api/tee-times/{club_id}/{course_id}/{date_str}")
async def get_tee_times(club_id: int, course_id: int, date_str: str):
    course = next((c for c in COURSES if c["club_id"] == club_id), None)
    course_name = course["name"] if course else "Unknown"
    return await get_available_times(club_id, course_id, course_name, date_str)

@app.post("/api/alerts")
async def create_alert(alert: AlertCreate):
    db = SessionLocal()
    try:
        db_alert = Alert(
            phone=alert.phone,
            club_id=alert.club_id,
            course_name=alert.course_name,
            date=alert.date,
            time_start=alert.time_start,
            time_end=alert.time_end
        )
        db.add(db_alert)
        db.commit()
        db.refresh(db_alert)
        return {"id": db_alert.id, "message": "Alert created"}
    finally:
        db.close()

@app.get("/api/alerts/{phone}")
async def get_alerts(phone: str):
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.phone == phone, Alert.active == True).all()
        return [AlertResponse(
            id=a.id,
            phone=a.phone,
            course_name=a.course_name,
            date=a.date,
            time_start=a.time_start,
            time_end=a.time_end,
            active=a.active
        ) for a in alerts]
    finally:
        db.close()

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int):
    db = SessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.active = False
        db.commit()
        return {"message": "Alert deleted"}
    finally:
        db.close()
