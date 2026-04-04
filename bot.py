import asyncio, json, os, logging
from datetime import datetime
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
ADMIN_IDS = [0]

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()

user_states = {}

def is_admin(uid):
      return uid in ADMIN_IDS

def set_state(uid, state, data=None):
      user_states[uid] = {"state": state, "data": data or {}}

def get_state(uid):
      return user_states.get(uid, {"state": None, "data": {}})

def clear_state(uid):
      user_states.pop(uid, None)

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
                [InlineKeyboardButton(text="<< Main Menu", callback_data="menu")]
      ])

def accounts_kb():
      return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Account List", callback_data="acc_list")],
                [InlineKeyboardButton(text="OAuth Connect", callback_data="oauth_connect")],
                [InlineKeyboardButton(text="Add Manual", callback_data="acc_add")],
                [InlineKeyboardButton(text="Import Bulk", callback_data="acc_import")],
                [InlineKeyboardButton(text="<< Back", callback_data="menu")],
      ])

def posting_kb():
      return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="New Post", callback_data="post_new")],
                [InlineKeyboardButton(text="Post Queue", callback_data="post_queue")],
                [InlineKeyboardButton(text="Mass Post", callback_data="post_mass")],
                [InlineKeyboardButton(text="<< Back", callback_data="menu")],
      ])

def proxies_kb():
      return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Proxy List", callback_data="proxy_list")],
                [InlineKeyboardButton(text="Add Proxy", callback_data="proxy_add")],
                [InlineKeyboardButton(text="Import Proxies", callback_data="proxy_import")],
                [InlineKeyboardButton(text="<< Back", callback_data="menu")],
      ])

def templates_kb():
      return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Template List", callback_data="tmpl_list")],
                [InlineKeyboardButton(text="New Template", callback_data="tmpl_add")],
                [InlineKeyboardButton(text="Test Spintax", callback_data="tmpl_test")],
                [InlineKeyboardButton(text="<< Back", callback_data="menu")],
      ])

def stats_kb():
      return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="<< Back", callback_data="menu")]
      ])

def settings_kb():
      return InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Admin List", callback_data="set_admins")],
                [InlineKeyboardButton(text="<< Back", callback_data="menu")]
      ])


@router.message(CommandStart())
async def cmd_start(message: Message):
      if not is_admin(message.from_user.id):
                return
    await message.answer(
                      "<b>Threads Bot Factory</b>\n\nWelcome! Select a section:",
                      reply_markup=main_menu_kb()
            )

@router.message(Command("help"))
async def cmd_help(message: Message):
      if not is_admin(message.from_user.id): return
            await message.answer(
                      "<b>Commands:</b>\n\n"
                      "/start - Main menu\n"
                      "/accounts - Manage accounts\n"
                      "/post ID text - Quick post\n"
                      "/mass text - Mass post\n"
                      "/stats - Statistics\n"
                      "/help - Help",
                      reply_markup=back_kb()
            )

@router.message(Command("add"))
async def cmd_add(message: Message):
      if not is_admin(message.from_user.id): return
            args = message.text.split(maxsplit=1)
    if len(args) < 2:
              await message.answer("Format: <code>/add username:token:user_id</code>", reply_markup=back_kb())
              return
          parts = args[1].split(":")
    if len(parts) < 2:
              await message.answer("Min: <code>/add username:token</code>", reply_markup=back_kb())
              return
          username = parts[0].strip().lstrip("@")
    token = parts[1].strip()
    user_id = parts[2].strip() if len(parts) > 2 else ""
    acc_id = await db.add_account(username, token, user_id)
    await message.answer(f"Account added! ID: {acc_id}, @{username}", reply_markup=back_kb())

@router.message(Command("post"))
async def cmd_post(message: Message):
      if not is_admin(message.from_user.id): return
            args = message.text.split(maxsplit=2)
    if len(args) < 3:
              accounts = await db.get_accounts("active")
              acc_list = "\n".join([f"  {a['id']}. @{a['username']}" for a in accounts]) or "  No accounts"
              await message.answer(f"<b>Quick Post</b>\n\nFormat: <code>/post ID text</code>\n\nAccounts:\n{acc_list}", reply_markup=back_kb())
              return
          try:
                    acc_id = int(args[1])
except ValueError:
        await message.answer("Account ID must be a number", reply_markup=back_kb())
        return
    text = args[2]
    account = await db.get_account(acc_id)
    if not account:
              await message.answer("Account not found", reply_markup=back_kb())
              return
          msg = await message.answer(f"Publishing to @{account['username']}...")
    result = await publish_thread(account["threads_user_id"], account["access_token"], text)
    if result["success"]:
              await db.increment_posts_today(acc_id)
              await db.log_post(acc_id, text, "success", result.get("thread_id"))
              await msg.edit_text(f"Published! @{account['username']}\nThread ID: {result.get('thread_id','N/A')}", reply_markup=back_kb())
