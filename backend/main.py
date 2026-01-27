from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from datetime import datetime, date
from apscheduler.schedulers.background import BackgroundScheduler
from twilio.rest import Client
import os
import asyncio

from scraper import COURSES, get_available_times
from models import SessionLocal, Alert

# Twilio setup
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_MESSAGING_SERVICE_SID = os.getenv("TWILIO_MESSAGING_SERVICE_SID")

def send_sms(to: str, body: str):
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_MESSAGING_SERVICE_SID]):
        print("Twilio not configured")
        return False
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            messaging_service_sid=TWILIO_MESSAGING_SERVICE_SID,
            body=body,
            to=to
        )
        print(f"SMS sent to {to}")
        return True
    except Exception as e:
        print(f"SMS error: {e}")
        return False

async def check_alerts():
    print("Checking alerts...")
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.active == True, Alert.notified_at == None, Alert.date >= date.today().isoformat()).all()
        print(f"Found {len(alerts)} active alerts")
        for alert in alerts:
            course = next((c for c in COURSES if c["club_id"] == alert.club_id and c["name"] == alert.course_name), None)
            if not course:
                course = next((c for c in COURSES if c["club_id"] == alert.club_id), None)
            if not course:
                print(f"Course not found for alert {alert.id}")
                continue
            print(f"Checking alert {alert.id} for {alert.course_name} on {alert.date}")
            times = await get_available_times(
                alert.club_id, 
                course["course_id"], 
                alert.course_name, 
                alert.date,
                course.get("config_type", 1),
                course.get("group_id", 1)
            )
            matching = [t for t in times if alert.time_start <= t["time_minutes"] <= alert.time_end and t["spots_available"] >= alert.min_spots]
            print(f"Found {len(matching)} matching times")
            if matching:
                time_list = ", ".join([t["time_display"] for t in matching[:5]])
                msg = f"⛳ Tee times available at {alert.course_name} on {alert.date}: {time_list}"
                if send_sms(alert.phone, msg):
                    alert.notified_at = datetime.utcnow()
                    db.commit()
                    print(f"Alert {alert.id} notified")
    except Exception as e:
        print(f"Error checking alerts: {e}")
    finally:
        db.close()

# Background scheduler
scheduler = BackgroundScheduler()

def run_check():
    print("Scheduler triggered")
    asyncio.run(check_alerts())

@asynccontextmanager
async def lifespan(app):
    scheduler.add_job(run_check, 'interval', minutes=5)
    scheduler.start()
    print("Scheduler started")
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# Pydantic models
class AlertCreate(BaseModel):
    phone: str
    club_id: int
    course_name: str
    date: str
    time_start: int
    time_end: int
    min_spots: int = 1

# Routes
@app.get("/api/courses")
async def get_courses():
    return COURSES

@app.get("/api/tee-times/{club_id}/{course_id}/{date_str}")
async def get_tee_times(club_id: int, course_id: int, date_str: str):
    course = next((c for c in COURSES if c["club_id"] == club_id and c["course_id"] == course_id), None)
    if not course:
        course = next((c for c in COURSES if c["club_id"] == club_id), None)
    course_name = course["name"] if course else "Unknown"
    config_type = course.get("config_type", 1) if course else 1
    group_id = course.get("group_id", 1) if course else 1
    return await get_available_times(club_id, course_id, course_name, date_str, config_type, group_id)

@app.post("/api/alerts")
async def create_alert(alert: AlertCreate, db = Depends(get_db)):
    digits = ''.join(c for c in alert.phone if c.isdigit())
    if len(digits) < 10 or len(digits) > 11:
        raise HTTPException(status_code=400, detail="Invalid phone number")
    
    # Check for duplicate alert
    existing = db.query(Alert).filter(
        Alert.phone == alert.phone,
        Alert.club_id == alert.club_id,
        Alert.date == alert.date,
        Alert.time_start == alert.time_start,
        Alert.time_end == alert.time_end,
        Alert.min_spots == alert.min_spots,
        Alert.active == True
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have an alert for this exact request")
    
    # Check if matching tee times already exist
    course = next((c for c in COURSES if c["club_id"] == alert.club_id and c["name"] == alert.course_name), None)
    if not course:
        course = next((c for c in COURSES if c["club_id"] == alert.club_id), None)
    if course:
        times = await get_available_times(
            alert.club_id, 
            course["course_id"], 
            alert.course_name, 
            alert.date,
            course.get("config_type", 1),
            course.get("group_id", 1)
        )
        matching = [t for t in times if alert.time_start <= t["time_minutes"] <= alert.time_end and t["spots_available"] >= alert.min_spots]
        if matching:
            raise HTTPException(status_code=400, detail="There are already tee time(s) that match this request")
    
    db_alert = Alert(
        phone=alert.phone,
        club_id=alert.club_id,
        course_name=alert.course_name,
        date=alert.date,
        time_start=alert.time_start,
        time_end=alert.time_end,
        min_spots=alert.min_spots
    )
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return {"id": db_alert.id, "message": "Alert created"}

@app.get("/api/alerts/{phone}")
async def get_alerts(phone: str, db = Depends(get_db)):
    alerts = db.query(Alert).filter(Alert.phone == phone, Alert.active == True).all()
    return [{"id": a.id, "course_name": a.course_name, "date": a.date, "time_start": a.time_start, "time_end": a.time_end} for a in alerts]

@app.delete("/api/alerts/{alert_id}")
async def delete_alert(alert_id: int, db = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.active = False
    db.commit()
    return {"message": "Alert deleted"}

@app.post("/api/test-alerts")
async def test_alerts():
    """Manually trigger alert check"""
    await check_alerts()
    return {"message": "Alert check completed"}

@app.post("/api/test-sms/{phone}")
async def test_sms(phone: str):
    """Send a test SMS"""
    success = send_sms(phone, "⛳ Test message from Denver Golf Tee Times!")
    return {"success": success}
