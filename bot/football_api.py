import aiohttp
import asyncio
from datetime import datetime, timedelta
from config import FOOTBALL_API_BASE, FOOTBALL_API_KEY, WORLD_CUP_COMPETITION_ID

# In-memory cache
_cache: dict = {}
_cache_ttl: dict = {}

CACHE_SECONDS = 55  # Just under 60s update interval


def _cache_get(key: str):
    if key in _cache and datetime.utcnow() < _cache_ttl.get(key, datetime.min):
        return _cache[key]
    return None


def _cache_set(key: str, value, ttl: int = CACHE_SECONDS):
    _cache[key] = value
    _cache_ttl[key] = datetime.utcnow() + timedelta(seconds=ttl)


HEADERS = {"X-Auth-Token": FOOTBALL_API_KEY}


async def _fetch(endpoint: str, params: dict = None):
    url = f"{FOOTBALL_API_BASE}{endpoint}"
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 429:
                    print("⚠️ Football API rate limited.")
                    return None
                else:
                    print(f"⚠️ Football API error {resp.status}: {endpoint}")
                    return None
    except Exception as e:
        print(f"⚠️ Football API fetch failed: {e}")
        return None


async def get_live_matches():
    cached = _cache_get("live_matches")
    if cached is not None:
        return cached

    data = await _fetch(f"/competitions/{WORLD_CUP_COMPETITION_ID}/matches", {"status": "LIVE,IN_PLAY,PAUSED"})
    if not data:
        # fallback: try scheduled matches today
        data = await _fetch(f"/competitions/{WORLD_CUP_COMPETITION_ID}/matches", {"status": "LIVE"})

    result = []
    if data and "matches" in data:
        for m in data["matches"]:
            result.append(_parse_match(m))

    _cache_set("live_matches", result, 55)
    return result


async def get_todays_matches():
    cached = _cache_get("todays_matches")
    if cached is not None:
        return cached

    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = await _fetch(f"/competitions/{WORLD_CUP_COMPETITION_ID}/matches", {
        "dateFrom": today, "dateTo": today
    })

    result = []
    if data and "matches" in data:
        for m in data["matches"]:
            result.append(_parse_match(m))

    _cache_set("todays_matches", result, 300)
    return result


async def get_upcoming_matches(days=3):
    cached = _cache_get(f"upcoming_{days}")
    if cached is not None:
        return cached

    today = datetime.utcnow()
    end = today + timedelta(days=days)
    data = await _fetch(f"/competitions/{WORLD_CUP_COMPETITION_ID}/matches", {
        "dateFrom": today.strftime("%Y-%m-%d"),
        "dateTo": end.strftime("%Y-%m-%d"),
        "status": "SCHEDULED,TIMED"
    })

    result = []
    if data and "matches" in data:
        for m in data["matches"]:
            result.append(_parse_match(m))

    _cache_set(f"upcoming_{days}", result, 300)
    return result


async def get_standings():
    cached = _cache_get("standings")
    if cached is not None:
        return cached

    data = await _fetch(f"/competitions/{WORLD_CUP_COMPETITION_ID}/standings")
    result = []
    if data and "standings" in data:
        for group in data["standings"]:
            group_name = group.get("group", group.get("stage", "Group"))
            teams = []
            for t in group.get("table", []):
                teams.append({
                    "position": t["position"],
                    "team": t["team"]["name"],
                    "played": t["playedGames"],
                    "won": t["won"],
                    "draw": t["draw"],
                    "lost": t["lost"],
                    "gf": t["goalsFor"],
                    "ga": t["goalsAgainst"],
                    "gd": t["goalDifference"],
                    "points": t["points"],
                })
            result.append({"group": group_name, "table": teams})

    _cache_set("standings", result, 600)
    return result


async def get_scorers():
    cached = _cache_get("scorers")
    if cached is not None:
        return cached

    data = await _fetch(f"/competitions/{WORLD_CUP_COMPETITION_ID}/scorers", {"limit": 10})
    result = []
    if data and "scorers" in data:
        for s in data["scorers"]:
            result.append({
                "player": s["player"]["name"],
                "team": s["team"]["name"],
                "goals": s.get("goals", 0),
                "assists": s.get("assists", 0),
            })

    _cache_set("scorers", result, 600)
    return result


async def get_match(match_id: int):
    data = await _fetch(f"/matches/{match_id}")
    if data:
        return _parse_match(data)
    return None


def _parse_match(m: dict) -> dict:
    home = m.get("homeTeam", {})
    away = m.get("awayTeam", {})
    score = m.get("score", {})
    full = score.get("fullTime", {})
    half = score.get("halfTime", {})
    current = full if score.get("winner") else score.get("regularTime", score.get("currentPeriod", full))

    home_score = current.get("home") if current else None
    away_score = current.get("away") if current else None
    if home_score is None:
        home_score = half.get("home")
        away_score = half.get("away")

    status = m.get("status", "SCHEDULED")
    minute = None
    if m.get("minute"):
        minute = m["minute"]

    utc_date = m.get("utcDate", "")
    try:
        match_dt = datetime.fromisoformat(utc_date.replace("Z", "+00:00"))
    except Exception:
        match_dt = None

    return {
        "id": m.get("id"),
        "home": home.get("name", "TBD"),
        "away": away.get("name", "TBD"),
        "home_score": home_score,
        "away_score": away_score,
        "status": status,
        "minute": minute,
        "stage": m.get("stage", ""),
        "group": m.get("group", ""),
        "utc_date": utc_date,
        "match_dt": match_dt,
        "winner": score.get("winner"),
    }


def format_status(match: dict) -> str:
    status = match["status"]
    minute = match.get("minute")
    if status in ("IN_PLAY", "LIVE"):
        return f"🟢 LIVE {minute}'" if minute else "🟢 LIVE"
    elif status == "PAUSED":
        return "🟡 Halftime"
    elif status == "FINISHED":
        return "✅ Finished"
    elif status in ("SCHEDULED", "TIMED"):
        if match.get("match_dt"):
            return f"🕐 {match['match_dt'].strftime('%H:%M UTC')}"
        return "⏳ Scheduled"
    elif status == "POSTPONED":
        return "⚠️ Postponed"
    return status


# Fallback mock data for when API is unavailable / off-season
MOCK_MATCHES = [
    {
        "id": 999001, "home": "Argentina", "away": "France",
        "home_score": 3, "away_score": 3, "status": "FINISHED",
        "minute": 120, "stage": "FINAL", "group": None,
        "utc_date": "2022-12-18T15:00:00Z", "match_dt": None, "winner": "Argentina",
    },
    {
        "id": 999002, "home": "Brazil", "away": "Croatia",
        "home_score": 1, "away_score": 1, "status": "FINISHED",
        "minute": 120, "stage": "QUARTER_FINALS", "group": None,
        "utc_date": "2022-12-09T15:00:00Z", "match_dt": None, "winner": "Croatia",
    },
]
