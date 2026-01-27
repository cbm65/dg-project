import httpx
import re
import uuid
from datetime import datetime

# MemberSports config
MEMBERSPORTS_API_URL = "https://api.membersports.com/api/v1/golfclubs/onlineBookingTeeTimes"
NGSW_URL = "https://app.membersports.com/ngsw.json"
APP_BASE_URL = "https://app.membersports.com"

# Chronogolf config
CHRONOGOLF_API_URL = "https://www.chronogolf.com/marketplace/v2/teetimes"

# CPS Golf config
CPS_GOLF_SITES = {
    "fossiltrace": {
        "base_url": "https://fossiltrace.cps.golf",
        "website_id": "b6c22f3a-944a-46e9-020e-08da90168fb2",
        "course_ids": "1,3,2"
    }
}

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
    # Fox Hollow / Homestead (MemberSports)
    {"provider": "membersports", "club_id": 3703, "course_id": 20589, "name": "Fox Hollow", "config_type": 0, "group_id": 7},
    {"provider": "membersports", "club_id": 3703, "course_id": 4902, "name": "Homestead", "config_type": 0, "group_id": 7},
    # South Suburban (Chronogolf)
    {"provider": "chronogolf", "course_id": "482fb33a-fa4a-48fb-85e1-e0492fe39d1a", "name": "SSG 18 Hole Course", "booking_slug": "south-suburban-golf-club"},
    {"provider": "chronogolf", "course_id": "68c1a9d5-f402-4d54-a1c5-991363899bc8", "name": "SSG 9 Hole Par 3", "booking_slug": "south-suburban-golf-club"},
    # Lone Tree (Chronogolf)
    {"provider": "chronogolf", "course_id": "001a7f2d-2c20-4bd9-8f91-3df9d051f737", "name": "Lone Tree 18 Hole", "booking_slug": "lone-tree-golf-club-hotel"},
    # Littleton (Chronogolf)
    {"provider": "chronogolf", "course_id": "6a1ad175-7c4f-4692-a58f-7879e72ed9e9", "name": "Littleton Golf & Tennis", "booking_slug": "littleton-golf-tennis-club"},
    # Family Sports (Chronogolf)
    {"provider": "chronogolf", "course_id": "34b44f75-a475-4ec1-b5d3-e3089b66cf86", "name": "Family Sports 9 Hole", "booking_slug": "family-sports-golf-course"},
    # Fossil Trace (CPS Golf)
    {"provider": "cpsgolf", "site": "fossiltrace", "name": "Fossil Trace"},
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

async def fetch_cpsgolf_tee_times(site: str, date: str):
    """Fetch tee times from CPS Golf sites like Fossil Trace."""
    config = CPS_GOLF_SITES.get(site)
    if not config:
        return {}
    
    # Convert YYYY-MM-DD to "Sat Jan 31 2026" format
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    formatted_date = date_obj.strftime("%a %b %d %Y")
    
    params = {
        "searchDate": formatted_date,
        "holes": 0,
        "numberOfPlayer": 0,
        "courseIds": config["course_ids"],
        "searchTimeType": 0,
        "transactionId": str(uuid.uuid4()),
        "teeOffTimeMin": 0,
        "teeOffTimeMax": 23,
        "isChangeTeeOffTime": "true",
        "teeSheetSearchView": 5,
        "classCode": "R",
        "defaultOnlineRate": "N",
        "isUseCapacityPricing": "false",
        "memberStoreId": 1,
        "searchType": 1
    }
    headers = {
        "Accept": "application/json, text/plain, */*",
        "client-id": "onlineresweb",
        "x-siteid": "1",
        "x-websiteid": config["website_id"],
        "x-terminalid": "3",
        "x-componentid": "1",
        "x-moduleid": "7",
        "x-productid": "1",
        "x-ismobile": "false",
        "x-timezoneid": "America/Denver",
        "x-timezone-offset": "420",
        "Referer": f"{config['base_url']}/onlineresweb/search-teetime",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    async with httpx.AsyncClient() as client:
        url = f"{config['base_url']}/onlineres/onlineapi/api/v1/onlinereservation/TeeTimes"
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            print(f"cpsgolf error: {resp.status_code} - {resp.text[:200]}")
            return {}
        try:
            return resp.json()
        except:
            print(f"cpsgolf JSON parse error: {resp.text[:200]}")
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
    elif provider == "cpsgolf":
        return await get_cpsgolf_times(course, date)
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

async def get_cpsgolf_times(course: dict, date: str):
    data = await fetch_cpsgolf_tee_times(course["site"], date)
    available = []
    if not isinstance(data, dict) or "content" not in data:
        return available
    for tt in data["content"]:
        # Parse ISO datetime to get time
        start_time = tt.get("startTime", "")  # e.g., "2026-01-31T13:50:00"
        if not start_time:
            continue
        time_parts = start_time.split("T")[1].split(":")
        time_minutes = int(time_parts[0]) * 60 + int(time_parts[1])
        
        # participants is max spots, we show all available times
        spots = tt.get("participants", 4)
        
        # Get price from first shItemPrices if available
        price = 0
        if tt.get("shItemPrices"):
            price = tt["shItemPrices"][0].get("displayPrice", 0)
        
        available.append({
            "course_id": tt.get("courseId"),
            "course_name": f"{course['name']} ({tt.get('courseName', '')})",
            "date": date,
            "time_minutes": time_minutes,
            "time_display": minutes_to_time(time_minutes),
            "spots_available": spots,
            "price": price,
            "holes": tt.get("holes", 18),
            "scraped_at": datetime.utcnow().isoformat()
        })
    return available
