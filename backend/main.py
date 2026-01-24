from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import COURSES, get_available_times
from datetime import date

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/courses")
def get_courses():
    return COURSES

@app.get("/api/tee-times/{club_id}/{course_id}/{date_str}")
async def get_tee_times(club_id: int, course_id: int, date_str: str):
    course = next((c for c in COURSES if c["club_id"] == club_id), None)
    name = course["name"] if course else "Unknown"
    return await get_available_times(club_id, course_id, name, date_str)

@app.get("/api/tee-times/all/{date_str}")
async def get_all_tee_times(date_str: str):
    all_times = []
    for course in COURSES:
        times = await get_available_times(
            course["club_id"], 
            course["course_id"], 
            course["name"], 
            date_str
        )
        all_times.extend(times)
    return sorted(all_times, key=lambda x: (x["time_minutes"], x["course_name"]))
