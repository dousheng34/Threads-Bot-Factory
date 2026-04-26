# Koyeb Deployment Guide

This project deploys to **Koyeb** as a single web service running the Telegram bot + Threads OAuth callback handler + AI engagement worker.

## 1. Prerequisites

- Koyeb account: https://app.koyeb.com
- Repo connected: https://github.com/dousheng34/Threads-Bot-Factory
- Telegram bot token (from @BotFather)
- Threads App credentials (https://developers.facebook.com/apps)
- Gemini API key (https://aistudio.google.com/apikey)

## 2. Create Koyeb Secrets (one-time)

Dashboard → Secrets → New Secret. Create these:

| Secret name | Value |
|---|---|
| `bot_token` | Telegram bot token |
| `threads_app_id` | Threads App ID |
| `threads_app_secret` | Threads App Secret |
| `admin_ids` | Your Telegram user ID |
| `redirect_uri` | `https://<your-service>.koyeb.app/callback` (fill after first deploy) |
| `gemini_api_key` | Gemini key |
| `groq_api_key` | (optional) Groq key |
| `openrouter_api_key` | (optional) OpenRouter key |

## 3. Create Persistent Volume

Dashboard → Volumes → New Volume
- Name: `botdata`
- Region: same as service (e.g. `fra`)
- Size: 1 GB

This keeps the SQLite DB across redeploys. Without it the DB is wiped every push.

## 4. Deploy the Service

### Option A — Dashboard
1. Create Service → GitHub → select `Threads-Bot-Factory` / `main`
2. Builder: **Dockerfile** (auto-detected)
3. Instance: **nano** (0.1 vCPU / 512MB)
4. Region: `fra` (or closest)
5. Scaling: min=1, max=1 — **must stay at 1** (SQLite + scheduler are not multi-instance safe)
6. Port: `8080`, protocol HTTP, route `/`
7. Health check: HTTP path `/health`, port `8080`
8. Volume: mount `botdata` at `/app/data`
9. Env vars: import from secrets above
10. Deploy

### Option B — koyeb.yaml
The repo includes `koyeb.yaml` with the full config. Import it in Koyeb dashboard.

## 5. Set REDIRECT_URI

After the first deploy, Koyeb gives you a public URL like:
```
https://threads-bot-factory-<org>.koyeb.app
```
Update the `redirect_uri` secret to:
```
https://threads-bot-factory-<org>.koyeb.app/callback
```
Then redeploy. **Also add this exact URL** to Threads App settings → OAuth Redirect URIs.

## 6. Verify

- Visit `https://<your-service>.koyeb.app/health` — should return 200.
- Telegram: `/start` → main menu.
- Telegram: `/ai_test привет` — confirms AI provider works.
- Add a Threads account via `/start` → Add Account → OAuth flow.
- Telegram: `/ai_reply_on` to enable AI auto-reply.

## 7. Logs & Debugging

```bash
# Koyeb CLI
koyeb services logs threads-bot-factory/bot --tail
```
Or use the dashboard → Service → Logs.

## 8. Troubleshooting

**Bot doesn't start**
- Check `BOT_TOKEN` is set and valid.
- Check logs for missing env vars.

**OAuth redirect mismatch**
- `REDIRECT_URI` in Koyeb env MUST exactly match the URL registered in the Threads developer console.

**SQLite resets on every deploy**
- Volume not mounted. Check `/app/data` mount in service config.

**`/ai_test` returns nothing**
- Wrong / expired Gemini key, or rate-limited. Try `AI_PROVIDER=groq` or `openrouter`.

**Auto-reply does nothing**
- `AI_REPLY_ENABLED` is still `false`. Send `/ai_reply_on` in Telegram (toggles in-process).
- No active accounts in DB.
- Daily limit reached (`AI_REPLY_DAILY_LIMIT`).

## 9. Cost

- Koyeb nano instance: free tier covers this single service.
- Persistent volume 1GB: included in free tier.
- Gemini API: 1500 req/day free.
- Total: **$0** to run.
