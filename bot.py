import asyncio, json, os, logging
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from threads_api import publish_thread, process_spintax
from oauth import get_auth_url, pending_auth, start_oauth_server
import uuid

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8770252683:AAE78GVg0eaUKG6CoOsZIk9hrDuHYFaQc-A"
ADMIN_IDS = set()  # Auto-detection: first /start = admin

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()

# ============ HELPERS ============

def is_admin(user_id: int) -> bool:
          if not ADMIN_IDS:
                        return True  # First user automatically becomes admin
    return user_id in ADMIN_IDS

def main_menu_kb():
          return InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Accounts", callback_data="accounts"),
                                  InlineKeyboardButton(text="Posting", callback_data="posting")],
                        [InlineKeyboardButton(text="Automation", callback_data="automation"),
                                  InlineKeyboardButton(text="Proxies", callback_data="proxies")],
                        [InlineKeyboardButton(text="Templates", callback_data="templates"),
                                  InlineKeyboardButton(text="Stats", callback_data="stats")],
                        [InlineKeyboardButton(text="Settings", callback_data="settings")],
          ])

def back_kb():
          return InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Back to Menu", callback_data="menu")]
          ])

def accounts_kb():
          return InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Accounts List", callback_data="acc_list")],
                        [InlineKeyboardButton(text="OAuth Connect", callback_data="oauth_connect")],
                        [InlineKeyboardButton(text="Add Manually", callback_data="acc_add")],
                        [InlineKeyboardButton(text="Import Bulk", callback_data="acc_import")],
                        [InlineKeyboardButton(text="Back", callback_data="menu")],
          ])

def posting_kb():
          return InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="New Post", callback_data="post_new")],
                        [InlineKeyboardButton(text="Posts Queue", callback_data="post_queue")],
                        [InlineKeyboardButton(text="Mass Post", callback_data="post_mass")],
                        [InlineKeyboardButton(text="Back", callback_data="menu")],
          ])

def proxies_kb():
          return InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Proxies List", callback_data="proxy_list")],
                        [InlineKeyboardButton(text="Add Proxy", callback_data="proxy_add")],
                        [InlineKeyboardButton(text="Import Proxies", callback_data="proxy_import")],
                        [InlineKeyboardButton(text="Back", callback_data="menu")],
          ])

def templates_kb():
          return InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Templates List", callback_data="tmpl_list")],
                        [InlineKeyboardButton(text="New Template", callback_data="tmpl_add")],
                        [InlineKeyboardButton(text="Spintax Test", callback_data="tmpl_test")],
                        [InlineKeyboardButton(text="Back", callback_data="menu")],
          ])

# ============ STATE MANAGEMENT ============
user_states = {}

def set_state(user_id, state, data=None):
          user_states[user_id] = {"state": state, "data": data or {}}

def get_state(user_id):
          return user_states.get(user_id, {"state": None, "data": {}})

def clear_state(user_id):
          user_states.pop(user_id, None)

# ============ COMMANDS ============

@router.message(CommandStart())
async def cmd_start(message: Message):
          # Auto-registration of the first user as admin
          if not ADMIN_IDS:
                        ADMIN_IDS.add(message.from_user.id)
                        logging.info(f"Admin registered: {message.from_user.id} (@{message.from_user.username})")

          if not is_admin(message.from_user.id):
                        await message.answer("Access Denied")
                        return
                    await message.answer(
                                  "Threads Bot Factory\n\n"
                                  "Welcome to the control panel!\n"
                                  f"Admin: {message.from_user.id}\n"
                                  "Manage your Threads accounts directly from Telegram.\n\n"
                                  "Select a section:",
                                  reply_markup=main_menu_kb()
                    )

@router.message(Command("help"))
async def cmd_help(message: Message):
          if not is_admin(message.from_user.id): return
                    await message.answer(
                                  "Commands:\n\n"
                                  "/start - Main Menu\n"
                                  "/accounts - Accounts Management\n"
                                  "/post - Quick Post\n"
                                  "/mass - Mass Posting\n"
                                  "/stats - Statistics\n"
                                  "/templates - Templates\n"
                                  "/proxies - Proxies\n"
                                  "/help - Help\n\n"
                                  "Formats:\n"
                                  "Add account: /add username:token:user_id\n"
                                  "Quick post: /post ID post text\n"
                                  "Spintax: {option1|option2|option3}",
                                  reply_markup=back_kb()
                    )