else:
        await db.log_post(acc_id, text, "failed", error=result.get("error"))
          await msg.edit_text(f"Error: {result.get('error','Unknown')}", reply_markup=back_kb())

@router.message(Command("mass"))
async def cmd_mass(message: Message):
      if not is_admin(message.from_user.id): return
            args = message.text.split(maxsplit=1)
    if len(args) < 2:
              await message.answer("<b>Mass Post</b>\n\nFormat: <code>/mass text</code>\nSupports spintax.", reply_markup=back_kb())
              return
          text = args[1]
    accounts = await db.get_accounts("active")
    if not accounts:
              await message.answer("No active accounts", reply_markup=back_kb())
              return
          msg = await message.answer(f"Mass posting to {len(accounts)} accounts...")
    success = 0
    failed = 0
    for acc in accounts:
              post_text = process_spintax(text) if "{" in text and "|" in text else text
              result = await publish_thread(acc["threads_user_id"], acc["access_token"], post_text)
              if result["success"]:
                            success += 1
                            await db.increment_posts_today(acc["id"])
                            await db.log_post(acc["id"], post_text, "success", result.get("thread_id"))
else:
            failed += 1
              await db.log_post(acc["id"], post_text, "failed", error=result.get("error"))
        await asyncio.sleep(3)
    await msg.edit_text(f"<b>Mass post done!</b>\n\nSuccess: {success}\nFailed: {failed}", reply_markup=back_kb())


@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery):
      await callback.message.edit_text("<b>Threads Bot Factory</b>\n\nSelect section:", reply_markup=main_menu_kb())

@router.callback_query(F.data == "accounts")
async def cb_accounts(callback: CallbackQuery):
      await callback.message.edit_text("<b>Accounts</b>\n\nManage Threads accounts:", reply_markup=accounts_kb())

