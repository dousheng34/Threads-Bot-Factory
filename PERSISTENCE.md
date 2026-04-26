# Why does my data reset on every Koyeb deploy?

Koyeb destroys the container's filesystem on each redeploy. SQLite lives **inside** that filesystem unless you mount a persistent volume. Without a volume, every push wipes accounts, templates, scheduled posts — everything.

## Fix in 5 steps

1. **Create a Volume** (Koyeb Dashboard → Volumes → New Volume)
   - Name: `botdata`
   - Region: same as your service (e.g. `fra`)
   - Size: `1 GB`

2. **Mount the volume** on the service (Service → Settings → Volumes)
   - Volume: `botdata`
   - Mount path: `/app/data`

3. **Set env var** on the service (Service → Settings → Environment)
   ```
   DB_PATH=/app/data/bot_factory.db
   ```

4. **Force scaling min=1, max=1**
   SQLite + apscheduler are **not** safe for multiple instances. Multiple replicas would corrupt the DB and double-post.

5. **Redeploy.**

On first start with the new mount, `database.py` auto-copies the existing legacy DB (if any) into `/app/data/bot_factory.db`, so historical data is preserved.

## Verify it worked

- Telegram: `/ai_stats` — the message will print the active `DB path`. It must be `/app/data/bot_factory.db`.
- Trigger a deploy (push any commit). After the new container is up, your accounts/templates/scheduled posts must still be there.

## Belt and suspenders: Telegram backup commands

Even with a volume, you should have a copy outside Koyeb. Two new commands:

- `/backup` — the bot DMs you the live SQLite file (safe snapshot via `VACUUM INTO`).
- `/restore` — reply to a `.db` file in Telegram with `/restore` to overwrite the live DB. The previous DB is kept as `.before_restore_<ts>` next to it. **Restart the service afterwards.**

Recommended: run `/backup` every few days and pin the file in your Telegram Saved Messages.

## Ultimate option: external Postgres

If you ever scale beyond a single instance or want zero-maintenance backups, swap SQLite for Postgres (Neon / Supabase free tier). That requires rewriting `database.py` to use `asyncpg`. Ping me if you want this PR.
