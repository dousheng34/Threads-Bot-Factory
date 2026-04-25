"""
Threads Bot Factory - Main Bot File
"""
import asyncio
import logging
import os
import uuid
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.filters import Command, CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import database as db
from threads_api import publish_thread, process_spintax
from oauth import get_auth_url, pending_auth, start_oauth_server

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS = set(int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip())

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()


# ───────────────── keyboards ─────────────────

def main_menu(user_id: int) -> InlineKeyboardMarkup:
    is_admin = user_id in ADMIN_IDS
    buttons = [
        [InlineKeyboardButton(text="👤 Аккаунттар", callback_data="accounts"),
         InlineKeyboardButton(text="📝 Жазу", callback_data="post")],
        [InlineKeyboardButton(text="📅 Жоспарлау", callback_data="schedule"),
         InlineKeyboardButton(text="📋 Шаблондар", callback_data="templates")],
        [InlineKeyboardButton(text="🌐 Прокси", callback_data="proxies"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="💎 Тариф", callback_data="plan")],
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def accounts_menu(accounts: list) -> InlineKeyboardMarkup:
    buttons = []
    for acc in accounts:
        status = "✅" if acc["status"] == "active" else "❌"
        buttons.append([InlineKeyboardButton(
            text=f"{status} @{acc['username']} (#{acc['id']})",
            callback_data=f"acc_{acc['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="➕ Аккаунт қосу", callback_data="add_account")])
    buttons.append([InlineKeyboardButton(text="🔙 Артқа", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def back_btn(target: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Артқа", callback_data=target)]
    ])


# ───────────────── /start ─────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    user = await db.get_or_create_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or ""
    )
    plan = await db.get_user_plan(message.from_user.id)
    await message.answer(
        f"👋 Сәлем, <b>{message.from_user.full_name}</b>!\n\n"
        f"🤖 <b>Threads Bot Factory</b> — Threads аккаунттарын басқару боты\n\n"
        f"💎 Тарифің: <b>{plan['name']}</b>\n"
        f"📱 Аккаунт лимиті: <b>{plan['accounts']}</b>\n"
        f"📝 Күнделікті пост: <b>{plan['daily_posts']}</b>\n\n"
        f"Төменден бөлімді таңда 👇",
        reply_markup=main_menu(message.from_user.id)
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer("📋 Негізгі мәзір:", reply_markup=main_menu(message.from_user.id))


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 <b>Командалар:</b>\n\n"
        "/start — Боттыбастау\n"
        "/menu — Мәзір\n"
        "/accounts — Аккаунттар\n"
        "/post — Пост жазу\n"
        "/stats — Статистика\n"
        "/plan — Тариф\n"
        "/help — Анықтама",
        reply_markup=back_btn()
    )


# ───────────────── callbacks: navigation ─────────────────

@router.callback_query(F.data == "main")
async def cb_main(call: CallbackQuery):
    plan = await db.get_user_plan(call.from_user.id)
    await call.message.edit_text(
        f"🏠 <b>Негізгі мәзір</b>\n\n💎 Тарифің: <b>{plan['name']}</b>",
        reply_markup=main_menu(call.from_user.id)
    )


# ───────────────── accounts ─────────────────

@router.callback_query(F.data == "accounts")
@router.message(Command("accounts"))
async def show_accounts(update):
    msg = update if isinstance(update, Message) else update.message
    user_id = update.from_user.id
    accounts = await db.get_accounts(user_id=user_id)
    if not accounts:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Аккаунт қосу", callback_data="add_account")],
            [InlineKeyboardButton(text="🔙 Артқа", callback_data="main")]
        ])
        text = "📱 Аккаунттар жоқ. Жаңасын қосыңыз."
    else:
        kb = accounts_menu(accounts)
        text = f"📱 <b>Сіздің аккаунттарыңыз ({len(accounts)}):</b>"
    if isinstance(update, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data == "add_account")
async def cb_add_account(call: CallbackQuery):
    user_id = call.from_user.id
    plan = await db.get_user_plan(user_id)
    accounts = await db.get_accounts(user_id=user_id)
    if len(accounts) >= plan["accounts"]:
        await call.answer(f"❌ Лимит толды ({plan['accounts']} аккаунт). Тарифті жоғарылат!", show_alert=True)
        return
    state_key = str(uuid.uuid4())
    pending_auth[state_key] = user_id
    auth_url = get_auth_url(state_key)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Threads-ке кіру", url=auth_url)],
        [InlineKeyboardButton(text="🔙 Артқа", callback_data="accounts")]
    ])
    await call.message.edit_text(
        "🔐 <b>Threads аккаунтын қосу</b>\n\n"
        "Төмендегі батырманы басып, Threads-ке кіріңіз:",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("acc_"))
async def cb_account_detail(call: CallbackQuery):
    acc_id = int(call.data.split("_")[1])
    acc = await db.get_account(acc_id, user_id=call.from_user.id)
    if not acc:
        await call.answer("❌ Аккаунт табылмады", show_alert=True)
        return
    status = "✅ Белсенді" if acc["status"] == "active" else "❌ Өшірілген"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Пост жазу", callback_data=f"post_acc_{acc_id}")],
        [InlineKeyboardButton(text="🗑 Жою", callback_data=f"del_acc_{acc_id}")],
        [InlineKeyboardButton(text="🔙 Артқа", callback_data="accounts")]
    ])
    await call.message.edit_text(
        f"👤 <b>@{acc['username']}</b>\n\n"
        f"Статус: {status}\n"
        f"Бүгін: {acc['posts_today']}/{acc['daily_limit']} пост\n"
        f"Барлығы: {acc['posts_count']} пост\n"
        f"Қосылған: {acc['created_at'][:10]}",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("del_acc_"))
