import httpx
import re
from datetime import datetime

# MemberSports config
MEMBERSPORTS_API_URL = "https://api.membersports.com/api/v1/golfclubs/onlineBookingTeeTimes"
NGSW_URL = "https://app.membersports.com/ngsw.json"
APP_BASE_URL = "https://app.membersports.com"

# Chronogolf config
CHRONOGOLF_API_URL = "https://www.chronogolf.com/marketplace/v2/teetimes"

# ezlinks config
EZLINKS_API_URL = "https://cityofaurora.ezlinksgolf.com/api/search/search"

# Mutable API key for MemberSports (can be refreshed)
_api_key = "A9814038-9E19-4683-B171-5A06B39147FC"

COURSES = [
    # Denver Municipal (MemberSports)
    {"provider": "membersports", "club_id": 3660, "course_id": 4711, "name": "City Park", "config_type": 1, "group_id": 1},
    {"provider": "membersports", "club_id": 3691, "course_id": 4756, "name": "Evergreen", "config_type": 1, "group_id": 1},
    {"provider": "membersports", "club_id": 3713, "course_id": 4770, "name": "Harvard Gulch", "config_type": 1, "group_id": 1},
    {"provider": "membersports", "club_id": 3629, "course_id": 20573, "name": "Kennedy", "config_type": 1, "group_id": 1},
    {"provider": "membersports", "club_id": 3755, "course_id": 4827, "name": "Overland Park", "config_type": 1, "group_id": 1},
    {"provider": "membersports", "club_id": 3831, "course_id": 4928, "name": "Wellshire", "config_type": 1, "group_id": 1},
    {"provider": "membersports", "club_id": 3833, "course_id": 4932, "name": "Willis Case", "config_type": 1, "group_id": 1},
    # Foothills (MemberSports)
    {"provider": "membersports", "club_id": 3697, "course_id": 4758, "name": "Foothills Executive 9", "config_type": 0, "group_id": 3},
    {"provider": "membersports", "club_id": 3697, "course_id": 4757, "name": "Foothills Par 3", "config_type": 0, "group_id": 3},
    # South Suburban (Chronogolf)
    {"provider": "chronogolf", "course_id": "482fb33a-fa4a-48fb-85e1-e0492fe39d1a", "name": "SSG 18 Hole Course", "booking_slug": "south-suburban-golf-club"},
    {"provider": "chronogolf", "course_id": "68c1a9d5-f402-4d54-a1c5-991363899bc8", "name": "SSG 9 Hole Par 3", "booking_slug": "south-suburban-golf-club"},
    # Lone Tree (Chronogolf)
    {"provider": "chronogolf", "course_id": "001a7f2d-2c20-4bd9-8f91-3df9d051f737", "name": "Lone Tree 18 Hole", "booking_slug": "lone-tree-golf-club-hotel"},
    # Aurora (ezlinks)
    {"provider": "ezlinks", "course_id": 19197, "name": "Saddle Rock"},
    {"provider": "ezlinks", "course_id": 6386, "name": "Aurora Hills"},
    {"provider": "ezlinks", "course_id": 6516, "name": "Springhill"},
    {"provider": "ezlinks", "course_id": 6474, "name": "Meadow Hills"},
    {"provider": "ezlinks", "course_id": 19921, "name": "Murphy Creek"},
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

async def fetch_membersports_tee_times(club_id: int, course_id: int, date: str, config_type: int = 1, group_id: int = 1, retry: bool = True):
    payload = {
        "configurationTypeId": config_type,
        "date": date,
        "golfClubGroupId": group_id,
        "golfClubId": club_id,
        "golfCourseId": course_id,
        "groupSheetTypeId": 0
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(MEMBERSPORTS_API_URL, json=payload, headers=get_headers())
        
        # If auth failed, try refreshing the key
        if resp.status_code in (401, 403) and retry:
            print(f"Auth failed ({resp.status_code}), refreshing API key...")
            if await refresh_api_key():
                return await fetch_membersports_tee_times(club_id, course_id, date, config_type, group_id, retry=False)
        
        return resp.json()

async def fetch_chronogolf_tee_times(course_id: str, date: str):
    params = {
        "start_date": date,
        "course_ids": course_id,
        "page": 1
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(CHRONOGOLF_API_URL, params=params)
        return resp.json()

async def fetch_ezlinks_tee_times(course_id: int, date: str):
    # Format date as MM/DD/YYYY
    parts = date.split('-')
    formatted_date = f"{parts[1]}/{parts[2]}/{parts[0]}"
    payload = {
        "p01": [course_id],
        "p02": formatted_date,
        "p03": "5:00 AM",
        "p04": "9:00 PM",
        "p05": 0,
        "p06": 1,
        "p07": False
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json; charset=UTF-8",
        "Origin": "https://cityofaurora.ezlinksgolf.com",
        "Referer": "https://cityofaurora.ezlinksgolf.com/index.html",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(EZLINKS_API_URL, json=payload, headers=headers)
        if resp.status_code != 200:
            print(f"ezlinks error: {resp.status_code} - {resp.text[:200]}")
            return {}
        try:
            return resp.json()
        except:
            print(f"ezlinks JSON parse error: {resp.text[:200]}")
            return {}

def parse_time_to_minutes(time_str: str) -> int:
    """Convert time string like '9:35' or '14:30' to minutes from midnight."""
    parts = time_str.split(':')
    hours = int(parts[0])
    mins = int(parts[1]) if len(parts) > 1 else 0
    return hours * 60 + mins

async def get_available_times(course: dict, date: str):
    """Unified function to get available times from any provider."""
    provider = course.get("provider", "membersports")
    
    if provider == "membersports":
        return await get_membersports_times(course, date)
    elif provider == "chronogolf":
        return await get_chronogolf_times(course, date)
    elif provider == "ezlinks":
        return await get_ezlinks_times(course, date)
    else:
        return []

async def get_membersports_times(course: dict, date: str):
    data = await fetch_membersports_tee_times(
        course["club_id"], 
        course["course_id"], 
        date,
        course.get("config_type", 1),
        course.get("group_id", 1)
    )
    available = []
    if not isinstance(data, list):
        return available
    for slot in data:
        for item in slot.get("items", []):
            if item.get("golfCourseId") == course["course_id"] and item.get("playerCount", 4) < 4:
                spots_left = 4 - item.get("playerCount", 0)
                available.append({
                    "course_id": course["course_id"],
                    "course_name": item.get("name", course["name"]),
                    "date": date,
                    "time_minutes": slot["teeTime"],
                    "time_display": minutes_to_time(slot["teeTime"]),
                    "spots_available": spots_left,
                    "price": item.get("price", 0),
                    "holes": item.get("golfCourseNumberOfHoles", 18),
                    "scraped_at": datetime.utcnow().isoformat()
                })
    return available

async def get_chronogolf_times(course: dict, date: str):
    data = await fetch_chronogolf_tee_times(course["course_id"], date)
    available = []
    if not isinstance(data, dict) or "teetimes" not in data:
        return available
    for tt in data["teetimes"]:
        # Only include times for this specific course
        if tt.get("course", {}).get("uuid") != course["course_id"]:
            continue
        time_minutes = parse_time_to_minutes(tt["start_time"])
        available.append({
            "course_id": course["course_id"],
            "course_name": tt.get("course", {}).get("name", course["name"]),
            "date": tt.get("date", date),
            "time_minutes": time_minutes,
            "time_display": minutes_to_time(time_minutes),
            "spots_available": tt.get("max_player_size", 4),
            "price": tt.get("default_price", {}).get("green_fee", 0),
            "holes": tt.get("course", {}).get("holes", 18),
            "scraped_at": datetime.utcnow().isoformat()
        })
    return available

async def get_ezlinks_times(course: dict, date: str):
    data = await fetch_ezlinks_tee_times(course["course_id"], date)
    available = []
    if not isinstance(data, dict) or "r06" not in data:
        return available
    
    # Group by time to avoid duplicates (ezlinks returns multiple rate types per time)
    seen_times = set()
    for tt in data["r06"]:
        # Only include times for this specific course
        if tt.get("r07") != course["course_id"]:
            continue
        
        time_str = tt.get("r24", "")  # e.g., "10:05 AM"
        if time_str in seen_times:
            continue
        seen_times.add(time_str)
        
        time_minutes = parse_time_to_minutes_12hr(time_str)
        available.append({
            "course_id": course["course_id"],
            "course_name": course["name"],
            "date": date,
            "time_minutes": time_minutes,
            "time_display": time_str,
            "spots_available": tt.get("r14", 4),
            "price": tt.get("r08", 0),
            "holes": 18,
            "scraped_at": datetime.utcnow().isoformat()
        })
    return available

def parse_time_to_minutes_12hr(time_str: str) -> int:
    """Convert 12-hour time string like '10:05 AM' to minutes from midnight."""
    try:
        parts = time_str.replace(':', ' ').split()
        hours = int(parts[0])
        mins = int(parts[1])
        period = parts[2].upper() if len(parts) > 2 else "AM"
        if period == "PM" and hours != 12:
            hours += 12
        if period == "AM" and hours == 12:
            hours = 0
        return hours * 60 + mins
    except:
        return 0
