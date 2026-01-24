from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scraper import COURSES, get_available_times

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

@app.get("/api/courses")
async def get_courses():
    return COURSES

@app.get("/api/tee-times/{club_id}/{course_id}/{date_str}")
async def get_tee_times(club_id: int, course_id: int, date_str: str):
    course = next((c for c in COURSES if c["club_id"] == club_id), None)
    course_name = course["name"] if course else "Unknown"
    return await get_available_times(club_id, course_id, course_name, date_str)
