# AI Engagement Suite

This adds AI auto-reply, post generation, sentiment moderation and analytics on top of Threads-Bot-Factory.

## What's new

| File | Purpose |
|---|---|
| `ai_engine.py` | Provider-agnostic AI client (Gemini / Groq / OpenRouter) with auto-fallback. |
| `threads_engagement.py` | Threads Graph API: replies, conversation, mentions, hide, repost, insights. |
| `auto_reply_loop.py` | Background cycle: reads new comments → sentiment check → AI reply → publish. |
| `ai_post_generator.py` | Bulk-generate posts on a topic and queue them. |
| `ai_handlers.py` | Telegram commands `/ai_*`. |

## Free API keys

| Provider | Free tier | Get key |
|---|---|---|
| **Google Gemini** | 15 req/min, 1500/day | https://aistudio.google.com/apikey |
| **Groq** | Fast Llama 3.3 70B, free tier | https://console.groq.com |
| **OpenRouter** | Free models (`:free` suffix) | https://openrouter.ai |

Gemini is the most generous free tier and the recommended default.

## Setup

1. Copy `.env.example` → `.env`, fill keys.
2. `pip install -r requirements.txt`
3. Wire the handlers and scheduler into `bot.py` (one-time edit, see below).
4. Restart the bot.

### Wire into `bot.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ai_handlers import register_ai_handlers
from auto_reply_loop import run_auto_reply_cycle

# after dp = Dispatcher() and before bot start:
register_ai_handlers(dp)

scheduler = AsyncIOScheduler()
scheduler.add_job(run_auto_reply_cycle, 'interval', minutes=10)
scheduler.start()
```

## Telegram commands

- `/ai_test <prompt>`     — sanity-check the AI provider.
- `/ai_reply_on`          — enable auto-reply.
- `/ai_reply_off`         — disable.
- `/ai_reply_now`         — run one cycle immediately (manual trigger).
- `/ai_post topic | count | niche` — bulk generate & queue posts for every active account.
- `/ai_stats`             — AI activity dashboard.

## How auto-reply works

1. Scheduler fires every N minutes (`AI_REPLY_DELAY_MIN`).
2. For each active account: fetch your last 10 posts → pull replies.
3. Skip own replies and ones already handled (deduped via `ai_replies` table).
4. Run sentiment analysis. If `toxic` and `AI_SKIP_TOXIC=true` → hide reply, do not respond.
5. Generate AI reply, sleep human-like 60–300s, post via Threads API.
6. Daily limit per account: `AI_REPLY_DAILY_LIMIT` (default 40).

## DM / private messages

Threads does **not** expose a public DM API. Direct-message automation is not possible through official endpoints — only post replies, mentions and conversations are available.

## Roadmap ideas

- Auto-likes & reposts by hashtag/niche (uses `threads_engagement.repost`).
- Cross-posting from Threads → X / IG / Bluesky.
- AI image generation per post (Pollinations / Cloudflare Workers AI).
- Multi-language post packs.
- Web dashboard (extend `src/`).
- Telegram Stars billing (multi-tenant SaaS).