@router.callback_query(F.data == "acc_list")
async def cb_acc_list(callback: CallbackQuery):
      accounts = await db.get_accounts()
    if not accounts:
              await callback.message.edit_text("No accounts yet.\nAdd: <code>/add user:token:id</code>", reply_markup=accounts_kb())
              return
          text = "<b>Accounts:</b>\n\n"
    for a in accounts:
              text += f"#{a['id']} @{a['username']} | Posts: {a['posts_count']} | Today: {a['posts_today']}/{a['daily_limit']}\n"
          btns = [[InlineKeyboardButton(text=f"Del #{a['id']}", callback_data=f"acc_del_{a['id']}")] for a in accounts[:5]]
    btns.append([InlineKeyboardButton(text="<< Back", callback_data="accounts")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("acc_del_"))
async def cb_acc_del(callback: CallbackQuery):
      acc_id = int(callback.data.split("_")[-1])
    await db.delete_account(acc_id)
    await callback.answer(f"Account #{acc_id} deleted!")
    await cb_acc_list(callback)

@router.callback_query(F.data == "oauth_connect")
async def cb_oauth(callback: CallbackQuery):
      state = str(uuid.uuid4())
    pending_auth[state] = callback.from_user.id
    url = get_auth_url(state)
    kb = InlineKeyboardMarkup(inline_keyboard=[
              [InlineKeyboardButton(text="Connect Threads", url=url)],
              [InlineKeyboardButton(text="<< Back", callback_data="accounts")]
    ])
    await callback.message.edit_text("<b>OAuth Connect</b>\n\nClick below to connect:", reply_markup=kb)

@router.callback_query(F.data == "acc_add")
async def cb_acc_add(callback: CallbackQuery):
      set_state(callback.from_user.id, "waiting_account")
    await callback.message.edit_text("<b>Add Account</b>\n\nSend: <code>username:token:user_id</code>", reply_markup=back_kb())

@router.callback_query(F.data == "posting")
async def cb_posting(callback: CallbackQuery):
      await callback.message.edit_text("<b>Posting</b>\n\nSelect action:", reply_markup=posting_kb())

@router.callback_query(F.data == "post_new")
async def cb_post_new(callback: CallbackQuery):
      accounts = await db.get_accounts("active")
    if not accounts:
              await callback.message.edit_text("No active accounts", reply_markup=posting_kb())
              return
          btns = [[InlineKeyboardButton(text=f"@{a['username']}", callback_data=f"post_to_{a['id']}")] for a in accounts]
    btns.append([InlineKeyboardButton(text="<< Back", callback_data="posting")])
    await callback.message.edit_text("Select account:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("post_to_"))
async def cb_post_to(callback: CallbackQuery):
      acc_id = int(callback.data.split("_")[-1])
    set_state(callback.from_user.id, "waiting_post_text", {"account_id": acc_id})
    await callback.message.edit_text("Send your post text:", reply_markup=back_kb())

@router.callback_query(F.data == "post_mass")
async def cb_post_mass(callback: CallbackQuery):
      set_state(callback.from_user.id, "waiting_mass_text")
    await callback.message.edit_text("Send text for mass posting:\nSpintax supported: {opt1|opt2}", reply_markup=back_kb())

@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
      s = await db.get_post_stats()
    text = (f"<b>Statistics</b>\n\n"
                        f"Accounts: {s['active_accounts']}/{s['total_accounts']}\n"
                        f"Proxies: {s['active_proxies']}\n"
                        f"Total posts: {s['total_posts']}\n"
                        f"Today: {s['today_posts']}\n"
                        f"Success rate: {s['success_rate']}%")
    await callback.message.edit_text(text, reply_markup=back_kb())

@router.callback_query(F.data == "proxies")
async def cb_proxies(callback: CallbackQuery):
      await callback.message.edit_text("<b>Proxies</b>", reply_markup=proxies_kb())

@router.callback_query(F.data == "templates")
async def cb_templates(callback: CallbackQuery):
      await callback.message.edit_text("<b>Templates</b>", reply_markup=templates_kb())

@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
      await callback.message.edit_text("<b>Settings</b>\n\nBot is running.", reply_markup=back_kb())

@router.callback_query(F.data == "automation")
async def cb_automation(callback: CallbackQuery):
      await callback.message.edit_text("<b>Automation</b>\n\nComing soon.", reply_markup=back_kb())


@router.message()
async def handle_text(message: Message):
      if not is_admin(message.from_user.id): return
            state = get_state(message.from_user.id)
    if state["state"] == "waiting_account":
              clear_state(message.from_user.id)
              parts = message.text.split(":")
              if len(parts) < 2:
                            await message.answer("Format: username:token:user_id", reply_markup=back_kb())
                            return
                        username = parts[0].strip().lstrip("@")
        token = parts[1].strip()
        uid = parts[2].strip() if len(parts) > 2 else ""
        acc_id = await db.add_account(username, token, uid)
        await message.answer(f"Account added! ID: {acc_id}", reply_markup=main_menu_kb())
elif state["state"] == "waiting_post_text":
        clear_state(message.from_user.id)
        acc_id = state["data"].get("account_id")
        account = await db.get_account(acc_id)
        if not account:
                      await message.answer("Account not found", reply_markup=main_menu_kb())
                      return
                  msg = await message.answer(f"Publishing...")
        result = await publish_thread(account["threads_user_id"], account["access_token"], message.text)
        if result["success"]:
                      await db.increment_posts_today(acc_id)
                      await db.log_post(acc_id, message.text, "success", result.get("thread_id"))
                      await msg.edit_text(f"Published! Thread: {result.get('thread_id','')}", reply_markup=main_menu_kb())
else:
            await db.log_post(acc_id, message.text, "failed", error=result.get("error"))
            await msg.edit_text(f"Error: {result.get('error','')}", reply_markup=main_menu_kb())
elif state["state"] == "waiting_mass_text":
        clear_state(message.from_user.id)
        accounts = await db.get_accounts("active")
        if not accounts:
                      await message.answer("No active accounts", reply_markup=main_menu_kb())
                      return
                  msg = await message.answer(f"Mass posting to {len(accounts)} accounts...")
        ok = 0
        fail = 0
        for acc in accounts:
                      t = process_spintax(message.text) if "{" in message.text and "|" in message.text else message.text
                      r = await publish_thread(acc["threads_user_id"], acc["access_token"], t)
                      if r["success"]:
                                        ok += 1
                                        await db.increment_posts_today(acc["id"])
else:
                fail += 1
              await asyncio.sleep(3)
        await msg.edit_text(f"Done! Success: {ok}, Failed: {fail}", reply_markup=main_menu_kb())



async def process_scheduled():
      posts = await db.get_pending_posts()
    for post in posts:
              acc_ids = json.loads(post["account_ids"])
        for aid in acc_ids:
                      acc = await db.get_account(aid)
                      if not acc: continue
                                    text = process_spintax(post["content"]) if post.get("use_spintax") else post["content"]
            result = await publish_thread(acc["threads_user_id"], acc["access_token"], text)
            if result["success"]:
                              await db.increment_posts_today(aid)
                          await asyncio.sleep(3)
        await db.update_post_status(post["id"], "published")


async def main():
      await db.init_db()
    accounts = await db.get_accounts()
    if not accounts:
              await db.add_account("qarapaiym2026", "THAFg1uMAVvw1BUVM3eVhWcHNlNlJia2dIeTNrblBBYnFrdzVaODdTQVhQNTNUdmN3eGZAGRUF6ZAEpza1NCQzhpQmFVV2NleTZA2NHRfVzdicHoyMnlhVEs2V2tvLUtCVUZA0ODRLU1RYWnhoaGVTZA2ZA2LTNoOFdlQmJoMVdwbHhHejhvanMzSXZASRHpfcXI5eUEZD", "69059887842")
        logging.info("Auto-registered default account")
    oauth_runner = await start_oauth_server(5000)
    scheduler.add_job(process_scheduled, "interval", minutes=1)
    scheduler.add_job(db.reset_daily_posts, "cron", hour=0, minute=0)
    scheduler.start()
    dp.include_router(router)
    logging.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
      asyncio.run(main())
