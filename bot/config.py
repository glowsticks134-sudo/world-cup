import os

# Bot Configuration
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")

# Football API
FOOTBALL_API_BASE = "https://api.football-data.org/v4"
WORLD_CUP_COMPETITION_ID = 2000  # FIFA World Cup

# Database
DATABASE_PATH = "bot/data/worldcup.db"

# Update intervals (seconds)
LIVE_MATCH_UPDATE_INTERVAL = 60
NO_MATCH_UPDATE_INTERVAL = 300
LEADERBOARD_UPDATE_INTERVAL = 300
STATS_UPDATE_INTERVAL = 300

# Economy
DAILY_COINS = 100
PREDICTION_CORRECT_COINS = 200
PREDICTION_BONUS_EXACT_SCORE = 500
TRIVIA_COINS = 50
ACTIVITY_COINS = 10
GIVEAWAY_ENTRY_COINS = 25

# Colors (Discord embed hex)
COLOR_GOLD = 0xFFD700
COLOR_GREEN = 0x00A86B
COLOR_RED = 0xFF4444
COLOR_BLUE = 0x4169E1
COLOR_DARK = 0x1A1A2E
COLOR_WHITE = 0xFFFFFF

# Role names
ROLES = {
    "fan": "Fan",
    "super_fan": "Super Fan",
    "predictor": "Predictor",
    "champion": "World Cup Champion",
    "legend": "Legend",
}

# Point thresholds for roles
ROLE_THRESHOLDS = {
    "Fan": 0,
    "Super Fan": 500,
    "Predictor": 1000,
    "World Cup Champion": 3000,
    "Legend": 7500,
}

# Achievements
ACHIEVEMENTS = {
    "first_prediction": {"name": "First Blood", "desc": "Made your first prediction", "icon": "🎯", "coins": 50},
    "correct_10": {"name": "Sharp Eye", "desc": "Got 10 correct predictions", "icon": "👁️", "coins": 200},
    "correct_50": {"name": "Oracle", "desc": "Got 50 correct predictions", "icon": "🔮", "coins": 1000},
    "trivia_10": {"name": "Football Scholar", "desc": "Answered 10 trivia questions", "icon": "📚", "coins": 100},
    "streak_7": {"name": "Dedicated Fan", "desc": "Logged in 7 days in a row", "icon": "🔥", "coins": 300},
    "coins_1000": {"name": "Coin Collector", "desc": "Earned 1,000 Fan Coins", "icon": "💰", "coins": 0},
    "coins_10000": {"name": "Millionaire", "desc": "Earned 10,000 Fan Coins", "icon": "💎", "coins": 500},
    "transfer": {"name": "Generous Soul", "desc": "Transferred coins to another member", "icon": "🤝", "coins": 25},
}

# Country flag emojis
FLAGS = {
    "Argentina": "🇦🇷", "Brazil": "🇧🇷", "France": "🇫🇷", "Germany": "🇩🇪",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Spain": "🇪🇸", "Portugal": "🇵🇹", "Netherlands": "🇳🇱",
    "Belgium": "🇧🇪", "Italy": "🇮🇹", "Croatia": "🇭🇷", "Morocco": "🇲🇦",
    "Senegal": "🇸🇳", "Japan": "🇯🇵", "South Korea": "🇰🇷", "USA": "🇺🇸",
    "Mexico": "🇲🇽", "Uruguay": "🇺🇾", "Colombia": "🇨🇴", "Chile": "🇨🇱",
    "Algeria": "🇩🇿", "Nigeria": "🇳🇬", "Ghana": "🇬🇭", "Cameroon": "🇨🇲",
    "Poland": "🇵🇱", "Serbia": "🇷🇸", "Switzerland": "🇨🇭", "Denmark": "🇩🇰",
    "Sweden": "🇸🇪", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Australia": "🇦🇺",
    "Iran": "🇮🇷", "Saudi Arabia": "🇸🇦", "Tunisia": "🇹🇳", "Ecuador": "🇪🇨",
    "Qatar": "🇶🇦", "Canada": "🇨🇦", "Costa Rica": "🇨🇷", "Panama": "🇵🇦",
}

def get_flag(team_name: str) -> str:
    for name, flag in FLAGS.items():
        if name.lower() in team_name.lower() or team_name.lower() in name.lower():
            return flag
    return "🏳️"
