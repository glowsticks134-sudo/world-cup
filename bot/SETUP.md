# ⚽ World Cup Festival Bot — Setup Guide

## Quick Start

### 1. Secrets Required
In Replit Secrets, set:
- `DISCORD_TOKEN` — Your bot's token from Discord Developer Portal
- `FOOTBALL_API_KEY` — Free key from football-data.org

### 2. Discord Bot Permissions
When inviting the bot, ensure these permissions:
- Read Messages / View Channels
- Send Messages
- Embed Links
- Manage Roles
- Manage Channels
- Kick/Ban Members
- Moderate Members (for timeouts)
- Use Application Commands

**Required Intents (in Developer Portal → Bot):**
- ✅ Server Members Intent
- ✅ Message Content Intent
- ✅ Presence Intent (optional)

### 3. Run the Bot
The bot starts automatically via the workflow. Check logs to confirm it's online.

### 4. First-Time Server Setup

Use `/setup_all` to configure all channels at once:
```
/setup_all
  live: #live-scores
  leaderboard: #leaderboard
  stats: #server-stats
  bracket: #tournament-tracker
  notifications: #match-alerts
```

Or set channels individually:
- `/setup_live #channel` — Live match scores (auto-updates every 60s)
- `/setup_leaderboard #channel` — Prediction leaderboard (auto-updates every 5m)
- `/setup_stats #channel` — Server statistics (auto-updates every 5m)
- `/setup_bracket #channel` — Group standings & scorers (auto-updates every 10m)
- `/setup_notifications #channel` — Goal/kickoff/halftime alerts
- `/setup_log #channel` — Mod log channel

### 5. Create Roles (Optional)
Create these roles in your server for the bot to assign:
- `Fan` — Auto-assigned to new members
- `Super Fan` — Purchasable in `/shop`
- `Predictor` — For active predictors
- `World Cup Champion` — Top tier
- `Legend` — Elite status

### 6. Dynamic Voice Channel (Optional)
Use `/create_wc_voice` to create a voice channel that automatically renames
to show live match scores or member count.

---

## All Commands

### ⚽ Match Info
| Command | Description |
|---------|-------------|
| `/worldcup` | Main hub dashboard with dropdown menu |
| `/live` | Current live match scores |
| `/schedule` | Upcoming fixtures |
| `/standings` | Group stage standings |
| `/scorers` | Tournament top scorers |

### 🎯 Predictions
| Command | Description |
|---------|-------------|
| `/predict` | Predict match winner (earns 200 coins + 100 pts if correct) |
| `/mypredictions` | Your prediction history |
| `/leaderboard` | Top predictors by points |
| `/mypoints` | Your stats and server rank |

### 💰 Economy
| Command | Description |
|---------|-------------|
| `/balance` | Your Fan Coin balance |
| `/daily` | Claim daily coins (streak bonuses!) |
| `/transfer @user amount` | Send coins to a member |
| `/shop` | Buy items with Fan Coins |
| `/richlist` | Top coin holders |

### 🎮 Games
| Command | Description |
|---------|-------------|
| `/trivia` | Football trivia for coins |
| `/achievements` | Your earned badges |

### 🛠️ Admin
| Command | Description |
|---------|-------------|
| `/setup_all` | Configure all channels at once |
| `/setup_live` | Set live scores channel |
| `/setup_leaderboard` | Set leaderboard channel |
| `/setup_stats` | Set stats channel |
| `/setup_bracket` | Set tournament tracker channel |
| `/setup_notifications` | Set match alert channel |
| `/setup_log` | Set mod log channel |
| `/admin_coins add/remove @user amount` | Manage coins |
| `/admin_points add/remove @user amount` | Manage points |
| `/event start` | Trigger a Hype Train event |
| `/event announcement` | Post official announcement |
| `/giveaway prize: duration: channel:` | Start a giveaway |
| `/giveaway_end id` | End a giveaway early |
| `/award_achievement @user key` | Manually award a badge |
| `/reset_leaderboard` | Reset all predictions |
| `/create_wc_voice` | Create dynamic voice channel |
| `/kick @user` | Kick a member |
| `/ban @user` | Ban a member |
| `/timeout @user minutes` | Timeout a member |
| `/purge amount` | Delete messages (max 100) |

---

## Coin Earning Guide
| Action | Coins |
|--------|-------|
| Daily claim (base) | 100 🪙 |
| Streak bonus (per day) | +10 🪙 (max +200) |
| Correct prediction | 200 🪙 + 100 pts |
| Exact score prediction | +500 🪙 bonus |
| Trivia correct | 50 🪙 |
| Joining server | 100 🪙 welcome bonus |
| Hype Train event | 50-100 🪙 |
| Achievement unlock | Varies |

---

## Football API Notes
- Free tier: 10 requests/minute, 100/day
- The bot caches responses (55s for live, 5min for others)
- If the World Cup isn't active, the API returns historical data
- Competition ID 2000 = FIFA World Cup