@router.message(Command("accounts"))
async def cmd_accounts(message: Message):
          if not is_admin(message.from_user.id): return
                    await show_accounts_menu(message)

@router.message(Command("stats"))
async def cmd_stats(message: Message):
          if not is_admin(message.from_user.id): return
                    await show_stats(message)

@router.message(Command("add"))
async def cmd_add(message: Message):
          if not is_admin(message.from_user.id): return
                    args = message.text.split(maxsplit=1)
    if len(args) < 2:
                  await message.answer("Format: /add username:token:user_id", reply_markup=back_kb())
                  return
              parts = args[1].split(":")
    if len(parts) < 2:
                  await message.answer("Minimum: /add username:token", reply_markup=back_kb())
                  return
              username = parts[0].strip().lstrip("@")
    token = parts[1].strip()
    user_id = parts[2].strip() if len(parts) > 2 else ""
    acc_id = await db.add_account(username, token, user_id)
    await message.answer(
                  f"Account added!\n\n"
                  f"ID: {acc_id}\n"
                  f"Username: @{username}\n"
                  f"Token: {token[:20]}...",
                  reply_markup=back_kb()
    )

@router.message(Command("post"))
async def cmd_post(message: Message):
          if not is_admin(message.from_user.id): return
                    args = message.text.split(maxsplit=2)
    if len(args) < 3:
                  accounts = await db.get_accounts("active")
                  acc_list = "\n".join([f"  {a['id']}. @{a['username']}" for a in accounts]) or "  No accounts"
                  await message.answer(
                      "Quick Post\n\n"
                      "Format: /post ID text\n\n"
                      f"Available accounts:\n{acc_list}",
                      reply_markup=back_kb()
                  )
                  return

    try:
                  acc_id = int(args[1])
except ValueError:
        await message.answer("Error: Account ID must be a number", reply_markup=back_kb())
        return

    text = args[2]
    account = await db.get_account(acc_id)
    if not account:
                  await message.answer("Error: Account not found", reply_markup=back_kb())
                  return

    msg = await message.answer(f"Publishing to @{account['username']}...")
    result = await publish_thread(account["threads_user_id"], account["access_token"], text)

    if result["success"]:
                  await db.increment_posts_today(acc_id)
                  await db.log_post(acc_id, text, "success", result.get("thread_id"))
                  await msg.edit_text(
                      "Published!\n\n"
                      f"Username: @{account['username']}\n"
                      f"Text: {text[:100]}...\n"
                      f"Thread ID: {result.get('thread_id', 'N/A')}",
                      reply_markup=back_kb()
                  )
else:
        await db.log_post(acc_id, text, "failed", error=result.get("error"))
        await msg.edit_text(f"Error: {result.get('error', 'Unknown')}", reply_markup=back_kb())

@router.message(Command("mass"))
async def cmd_mass(message: Message):
          if not is_admin(message.from_user.id): return
                    args = message.text.split(maxsplit=1)
    if len(args) < 2:
                  await message.answer(
                                    "Mass Post\n\n"
                                    "Format: /mass post text\n"
                                    "Spintax supported: {opt1|opt2}\n\n"
                                    "The post will be sent to all active accounts.",
                                    reply_markup=back_kb()
                  )
                  return

    text = args[1]
    accounts = await db.get_accounts("active")
    if not accounts:
                  await message.answer("Error: No active accounts", reply_markup=back_kb())
                  return

    msg = await message.answer(f"Mass publishing to {len(accounts)} accounts...")
    success = 0
    failed = 0
    results_text = ""

    for acc in accounts:
                  post_text = process_spintax(text) if "{" in text and "|" in text else text
                  result = await publish_thread(acc["threads_user_id"], acc["access_token"], post_text)

        if result["success"]:
                          success += 1
                          await db.increment_posts_today(acc["id"])
                          await db.log_post(acc["id"], post_text, "success", result.get("thread_id"))
                          results_text += f"  OK: @{acc['username']}\n"
else:
            failed += 1
                  await db.log_post(acc["id"], post_text, "failed", error=result.get("error"))
            results_text += f"  FAIL: @{acc['username']}: {result.get('error','')[:30]}\n"

        await asyncio.sleep(2)  # Delay between posts

    await msg.edit_text(
                  "Mass Publication Finished!\n\n"
                  f"Success: {success}\nErrors: {failed}\n\n"
                  f"Results:\n{results_text}",
                  reply_markup=back_kb()
    )

