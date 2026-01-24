import httpx
from datetime import datetime

API_URL = "https://api.membersports.com/api/v1/golfclubs/onlineBookingTeeTimes"
API_KEY = "A9814038-9E19-4683-B171-5A06B39147FC"

COURSES = [
    {"club_id": 3660, "course_id": 4711, "name": "City Park"},
    {"club_id": 3691, "course_id": 4756, "name": "Evergreen"},
    {"club_id": 3713, "course_id": 4770, "name": "Harvard Gulch"},
    {"club_id": 3629, "course_id": 20573, "name": "Kennedy"},
    {"club_id": 3755, "course_id": 4827, "name": "Overland Park"},
    {"club_id": 3831, "course_id": 4928, "name": "Wellshire"},
    {"club_id": 3833, "course_id": 4932, "name": "Willis Case"},
]

HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "x-api-key": API_KEY,
    "Referer": "https://app.membersports.com/",
}

def minutes_to_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    period = "AM" if hours < 12 else "PM"
    if hours > 12:
        hours -= 12
    if hours == 0:
        hours = 12
    return f"{hours}:{mins:02d} {period}"

async def fetch_tee_times(club_id: int, course_id: int, date: str):
    payload = {
        "configurationTypeId": 1,
        "date": date,
        "golfClubGroupId": 1,
        "golfClubId": club_id,
        "golfCourseId": course_id,
        "groupSheetTypeId": 0
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(API_URL, json=payload, headers=HEADERS)
        return resp.json()

async def get_available_times(club_id: int, course_id: int, course_name: str, date: str):
    data = await fetch_tee_times(club_id, course_id, date)
    available = []
    if not isinstance(data, list):
        return available
    for slot in data:
        for item in slot.get("items", []):
            # Filter by course and check availability (playerCount < 4 means spots available)
            if item.get("golfClubId") == club_id and item.get("playerCount", 4) < 4:
                spots_left = 4 - item.get("playerCount", 0)
                available.append({
                    "course_id": club_id,
                    "course_name": item.get("name", course_name),
                    "date": date,
                    "time_minutes": slot["teeTime"],
                    "time_display": minutes_to_time(slot["teeTime"]),
                    "spots_available": spots_left,
                    "price": item.get("price", 0),
                    "holes": item.get("golfCourseNumberOfHoles", 18),
                    "scraped_at": datetime.utcnow().isoformat()
                })
    return available
