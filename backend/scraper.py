import httpx
import re
from datetime import datetime

API_URL = "https://api.membersports.com/api/v1/golfclubs/onlineBookingTeeTimes"
NGSW_URL = "https://app.membersports.com/ngsw.json"
APP_BASE_URL = "https://app.membersports.com"

# Mutable API key that can be refreshed
_api_key = "A9814038-9E19-4683-B171-5A06B39147FC"

COURSES = [
    # Denver Municipal
    {"club_id": 3660, "course_id": 4711, "name": "City Park", "config_type": 1, "group_id": 1},
    {"club_id": 3691, "course_id": 4756, "name": "Evergreen", "config_type": 1, "group_id": 1},
    {"club_id": 3713, "course_id": 4770, "name": "Harvard Gulch", "config_type": 1, "group_id": 1},
    {"club_id": 3629, "course_id": 20573, "name": "Kennedy", "config_type": 1, "group_id": 1},
    {"club_id": 3755, "course_id": 4827, "name": "Overland Park", "config_type": 1, "group_id": 1},
    {"club_id": 3831, "course_id": 4928, "name": "Wellshire", "config_type": 1, "group_id": 1},
    {"club_id": 3833, "course_id": 4932, "name": "Willis Case", "config_type": 1, "group_id": 1},
    # Foothills
    {"club_id": 3697, "course_id": 4758, "name": "Foothills Executive 9", "config_type": 0, "group_id": 3},
    {"club_id": 3697, "course_id": 4757, "name": "Foothills Par 3", "config_type": 0, "group_id": 3},
]

def get_headers():
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": _api_key,
        "Referer": "https://app.membersports.com/",
    }

async def refresh_api_key():
    """Fetch new API key from MemberSports frontend."""
    global _api_key
    try:
        async with httpx.AsyncClient() as client:
            # Get ngsw.json to find main.js filename
            resp = await client.get(NGSW_URL)
            ngsw = resp.json()
            
            # Find main-*.js file
            main_js = next((url for url in ngsw.get("assetGroups", [{}])[0].get("urls", []) if url.startswith("/main-")), None)
            if not main_js:
                print("Could not find main.js in ngsw.json")
                return False
            
            # Fetch main.js
            js_resp = await client.get(f"{APP_BASE_URL}{main_js}")
            js_content = js_resp.text
            
            # Find UUID pattern (API key)
            matches = re.findall(r'[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}', js_content, re.IGNORECASE)
            if matches:
                _api_key = matches[0]
                print(f"API key refreshed: {_api_key}")
                return True
            else:
                print("Could not find API key in main.js")
                return False
    except Exception as e:
        print(f"Error refreshing API key: {e}")
        return False

def minutes_to_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60
    period = "AM" if hours < 12 else "PM"
    if hours > 12:
        hours -= 12
    if hours == 0:
        hours = 12
    return f"{hours}:{mins:02d} {period}"

async def fetch_tee_times(club_id: int, course_id: int, date: str, config_type: int = 1, group_id: int = 1, retry: bool = True):
    payload = {
        "configurationTypeId": config_type,
        "date": date,
        "golfClubGroupId": group_id,
        "golfClubId": club_id,
        "golfCourseId": course_id,
        "groupSheetTypeId": 0
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(API_URL, json=payload, headers=get_headers())
        
        # If auth failed, try refreshing the key
        if resp.status_code in (401, 403) and retry:
            print(f"Auth failed ({resp.status_code}), refreshing API key...")
            if await refresh_api_key():
                return await fetch_tee_times(club_id, course_id, date, config_type, group_id, retry=False)
        
        return resp.json()

async def get_available_times(club_id: int, course_id: int, course_name: str, date: str, config_type: int = 1, group_id: int = 1):
    data = await fetch_tee_times(club_id, course_id, date, config_type, group_id)
    available = []
    if not isinstance(data, list):
        return available
    for slot in data:
        for item in slot.get("items", []):
            # Filter by course and check availability (playerCount < 4 means spots available)
            if item.get("golfCourseId") == course_id and item.get("playerCount", 4) < 4:
                spots_left = 4 - item.get("playerCount", 0)
                available.append({
                    "course_id": course_id,
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