# ============ CALLBACKS ============

@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery):
          await callback.message.edit_text(
                        "Threads Bot Factory\n\nSelect a section:",
                        reply_markup=main_menu_kb()
          )

@router.callback_query(F.data == "accounts")
async def cb_accounts(callback: CallbackQuery):
          await callback.message.edit_text("Accounts Management\n\nSelect an operation:", reply_markup=accounts_kb())

@router.callback_query(F.data == "acc_list")
async def cb_acc_list(callback: CallbackQuery):
          accounts = await db.get_accounts()
    if not accounts:
                  await callback.message.edit_text("No accounts found.\n\nAdd one using: /add user:token:id", reply_markup=accounts_kb())
                  return

    status_emoji = {"active":"OK","warming":"Warming","banned":"Banned","limited":"Limited","inactive":"Inactive"}
    text = "Accounts List:\n\n"
    for a in accounts:
                  emoji = status_emoji.get(a["status"], "Inactive")
                  text += (f"[{emoji}] #{a['id']} @{a['username']}\n"
                          f"   Posts: {a['posts_count']} | Today: {a['posts_today']}/{a['daily_limit']}\n")

    btns = [[InlineKeyboardButton(text=f"Delete #{a['id']}", callback_data=f"acc_del_{a['id']}")] for a in accounts[:5]]
    btns.append([InlineKeyboardButton(text="Back", callback_data="accounts")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("acc_del_"))
async def cb_acc_del(callback: CallbackQuery):
          acc_id = int(callback.data.split("_")[-1])
    await db.delete_account(acc_id)
    await callback.answer(f"Account #{acc_id} deleted!")
    await cb_acc_list(callback)

@router.callback_query(F.data == "acc_add")
async def cb_acc_add(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_account")
    await callback.message.edit_text(
                  "Add Account\n\n"
                  "Send the data in format:\n"
                  "username:access_token:threads_user_id\n\n"
                  "Or minimum:\n"
                  "username:access_token",
                  reply_markup=back_kb()
    )

@router.callback_query(F.data == "acc_import")
async def cb_acc_import(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_import")
    await callback.message.edit_text(
                  "Bulk Import\n\n"
                  "Send the accounts one per line:\n"
                  "username:token:user_id\nusername2:token2:user_id2",
                  reply_markup=back_kb()
    )

# ---- Posting ----
@router.callback_query(F.data == "posting")
async def cb_posting(callback: CallbackQuery):
          await callback.message.edit_text("Posting\n\nManage your publications:", reply_markup=posting_kb())

@router.callback_query(F.data == "post_new")
async def cb_post_new(callback: CallbackQuery):
          accounts = await db.get_accounts("active")
    if not accounts:
                  await callback.message.edit_text("Error: No active accounts", reply_markup=posting_kb())
                  return
              btns = [[InlineKeyboardButton(text=f"@{a['username']}", callback_data=f"post_to_{a['id']}")] for a in accounts]
    btns.append([InlineKeyboardButton(text="Mass Post", callback_data="post_to_all")])
    btns.append([InlineKeyboardButton(text="Back", callback_data="posting")])
    await callback.message.edit_text("Select an account for the post:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("post_to_"))
async def cb_post_to(callback: CallbackQuery):
          target = callback.data.replace("post_to_", "")
    set_state(callback.from_user.id, "waiting_post", {"target": target})
    if target == "all":
                  await callback.message.edit_text("Write the post text (will be sent to all accounts):\n\nSpintax: {opt1|opt2}", reply_markup=back_kb())
else:
        acc = await db.get_account(int(target))
        name = acc["username"] if acc else target
        await callback.message.edit_text(f"Write the post text for @{name}:", reply_markup=back_kb())

@router.callback_query(F.data == "post_queue")
async def cb_post_queue(callback: CallbackQuery):
          posts = await db.get_scheduled_posts()
    if not posts:
                  await callback.message.edit_text("Queue is empty", reply_markup=posting_kb())
                  return
              status_e = {"pending":"Waiting","published":"OK","failed":"Error","cancelled":"Cancelled"}
    text = "Posts Queue:\n\n"
    for p in posts[:10]:
                  e = status_e.get(p["status"], "Unknown")
                  text += f"[{e}] #{p['id']} - {p['content'][:40]}...\n   Date: {p['scheduled_at']}\n\n"
              await callback.message.edit_text(text, reply_markup=posting_kb())

@router.callback_query(F.data == "post_mass")
async def cb_post_mass(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_post", {"target": "all"})
    await callback.message.edit_text(
                  "Mass Post\n\n"
                  "Write the text - it will be published to all active accounts.\n"
                  "Spintax supported: {hello|hi|hey}",
                  reply_markup=back_kb()
    )

# ---- Proxies ----
@router.callback_query(F.data == "proxies")
async def cb_proxies(callback: CallbackQuery):
          await callback.message.edit_text("Proxies\n\nManage proxy servers:", reply_markup=proxies_kb())

@router.callback_query(F.data == "proxy_list")
async def cb_proxy_list(callback: CallbackQuery):
          proxies = await db.get_proxies()
    if not proxies:
                  await callback.message.edit_text("No proxies added", reply_markup=proxies_kb())
                  return
              status_e = {"active":"OK","dead":"Dead","slow":"Slow"}
    text = "Proxies:\n\n"
    for p in proxies:
                  e = status_e.get(p["status"], "Unknown")
                  text += f"[{e}] #{p['id']} {p['host']}:{p['port']} ({p['protocol']})\n   {p['country']} | {p['response_time']}ms\n\n"
              await callback.message.edit_text(text, reply_markup=proxies_kb())

@router.callback_query(F.data == "proxy_add")
async def cb_proxy_add(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_proxy")
    await callback.message.edit_text(
                  "Add Proxy\n\nFormat:\nprotocol://user:pass@host:port\n\nExample:\nsocks5://user:pass@1.2.3.4:1080",
                  reply_markup=back_kb()
    )

@router.callback_query(F.data == "proxy_import")
async def cb_proxy_import(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_proxy_import")
    await callback.message.edit_text("Bulk Import Proxies\n\nSend proxies one per line:\nprotocol://user:pass@host:port", reply_markup=back_kb())

# ---- Templates ----
@router.callback_query(F.data == "templates")
async def cb_templates(callback: CallbackQuery):
          await callback.message.edit_text("Templates\n\nManage content templates:", reply_markup=templates_kb())

@router.callback_query(F.data == "tmpl_list")
async def cb_tmpl_list(callback: CallbackQuery):
          templates = await db.get_templates()
    if not templates:
                  await callback.message.edit_text("No templates found. Create a new one!", reply_markup=templates_kb())
                  return
              text = "Templates:\n\n"
    for t in templates:
                  text += f"#{t['id']} {t['name']}\n   {t['content'][:50]}...\n   Used: {t['usage_count']} times\n\n"
              btns = [[InlineKeyboardButton(text=f"Use #{t['id']}", callback_data=f"tmpl_use_{t['id']}")] for t in templates[:5]]
    btns.append([InlineKeyboardButton(text="Back", callback_data="templates")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data == "tmpl_add")
async def cb_tmpl_add(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_template_name")
    await callback.message.edit_text("Enter template name:", reply_markup=back_kb())

@router.callback_query(F.data == "tmpl_test")
async def cb_tmpl_test(callback: CallbackQuery):
          set_state(callback.from_user.id, "waiting_spintax_test")
    await callback.message.edit_text(
                  "Spintax Test\n\nSend text with Spintax:\n{hello|hi|hey}, {how are you|what's up}? {!!|??|..}",
                  reply_markup=back_kb()
    )

@router.callback_query(F.data.startswith("tmpl_use_"))
async def cb_tmpl_use(callback: CallbackQuery):
          tmpl_id = int(callback.data.split("_")[-1])
    tmpl = await db.get_template(tmpl_id)
    if not tmpl:
                  await callback.answer("Error: Template not found")
                  return
              generated = process_spintax(tmpl["content"])
    await db.increment_template_usage(tmpl_id)
    accounts = await db.get_accounts("active")
    btns = [[InlineKeyboardButton(text=f"Send to @{a['username']}", callback_data=f"tmpl_send_{tmpl_id}_{a['id']}")] for a in accounts[:5]]
    btns.append([InlineKeyboardButton(text="All Accounts", callback_data=f"tmpl_send_{tmpl_id}_all")])
    btns.append([InlineKeyboardButton(text="Regenerate", callback_data=f"tmpl_use_{tmpl_id}")])
    btns.append([InlineKeyboardButton(text="Back", callback_data="tmpl_list")])
    await callback.message.edit_text(f"Generated Text:\n\n{generated}", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

# ---- Stats ----
@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
          await show_stats(callback.message, edit=True)

# ---- Settings ----
@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
          await callback.message.edit_text(
                        "Settings\n\n"
                        "Threads API:\n"
                        f"  App ID: {os.getenv('THREADS_APP_ID', 'not set')}\n\n"
                        "Threads API Limits:\n"
                        "  - 250 posts / 24 hours\n"
                        "  - 2-step publication\n"
                        "  - Token valid for 60 days\n\n",
                        reply_markup=back_kb()
          )

# ============ TEXT HANDLERS (STATE) ============

@router.message(F.text)
async def handle_text(message: Message):
          if not is_admin(message.from_user.id): return
                    state = get_state(message.from_user.id)

    if state["state"] == "waiting_account":
                  clear_state(message.from_user.id)
                  parts = message.text.split(":")
                  if len(parts) < 2:
                                    await message.answer("Error: Invalid format. Use: username:token", reply_markup=accounts_kb())
                                    return
                                username = parts[0].strip().lstrip("@")
        token = parts[1].strip()
        uid = parts[2].strip() if len(parts) > 2 else ""
        acc_id = await db.add_account(username, token, uid)
        await message.answer(f"Account @{username} added! (ID: {acc_id})", reply_markup=accounts_kb())

elif state["state"] == "waiting_import":
        clear_state(message.from_user.id)
        lines = message.text.strip().split("\n")
        added = 0
        for line in lines:
                          parts = line.strip().split(":")
                          if len(parts) >= 2:
                                                await db.add_account(parts[0].strip().lstrip("@"), parts[1].strip(), parts[2].strip() if len(parts) > 2 else "")
                                                added += 1
                                        await message.answer(f"Imported: {added} accounts", reply_markup=accounts_kb())

elif state["state"] == "waiting_post":
        clear_state(message.from_user.id)
        target = state["data"].get("target", "all")
        text = message.text

        if target == "all":
                          accounts = await db.get_accounts("active")
            if not accounts:
                                  await message.answer("Error: No active accounts", reply_markup=posting_kb())
                                  return
                              msg = await message.answer(f"Publishing to {len(accounts)} accounts...")
            ok, fail = 0, 0
            for acc in accounts:
                                  post_text = process_spintax(text) if "{" in text and "|" in text else text
                                  result = await publish_thread(acc["threads_user_id"], acc["access_token"], post_text)
                                  if result["success"]:
                                                            ok += 1
                                                            await db.increment_posts_today(acc["id"])
                                                            await db.log_post(acc["id"], post_text, "success", result.get("thread_id"))
else:
                    fail += 1
                    await db.log_post(acc["id"], post_text, "failed", error=result.get("error"))
                await asyncio.sleep(2)
            await msg.edit_text(f"Done! OK: {ok} | Fail: {fail}", reply_markup=posting_kb())
else:
            acc = await db.get_account(int(target))
            if not acc:
                                  await message.answer("Error: Account not found", reply_markup=posting_kb())
                                  return
                              msg = await message.answer(f"Publishing to @{acc['username']}...")
            result = await publish_thread(acc["threads_user_id"], acc["access_token"], text)
            if result["success"]:
                                  await db.increment_posts_today(acc["id"])
                                  await db.log_post(acc["id"], text, "success", result.get("thread_id"))
                                  await msg.edit_text(f"Published to @{acc['username']}!", reply_markup=posting_kb())
else:
                await db.log_post(acc["id"], text, "failed", error=result.get("error"))
                await msg.edit_text(f"Error: {result.get('error','')}", reply_markup=posting_kb())

elif state["state"] == "waiting_proxy":
        clear_state(message.from_user.id)
        import re
        m = re.match(r'^(https?|socks5)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$', message.text.strip())
        if not m:
                          await message.answer("Error: Invalid format. Use: protocol://user:pass@host:port", reply_markup=proxies_kb())
            return
        pid = await db.add_proxy(m.group(4), int(m.group(5)), m.group(2) or "", m.group(3) or "", m.group(1))
        await message.answer(f"Proxy added! (ID: {pid})", reply_markup=proxies_kb())

elif state["state"] == "waiting_proxy_import":
        clear_state(message.from_user.id)
        import re
        lines = message.text.strip().split("\n")
        added = 0
        for line in lines:
                          m = re.match(r'^(https?|socks5)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$', line.strip())
            if m:
                                  await db.add_proxy(m.group(4), int(m.group(5)), m.group(2) or "", m.group(3) or "", m.group(1))
                                  added += 1
                          await message.answer(f"Imported: {added} proxies", reply_markup=proxies_kb())

elif state["state"] == "waiting_template_name":
        set_state(message.from_user.id, "waiting_template_content", {"name": message.text})
        await message.answer("Enter template content:\n\nSpintax: {opt1|opt2}", reply_markup=back_kb())

elif state["state"] == "waiting_template_content":
        name = state["data"]["name"]
        content = message.text
        clear_state(message.from_user.id)
        tid = await db.add_template(name, content)
        await message.answer(f"Template  "{name}" created! (ID: {tid})", reply_markup=templates_kb())

            elif state["state"] == "waiting_spintax_test":
                    clear_state(message.from_user.id)
                            results = [process_spintax(message.text) for _ in range(3)]
                                    text = "Spintax Test Results:\n\n"
                                            for i, r in enumerate(results, 1):
                                                        text += f"  {i}. {r}\n\n"
                                                                await message.answer(text, reply_markup=templates_kb())

                                                                    elif state["state"] == "waiting_automation":
                                                                            clear_state(message.from_user.id)
                                                                                    await message.answer("Automation will be started!", reply_markup=back_kb())
                                                                                        else:
                                                                                                # Default: show menu
                                                                                                        await message.answer("Use /start for main menu", reply_markup=main_menu_kb())
                                                                                                        
                                                                                                        # ============ HELPERS ============
                                                                                                        
                                                                                                        async def show_accounts_menu(message: Message):
                                                                                                            await message.answer("Accounts Management\n\nSelect an operation:", reply_markup=accounts_kb())
                                                                                                            
                                                                                                            async def show_stats(message: Message, edit=False):
                                                                                                                stats = await db.get_post_stats()
                                                                                                                    text = (
                                                                                                                            "Statistics\n\n"
                                                                                                                                    f"Accounts: {stats['total_accounts']} ({stats['active_accounts']} active)\n"
                                                                                                                                            f"Active Proxies: {stats['active_proxies']}\n\n"
                                                                                                                                                    f"Total Posts: {stats['total_posts']}\n"
                                                                                                                                                            f"Today: {stats['today_posts']}\n"
                                                                                                                                                                    f"Success Rate: {stats['success_rate']}%\n"
                                                                                                                                                                        )
                                                                                                                                                                            if edit:
                                                                                                                                                                                    await message.edit_text(text, reply_markup=back_kb())
                                                                                                                                                                                        else:
                                                                                                                                                                                                await message.answer(text, reply_markup=back_kb())
                                                                                                                                                                                                
                                                                                                                                                                                                # ============ OAUTH ============
                                                                                                                                                                                                
                                                                                                                                                                                                @router.message(Command("connect"))
                                                                                                                                                                                                async def cmd_connect(message: Message):
                                                                                                                                                                                                    if not is_admin(message.from_user.id): return
                                                                                                                                                                                                        state = str(uuid.uuid4())[:8]
                                                                                                                                                                                                            pending_auth[state] = message.from_user.id
                                                                                                                                                                                                                auth_url = get_auth_url(state)
                                                                                                                                                                                                                    await message.answer(
                                                                                                                                                                                                                            "Connect Threads Account\n\n"
                                                                                                                                                                                                                                    "Click the button below and authorize:\n",
                                                                                                                                                                                                                                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                                                                                                                                                                                                                                        [InlineKeyboardButton(text="Authorize in Threads", url=auth_url)],
                                                                                                                                                                                                                                                                    [InlineKeyboardButton(text="Back", callback_data="menu")]
                                                                                                                                                                                                                                                                            ])
                                                                                                                                                                                                                                                                                )
                                                                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                                @router.callback_query(F.data == "oauth_connect")
                                                                                                                                                                                                                                                                                async def cb_oauth_connect(callback: CallbackQuery):
                                                                                                                                                                                                                                                                                    state = str(uuid.uuid4())[:8]
                                                                                                                                                                                                                                                                                        pending_auth[state] = callback.from_user.id
                                                                                                                                                                                                                                                                                            auth_url = get_auth_url(state)
                                                                                                                                                                                                                                                                                                await callback.message.edit_text(
                                                                                                                                                                                                                                                                                                        "Connect Threads Account\n\n"
                                                                                                                                                                                                                                                                                                                "Click the button below and authorize via Threads:\n",
                                                                                                                                                                                                                                                                                                                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                                                                                                                                                                                                                                                                                                                    [InlineKeyboardButton(text="Authorize", url=auth_url)],
                                                                                                                                                                                                                                                                                                                                                [InlineKeyboardButton(text="Back", callback_data="accounts")]
                                                                                                                                                                                                                                                                                                                                                        ])
                                                                                                                                                                                                                                                                                                                                                            )
                                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                            # ============ SCHEDULER ============
                                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                            async def check_scheduled_posts():
                                                                                                                                                                                                                                                                                                                                                                """Check and publish scheduled posts"""
                                                                                                                                                                                                                                                                                                                                                                    posts = await db.get_pending_posts()
                                                                                                                                                                                                                                                                                                                                                                        for post in posts:
                                                                                                                                                                                                                                                                                                                                                                                account_ids = json.loads(post["account_ids"])
        for acc_id in account_ids:
                    acc = await db.get_account(acc_id)
                                if not acc or acc["status"] != "active":
                                                continue
                                                            text = process_spintax(post["content"]) if post["use_spintax"] else post["content"]
                                                                        result = await publish_thread(acc["threads_user_id"], acc["access_token"], text)
                                                                                    if result["success"]:
                                                                                                    await db.increment_posts_today(acc_id)
                                                                                                                    await db.log_post(acc_id, text, "success", result.get("thread_id"))
                                                                                                                                else:
                                                                                                                                                await db.log_post(acc_id, text, "failed", error=result.get("error"))
                                                                                                                                                            await asyncio.sleep(2)
                                                                                                                                                                    status = "published"
                                                                                                                                                                            await db.update_post_status(post["id"], status)
                                                                                                                                                                            
                                                                                                                                                                            async def reset_daily_counters():
                                                                                                                                                                                """Reset daily counters"""
                                                                                                                                                                                    await db.reset_daily_posts()
                                                                                                                                                                                    
                                                                                                                                                                                    # ============ HEALTH CHECK (for Koyeb) ============
                                                                                                                                                                                    
                                                                                                                                                                                    async def health_handler(request):
                                                                                                                                                                                        return web.Response(text="OK", status=200)
                                                                                                                                                                                        
                                                                                                                                                                                        async def start_health_server():
                                                                                                                                                                                            """Health-check server for Koyeb"""
                                                                                                                                                                                                from aiohttp import web as aio_web
                                                                                                                                                                                                    app = aio_web.Application()
                                                                                                                                                                                                        app.router.add_get("/health", health_handler)
                                                                                                                                                                                                            app.router.add_get("/", health_handler)
                                                                                                                                                                                                                port = int(os.environ.get("PORT", 8000))
                                                                                                                                                                                                                    runner = aio_web.AppRunner(app)
                                                                                                                                                                                                                        await runner.setup()
                                                                                                                                                                                                                            site = aio_web.TCPSite(runner, "0.0.0.0", port)
                                                                                                                                                                                                                                await site.start()
                                                                                                                                                                                                                                    logging.info(f"Health-check server on port {port}")
                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                    # ============ MAIN ============
                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                    async def main():
                                                                                                                                                                                                                                        await db.init_db()
                                                                                                                                                                                                                                            dp.include_router(router)
                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                # Health-check server for Koyeb
                                                                                                                                                                                                                                                    await start_health_server()
                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                        # OAuth server
                                                                                                                                                                                                                                                            oauth_runner = await start_oauth_server(5000)
                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                # Scheduler
                                                                                                                                                                                                                                                                    scheduler.add_job(check_scheduled_posts, 'interval', minutes=1)
                                                                                                                                                                                                                                                                        scheduler.add_job(reset_daily_counters, 'cron', hour=0, minute=0)
                                                                                                                                                                                                                                                                            scheduler.start()
                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                logging.info("Threads Bot Factory started!")
                                                                                                                                                                                                                                                                                    logging.info("OAuth server: http://localhost:5000/callback")
                                                                                                                                                                                                                                                                                        await dp.start_polling(bot)
                                                                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                                                                        if __name__ == "__main__":
                                                                                                                                                                                                                                                                                            asyncio.run(main())
                                                                                                                                                                                                                                                                                            