async def cb_delete_account(call: CallbackQuery):
    acc_id = int(call.data.split("_")[2])
    await db.delete_account(acc_id, user_id=call.from_user.id)
    await call.answer("✅ Аккаунт жойылды")
    accounts = await db.get_accounts(user_id=call.from_user.id)
    if not accounts:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Аккаунт қосу", callback_data="add_account")],
            [InlineKeyboardButton(text="🔙 Артқа", callback_data="main")]
        ])
        await call.message.edit_text("📱 Аккаунттар жоқ.", reply_markup=kb)
    else:
        await call.message.edit_text(
            f"📱 <b>Аккаунттар ({len(accounts)}):</b>",
            reply_markup=accounts_menu(accounts)
        )


# ───────────────── post ─────────────────

user_post_state = {}

@router.callback_query(F.data == "post")
@router.message(Command("post"))
async def show_post(update):
    msg = update if isinstance(update, Message) else update.message
    user_id = update.from_user.id
    accounts = await db.get_accounts(status="active", user_id=user_id)
    if not accounts:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Аккаунт қосу", callback_data="add_account")],
            [InlineKeyboardButton(text="🔙 Артқа", callback_data="main")]
        ])
        text = "❌ Белсенді аккаунт жоқ. Алдымен аккаунт қосыңыз."
        if isinstance(update, CallbackQuery):
            await msg.edit_text(text, reply_markup=kb)
        else:
            await msg.answer(text, reply_markup=kb)
        return

    buttons = []
    for acc in accounts:
        buttons.append([InlineKeyboardButton(
            text=f"📤 @{acc['username']}",
            callback_data=f"post_acc_{acc['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="📤 Барлығына жазу", callback_data="post_all")])
    buttons.append([InlineKeyboardButton(text="🔙 Артқа", callback_data="main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    text = "📝 <b>Пост жазу</b>\n\nАккаунт таңда:"
    if isinstance(update, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("post_acc_"))
async def cb_post_to_account(call: CallbackQuery):
    acc_id = int(call.data.split("_")[2])
    user_post_state[call.from_user.id] = {"mode": "single", "acc_id": acc_id}
    await call.message.edit_text(
        "✍️ Пост мәтінін жіберіңіз:\n\n"
        "<i>Спинтакс қолдайды: {нұсқа1|нұсқа2|нұсқа3}</i>",
        reply_markup=back_btn("post")
    )


@router.callback_query(F.data == "post_all")
async def cb_post_all(call: CallbackQuery):
    user_post_state[call.from_user.id] = {"mode": "all"}
    await call.message.edit_text(
        "✍️ Барлық аккаунтқа жіберілетін мәтін:\n\n"
        "<i>Спинтакс қолдайды: {нұсқа1|нұсқа2|нұсқа3}</i>",
        reply_markup=back_btn("post")
    )


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message):
    user_id = message.from_user.id
    state = user_post_state.get(user_id)
    if not state:
        return

    del user_post_state[user_id]
    text = message.text
    plan = await db.get_user_plan(user_id)

    if state["mode"] == "single":
        acc = await db.get_account(state["acc_id"], user_id=user_id)
        if not acc:
            await message.answer("❌ Аккаунт табылмады")
            return
        if acc["posts_today"] >= acc["daily_limit"]:
            await message.answer(f"❌ @{acc['username']} күнделікті лимит толды ({acc['daily_limit']} пост)")
            return
        final_text = process_spintax(text)
        wait_msg = await message.answer(f"⏳ @{acc['username']}-ке жіберілуде...")
        result = await publish_thread(acc["threads_user_id"], acc["access_token"], final_text)
        if result["success"]:
            await db.increment_posts_today(acc["id"])
            await db.log_post(acc["id"], final_text, "success", result.get("thread_id",""), user_id=user_id)
            await wait_msg.edit_text(
                f"✅ <b>Жіберілді!</b>\n👤 @{acc['username']}\n📝 {final_text[:100]}...",
                reply_markup=main_menu(user_id)
            )
        else:
            await db.log_post(acc["id"], final_text, "error", error=result.get("error",""), user_id=user_id)
            await wait_msg.edit_text(
                f"❌ Қате: {result.get('error','Белгісіз қате')}",
                reply_markup=main_menu(user_id)
            )

    elif state["mode"] == "all":
        accounts = await db.get_accounts(status="active", user_id=user_id)
        if not accounts:
            await message.answer("❌ Белсенді аккаунт жоқ", reply_markup=main_menu(user_id))
            return
        wait_msg = await message.answer(f"⏳ {len(accounts)} аккаунтқа жіберілуде...")
        ok, fail = 0, 0
        for acc in accounts:
            if acc["posts_today"] >= acc["daily_limit"]:
                fail += 1
                continue
            final_text = process_spintax(text)
            result = await publish_thread(acc["threads_user_id"], acc["access_token"], final_text)
            if result["success"]:
                await db.increment_posts_today(acc["id"])
                await db.log_post(acc["id"], final_text, "success", result.get("thread_id",""), user_id=user_id)
                ok += 1
            else:
                await db.log_post(acc["id"], final_text, "error", error=result.get("error",""), user_id=user_id)
                fail += 1
        await wait_msg.edit_text(
            f"📊 <b>Нәтиже:</b>\n✅ Жіберілді: {ok}\n❌ Қате: {fail}",
            reply_markup=main_menu(user_id)
        )


# ───────────────── stats ─────────────────

@router.callback_query(F.data == "stats")
@router.message(Command("stats"))
async def show_stats(update):
    msg = update if isinstance(update, Message) else update.message
    user_id = update.from_user.id
    stats = await db.get_post_stats(user_id=user_id)
    accounts = await db.get_accounts(user_id=user_id)
    active = sum(1 for a in accounts if a["status"] == "active")
    text = (
        f"📊 <b>Статистика</b>\n\n"
        f"📱 Аккаунт: {len(accounts)} (белсенді: {active})\n"
        f"📝 Барлық пост: {stats['total']}\n"
        f"✅ Сәтті: {stats['success']}\n"
        f"❌ Қате: {stats['errors']}\n"
        f"📅 Бүгін: {stats['today']}"
    )
    kb = back_btn()
    if isinstance(update, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


# ───────────────── plan ─────────────────

@router.callback_query(F.data == "plan")
@router.message(Command("plan"))
async def show_plan(update):
    msg = update if isinstance(update, Message) else update.message
    user_id = update.from_user.id
    user = await db.get_user(user_id)
    plan = await db.get_user_plan(user_id)
    expires = user.get("plan_expires_at", "")
    expires_str = f"\n📅 Мерзімі: {expires[:10]}" if expires else ""
    text = (
        f"💎 <b>Тарифтер</b>\n\n"
        f"Қазіргі: <b>{plan['name']}</b>{expires_str}\n\n"
        f"🆓 <b>Free</b> — тегін\n"
        f"  • 1 аккаунт, 10 пост/күн\n\n"
        f"⭐ <b>Pro</b> — 990₽/ай\n"
        f"  • 10 аккаунт, шексіз пост\n"
        f"  • 50 AI сұраныс/күн\n\n"
        f"🏆 <b>Business</b> — 4990₽/ай\n"
        f"  • Шексіз аккаунт\n"
        f"  • Шексіз пост\n"
        f"  • Шексіз AI"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Pro — 990₽/ай", callback_data="buy_pro")],
        [InlineKeyboardButton(text="🏆 Business — 4990₽/ай", callback_data="buy_business")],
        [InlineKeyboardButton(text="🔙 Артқа", callback_data="main")]
    ])
    if isinstance(update, CallbackQuery):
        await msg.edit_text(text, reply_markup=kb)
    else:
        await msg.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("buy_"))
async def cb_buy(call: CallbackQuery):
    plan_name = call.data.split("_")[1]
    plans = {"pro": ("Pro", "990₽"), "business": ("Business", "4990₽")}
    name, price = plans.get(plan_name, ("?", "?"))
    await call.message.edit_text(
        f"💳 <b>{name} тарифін сатып алу</b>\n\n"
        f"Баға: <b>{price}/ай</b>\n\n"
        f"Төлем үшін админге хабарласыңыз: @admin",
        reply_markup=back_btn("plan")
    )


# ───────────────── templates ─────────────────

@router.callback_query(F.data == "templates")
async def cb_templates(call: CallbackQuery):
    templates = await db.get_templates(user_id=call.from_user.id)
    if not templates:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Артқа", callback_data="main")]
        ])
        await call.message.edit_text("📋 Шаблондар жоқ.", reply_markup=kb)
        return
    buttons = []
    for t in templates[:10]:
        buttons.append([InlineKeyboardButton(text=f"📄 {t['name']}", callback_data=f"tpl_{t['id']}")])
    buttons.append([InlineKeyboardButton(text="🔙 Артқа", callback_data="main")])
    await call.message.edit_text(
        f"📋 <b>Шаблондар ({len(templates)}):</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


# ───────────────── proxies ─────────────────

@router.callback_query(F.data == "proxies")
async def cb_proxies(call: CallbackQuery):
    proxies = await db.get_proxies(user_id=call.from_user.id)
    text = f"🌐 <b>Прокси ({len(proxies)}):</b>\n\n"
    for p in proxies:
        text += f"• {p['host']}:{p['port']} [{p['status']}]\n"
    if not proxies:
        text = "🌐 Прокси жоқ."
    await call.message.edit_text(text, reply_markup=back_btn())


# ───────────────── schedule ─────────────────

@router.callback_query(F.data == "schedule")
async def cb_schedule(call: CallbackQuery):
    posts = await db.get_scheduled_posts(user_id=call.from_user.id)
    pending = [p for p in posts if p["status"] == "pending"]
    text = f"📅 <b>Жоспарланған посттар: {len(pending)}</b>\n\n"
    for p in pending[:5]:
        text += f"• {p['scheduled_at'][:16]} — {p['content'][:40]}...\n"
    if not pending:
        text = "📅 Жоспарланған пост жоқ."
    await call.message.edit_text(text, reply_markup=back_btn())


# ───────────────── admin ─────────────────

@router.callback_query(F.data == "admin")
async def cb_admin(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return
    user_stats = await db.get_user_stats_count()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Пайдаланушылар", callback_data="admin_users"),
         InlineKeyboardButton(text="💰 Төлемдер", callback_data="admin_payments")],
        [InlineKeyboardButton(text="📊 Жалпы статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🔙 Артқа", callback_data="main")]
    ])
    await call.message.edit_text(
        f"⚙️ <b>Админ панель</b>\n\n"
        f"👥 Пайдаланушылар: {user_stats['total']}\n"
        f"💎 Ақылы: {user_stats['paid']}\n"
        f"🆓 Тегін: {user_stats['free']}",
        reply_markup=kb
    )


@router.callback_query(F.data == "admin_users")
async def cb_admin_users(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return
    users = await db.get_all_users()
    text = f"👥 <b>Пайдаланушылар ({len(users)}):</b>\n\n"
    for u in users[:15]:
        plan = u.get("plan","free")
        text += f"• {u['telegram_id']} @{u['username'] or '-'} [{plan}]\n"
    await call.message.edit_text(text, reply_markup=back_btn("admin"))


@router.callback_query(F.data == "admin_payments")
async def cb_admin_payments(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return
    payments = await db.get_pending_payments()
    if not payments:
        await call.message.edit_text("💰 Күтілетін төлем жоқ.", reply_markup=back_btn("admin"))
        return
    buttons = []
    for p in payments:
        buttons.append([InlineKeyboardButton(
            text=f"✅ #{p['id']} @{p['username'] or p['user_id']} — {p['plan']} {p['amount']}₽",
            callback_data=f"confirm_pay_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Артқа", callback_data="admin")])
    await call.message.edit_text(
        f"💰 <b>Төлемдер ({len(payments)}):</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("confirm_pay_"))
async def cb_confirm_payment(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return
    pay_id = int(call.data.split("_")[2])
    success = await db.confirm_payment(pay_id)
    if success:
        await call.answer("✅ Төлем расталды!")
    else:
        await call.answer("❌ Қате", show_alert=True)


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(call: CallbackQuery):
    if call.from_user.id not in ADMIN_IDS:
        await call.answer("❌ Рұқсат жоқ", show_alert=True)
        return
    stats = await db.get_post_stats()
    await call.message.edit_text(
        f"📊 <b>Жалпы статистика</b>\n\n"
        f"📝 Барлық пост: {stats['total']}\n"
        f"✅ Сәтті: {stats['success']}\n"
        f"❌ Қате: {stats['errors']}\n"
        f"📅 Бүгін: {stats['today']}",
        reply_markup=back_btn("admin")
    )


# ───────────────── health + server ─────────────────

async def health_handler(request):
    return web.Response(text="OK", status=200)


async def start_health_server():
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Health check server started on port {port}")


async def main():
    await db.init_db()
    dp.include_router(router)
    await start_health_server()
    await start_oauth_server(5000)
    scheduler.start()
    logging.info("Threads Bot Factory started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
