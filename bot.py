"""
🏭 Threads Bot Factory — Telegram Bot
Управляй ботами Threads прямо из Telegram!
"""
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
from oauth import get_auth_url, pending_auth, handle_callback
import uuid

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8770252683:AAE78GVg0eaUKG6CoOsZIk9hrDuHYFaQc-A")
ADMIN_IDS = set()  # Авто-определение: первый /start = админ

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()
auto_jobs = {}  # job_id -> {desc, target, text}

# ============ HELPERS ============

def is_admin(user_id: int) -> bool:
    if not ADMIN_IDS:
        return True  # Первый пользователь автоматически станет админом
    return user_id in ADMIN_IDS

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Аккаунты", callback_data="accounts"),
         InlineKeyboardButton(text="📝 Постинг", callback_data="posting")],
        [InlineKeyboardButton(text="🤖 Автоматизация", callback_data="automation"),
         InlineKeyboardButton(text="🛡️ Прокси", callback_data="proxies")],
        [InlineKeyboardButton(text="📋 Шаблоны", callback_data="templates"),
         InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")],
    ])

def back_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu")]
    ])

def accounts_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список аккаунтов", callback_data="acc_list")],
        [InlineKeyboardButton(text="🔗 OAuth подключение", callback_data="oauth_connect")],
        [InlineKeyboardButton(text="➕ Добавить вручную", callback_data="acc_add")],
        [InlineKeyboardButton(text="📥 Импорт (массово)", callback_data="acc_import")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")],
    ])

def posting_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Новый пост", callback_data="post_new")],
        [InlineKeyboardButton(text="📅 Очередь постов", callback_data="post_queue")],
        [InlineKeyboardButton(text="🔄 Массовый пост", callback_data="post_mass")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")],
    ])

def proxies_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список прокси", callback_data="proxy_list")],
        [InlineKeyboardButton(text="➕ Добавить прокси", callback_data="proxy_add")],
        [InlineKeyboardButton(text="📥 Импорт прокси", callback_data="proxy_import")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")],
    ])

def templates_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Список шаблонов", callback_data="tmpl_list")],
        [InlineKeyboardButton(text="➕ Новый шаблон", callback_data="tmpl_add")],
        [InlineKeyboardButton(text="🎲 Тест спинтакса", callback_data="tmpl_test")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")],
    ])

def automation_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Настроить автопостинг", callback_data="auto_setup")],
        [InlineKeyboardButton(text="📋 Активные задачи", callback_data="auto_list")],
        [InlineKeyboardButton(text="⏹ Остановить всё", callback_data="auto_stopall")],
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="menu")],
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
    # Авто-регистрация первого пользователя как админа
    if not ADMIN_IDS:
        ADMIN_IDS.add(message.from_user.id)
        logging.info(f"✅ Админ зарегистрирован: {message.from_user.id} (@{message.from_user.username})")
    
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer(
        "🏭 <b>Threads Bot Factory</b>\n\n"
        "Добро пожаловать в панель управления!\n"
        f"👤 Админ: <code>{message.from_user.id}</code>\n"
        "Управляй аккаунтами Threads прямо из Telegram.\n\n"
        "Выберите раздел:",
        reply_markup=main_menu_kb()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    if not is_admin(message.from_user.id): return
    await message.answer(
        "📖 <b>Команды:</b>\n\n"
        "/start — Главное меню\n"
        "/accounts — Управление аккаунтами\n"
        "/post — Быстрый пост\n"
        "/mass — Массовый постинг\n"
        "/stats — Статистика\n"
        "/templates — Шаблоны\n"
        "/proxies — Прокси\n"
        "/help — Помощь\n\n"
        "📌 <b>Форматы:</b>\n"
        "Добавить аккаунт: <code>/add username:token:user_id</code>\n"
        "Быстрый пост: <code>/post ID текст поста</code>\n"
        "Spintax: <code>{вариант1|вариант2|вариант3}</code>",
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
        await message.answer("❌ Формат: <code>/add username:token:user_id</code>", reply_markup=back_kb())
        return
    parts = args[1].split(":")
    if len(parts) < 2:
        await message.answer("❌ Минимум: <code>/add username:token</code>", reply_markup=back_kb())
        return
    username = parts[0].strip().lstrip("@")
    token = parts[1].strip()
    user_id = parts[2].strip() if len(parts) > 2 else ""
    acc_id = await db.add_account(username, token, user_id)
    await message.answer(
        f"✅ Аккаунт добавлен!\n\n"
        f"🆔 ID: <code>{acc_id}</code>\n"
        f"👤 Username: @{username}\n"
        f"🔑 Token: <code>{token[:20]}...</code>",
        reply_markup=back_kb()
    )

@router.message(Command("post"))
async def cmd_post(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        accounts = await db.get_accounts("active")
        acc_list = "\n".join([f"  {a['id']}. @{a['username']}" for a in accounts]) or "  Нет аккаунтов"
        await message.answer(
            f"📝 <b>Быстрый пост</b>\n\n"
            f"Формат: <code>/post ID текст</code>\n\n"
            f"Доступные аккаунты:\n{acc_list}",
            reply_markup=back_kb()
        )
        return

    try:
        acc_id = int(args[1])
    except ValueError:
        await message.answer("❌ ID аккаунта должен быть числом", reply_markup=back_kb())
        return

    text = args[2]
    account = await db.get_account(acc_id)
    if not account:
        await message.answer("❌ Аккаунт не найден", reply_markup=back_kb())
        return

    msg = await message.answer(f"⏳ Публикую в @{account['username']}...")
    result = await publish_thread(account["threads_user_id"], account["access_token"], text)

    if result["success"]:
        await db.increment_posts_today(acc_id)
        await db.log_post(acc_id, text, "success", result.get("thread_id"))
        await msg.edit_text(
            f"✅ <b>Опубликовано!</b>\n\n"
            f"👤 @{account['username']}\n"
            f"📝 {text[:100]}...\n"
            f"🔗 Thread ID: <code>{result.get('thread_id', 'N/A')}</code>",
            reply_markup=back_kb()
        )
    else:
        await db.log_post(acc_id, text, "failed", error=result.get("error"))
        await msg.edit_text(f"❌ Ошибка: {result.get('error', 'Неизвестная')}", reply_markup=back_kb())

@router.message(Command("mass"))
async def cmd_mass(message: Message):
    if not is_admin(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer(
            "📣 <b>Массовый пост</b>\n\n"
            "Формат: <code>/mass текст поста</code>\n"
            "Поддерживается Spintax: <code>{вариант1|вариант2}</code>\n\n"
            "Пост будет отправлен во все активные аккаунты.",
            reply_markup=back_kb()
        )
        return

    text = args[1]
    accounts = await db.get_accounts("active")
    if not accounts:
        await message.answer("❌ Нет активных аккаунтов", reply_markup=back_kb())
        return

    msg = await message.answer(f"⏳ Массовая публикация в {len(accounts)} аккаунтов...")
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
            results_text += f"  ✅ @{acc['username']}\n"
        else:
            failed += 1
            await db.log_post(acc["id"], post_text, "failed", error=result.get("error"))
            results_text += f"  ❌ @{acc['username']}: {result.get('error','')[:30]}\n"

        await asyncio.sleep(3)  # Задержка между постами

    await msg.edit_text(
        f"📣 <b>Массовая публикация завершена!</b>\n\n"
        f"✅ Успешно: {success}\n❌ Ошибки: {failed}\n\n"
        f"<b>Результаты:</b>\n{results_text}",
        reply_markup=back_kb()
    )

# ============ CALLBACKS ============

@router.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏭 <b>Threads Bot Factory</b>\n\nВыберите раздел:",
        reply_markup=main_menu_kb()
    )

@router.callback_query(F.data == "accounts")
async def cb_accounts(callback: CallbackQuery):
    await callback.message.edit_text("👥 <b>Аккаунты</b>\n\nУправление аккаунтами Threads:", reply_markup=accounts_kb())

@router.callback_query(F.data == "acc_list")
async def cb_acc_list(callback: CallbackQuery):
    accounts = await db.get_accounts()
    if not accounts:
        await callback.message.edit_text("📋 Аккаунтов пока нет.\n\nДобавьте: <code>/add user:token:id</code>", reply_markup=accounts_kb())
        return

    status_emoji = {"active":"🟢","warming":"🟡","banned":"🔴","limited":"🟣","inactive":"⚪"}
    text = "👥 <b>Аккаунты:</b>\n\n"
    for a in accounts:
        emoji = status_emoji.get(a["status"], "⚪")
        text += (f"{emoji} <b>#{a['id']}</b> @{a['username']}\n"
                f"   📊 Постов: {a['posts_count']} | Сегодня: {a['posts_today']}/{a['daily_limit']}\n")

    btns = [[InlineKeyboardButton(text=f"❌ Удалить #{a['id']}", callback_data=f"acc_del_{a['id']}")] for a in accounts[:5]]
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="accounts")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("acc_del_"))
async def cb_acc_del(callback: CallbackQuery):
    acc_id = int(callback.data.split("_")[-1])
    await db.delete_account(acc_id)
    await callback.answer(f"✅ Аккаунт #{acc_id} удалён!")
    await cb_acc_list(callback)

@router.callback_query(F.data == "acc_add")
async def cb_acc_add(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_account")
    await callback.message.edit_text(
        "➕ <b>Добавить аккаунт</b>\n\n"
        "Отправьте данные в формате:\n"
        "<code>username:access_token:threads_user_id</code>\n\n"
        "Или минимально:\n"
        "<code>username:access_token</code>",
        reply_markup=back_kb()
    )

@router.callback_query(F.data == "acc_import")
async def cb_acc_import(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_import")
    await callback.message.edit_text(
        "📥 <b>Массовый импорт</b>\n\n"
        "Отправьте аккаунты по одному на строку:\n"
        "<code>username:token:user_id\nusername2:token2:user_id2</code>",
        reply_markup=back_kb()
    )

# ---- Posting ----
@router.callback_query(F.data == "posting")
async def cb_posting(callback: CallbackQuery):
    await callback.message.edit_text("📝 <b>Постинг</b>\n\nУправление публикациями:", reply_markup=posting_kb())

@router.callback_query(F.data == "post_new")
async def cb_post_new(callback: CallbackQuery):
    accounts = await db.get_accounts("active")
    if not accounts:
        await callback.message.edit_text("❌ Нет активных аккаунтов", reply_markup=posting_kb())
        return
    btns = [[InlineKeyboardButton(text=f"@{a['username']}", callback_data=f"post_to_{a['id']}")] for a in accounts]
    btns.append([InlineKeyboardButton(text="📣 Все аккаунты", callback_data="post_to_all")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="posting")])
    await callback.message.edit_text("✍️ Выберите аккаунт для поста:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("post_to_"))
async def cb_post_to(callback: CallbackQuery):
    target = callback.data.replace("post_to_", "")
    set_state(callback.from_user.id, "waiting_post", {"target": target})
    if target == "all":
        await callback.message.edit_text("✍️ Напишите текст поста (отправится во все аккаунты):\n\nSpintax: <code>{вариант1|вариант2}</code>", reply_markup=back_kb())
    else:
        acc = await db.get_account(int(target))
        name = acc["username"] if acc else target
        await callback.message.edit_text(f"✍️ Напишите текст поста для @{name}:", reply_markup=back_kb())

@router.callback_query(F.data == "post_queue")
async def cb_post_queue(callback: CallbackQuery):
    posts = await db.get_scheduled_posts()
    status_e = {"pending": "⏳", "published": "✅", "failed": "❌", "cancelled": "🚫"}
    text = "📅 <b>Очередь постов:</b>\n\n"
    btns = []
    if posts:
        for p in posts[:8]:
            e = status_e.get(p["status"], "❓")
            sched = (p["scheduled_at"] or "")[:16].replace("T", " ")
            preview = p["content"][:35] + "..." if len(p["content"]) > 35 else p["content"]
            text += f"{e} <b>#{p['id']}</b> — {preview}\n   📅 {sched}\n\n"
        pending = [p for p in posts if p["status"] == "pending"][:3]
        for p in pending:
            btns.append([InlineKeyboardButton(text=f"🗑 Удалить #{p['id']}", callback_data=f"sched_del_{p['id']})")])
    else:
        text += "Очередь пуста.\n"
    btns.append([InlineKeyboardButton(text="➕ Добавить в очередь", callback_data="sched_add")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="posting")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data == "sched_add")
async def cb_sched_add(callback: CallbackQuery):
    accounts = await db.get_accounts("active")
    if not accounts:
        await callback.message.edit_text("❌ Нет активных аккаунтов", reply_markup=back_kb())
        return
    btns = [[InlineKeyboardButton(text=f"@{a['username']}", callback_data=f"sched_acc_{a['id']}")] for a in accounts]
    btns.append([InlineKeyboardButton(text="📣 Все аккаунты", callback_data="sched_acc_all")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="post_queue")])
    await callback.message.edit_text(
        "📅 <b>Новый запланированный пост</b>\n\nВыберите аккаунт:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )

@router.callback_query(F.data.startswith("sched_acc_"))
async def cb_sched_acc(callback: CallbackQuery):
    target = callback.data.replace("sched_acc_", "")
    set_state(callback.from_user.id, "waiting_sched_text", {"target": target})
    await callback.message.edit_text(
        "✍️ Напишите текст поста:\n\nSpintax: <code>{вариант1|вариант2}</code>",
        reply_markup=back_kb()
    )

@router.callback_query(F.data.startswith("sched_del_"))
async def cb_sched_del(callback: CallbackQuery):
    try:
        post_id = int(callback.data.replace("sched_del_", "").rstrip(")"))
        await db.delete_scheduled_post(post_id)
        await callback.answer(f"✅ Пост #{post_id} удалён!")
    except Exception:
        await callback.answer("❌ Ошибка удаления")
    await cb_post_queue(callback)

@router.callback_query(F.data == "post_mass")
async def cb_post_mass(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_post", {"target": "all"})
    await callback.message.edit_text(
        "📣 <b>Массовый пост</b>\n\n"
        "Напишите текст — он будет опубликован во все активные аккаунты.\n"
        "Поддерживается Spintax: <code>{привет|здравствуйте|хей}</code>",
        reply_markup=back_kb()
    )

# ---- Proxies ----
@router.callback_query(F.data == "proxies")
async def cb_proxies(callback: CallbackQuery):
    await callback.message.edit_text("🛡️ <b>Прокси</b>\n\nУправление прокси-серверами:", reply_markup=proxies_kb())

@router.callback_query(F.data == "proxy_list")
async def cb_proxy_list(callback: CallbackQuery):
    proxies = await db.get_proxies()
    if not proxies:
        await callback.message.edit_text("🛡️ Прокси не добавлены", reply_markup=proxies_kb())
        return
    status_e = {"active":"🟢","dead":"🔴","slow":"🟡"}
    text = "🛡️ <b>Прокси:</b>\n\n"
    for p in proxies:
        e = status_e.get(p["status"], "⚪")
        text += f"{e} #{p['id']} <code>{p['host']}:{p['port']}</code> ({p['protocol']})\n   {p['country']} | {p['response_time']}ms\n\n"
    await callback.message.edit_text(text, reply_markup=proxies_kb())

@router.callback_query(F.data == "proxy_add")
async def cb_proxy_add(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_proxy")
    await callback.message.edit_text(
        "➕ <b>Добавить прокси</b>\n\nФормат:\n<code>protocol://user:pass@host:port</code>\n\nПример:\n<code>socks5://user:pass@1.2.3.4:1080</code>",
        reply_markup=back_kb()
    )

@router.callback_query(F.data == "proxy_import")
async def cb_proxy_import(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_proxy_import")
    await callback.message.edit_text("📥 Отправьте прокси по одному на строку:\n<code>protocol://user:pass@host:port</code>", reply_markup=back_kb())

# ---- Templates ----
@router.callback_query(F.data == "templates")
async def cb_templates(callback: CallbackQuery):
    await callback.message.edit_text("📋 <b>Шаблоны</b>\n\nУправление шаблонами контента:", reply_markup=templates_kb())

@router.callback_query(F.data == "tmpl_list")
async def cb_tmpl_list(callback: CallbackQuery):
    templates = await db.get_templates()
    if not templates:
        await callback.message.edit_text("📋 Шаблонов нет. Создайте новый!", reply_markup=templates_kb())
        return
    text = "📋 <b>Шаблоны:</b>\n\n"
    for t in templates:
        text += f"📝 <b>#{t['id']}</b> {t['name']}\n   {t['content'][:50]}...\n   Использован: {t['usage_count']} раз\n\n"
    btns = [[InlineKeyboardButton(text=f"📝 Использовать #{t['id']}", callback_data=f"tmpl_use_{t['id']}")] for t in templates[:5]]
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="templates")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data == "tmpl_add")
async def cb_tmpl_add(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_template_name")
    await callback.message.edit_text("📝 Введите <b>название</b> шаблона:", reply_markup=back_kb())

@router.callback_query(F.data == "tmpl_test")
async def cb_tmpl_test(callback: CallbackQuery):
    set_state(callback.from_user.id, "waiting_spintax_test")
    await callback.message.edit_text(
        "🎲 <b>Тест Spintax</b>\n\nОтправьте текст с Spintax:\n<code>{привет|хей|здравствуйте}, {как дела|что нового}? {🔥|⚡|🚀}</code>",
        reply_markup=back_kb()
    )

@router.callback_query(F.data.startswith("tmpl_use_"))
async def cb_tmpl_use(callback: CallbackQuery):
    tmpl_id = int(callback.data.split("_")[-1])
    tmpl = await db.get_template(tmpl_id)
    if not tmpl:
        await callback.answer("❌ Шаблон не найден")
        return
    generated = process_spintax(tmpl["content"])
    await db.increment_template_usage(tmpl_id)
    accounts = await db.get_accounts("active")
    btns = [[InlineKeyboardButton(text=f"📤 Отправить в @{a['username']}", callback_data=f"tmpl_send_{tmpl_id}_{a['id']}")] for a in accounts[:5]]
    btns.append([InlineKeyboardButton(text="📣 Во все аккаунты", callback_data=f"tmpl_send_{tmpl_id}_all")])
    btns.append([InlineKeyboardButton(text="🎲 Генерировать снова", callback_data=f"tmpl_use_{tmpl_id}")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tmpl_list")])
    await callback.message.edit_text(f"🎲 <b>Сгенерировано:</b>\n\n{generated}", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

# ---- Stats ----
@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    await show_stats(callback.message, edit=True)

# ---- Settings ----
@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        "📌 <b>Threads API:</b>\n"
        f"  App ID: <code>{os.getenv('THREADS_APP_ID', 'не задан')}</code>\n\n"
        "📌 <b>Лимиты Threads API:</b>\n"
        "  • 250 постов / 24 часа\n"
        "  • 2-шаговая публикация\n"
        "  • Токен живёт 60 дней\n\n"
        "Настройки задаются через переменные окружения.",
        reply_markup=back_kb()
    )

# ============ OAUTH ============

@router.message(Command("connect"))
async def cmd_connect(message: Message):
    if not is_admin(message.from_user.id): return
    state = str(uuid.uuid4())[:8]
    pending_auth[state] = message.from_user.id
    auth_url = get_auth_url(state)
    await message.answer(
        "🔗 <b>Подключить аккаунт Threads</b>\n\n"
        "Нажмите кнопку ниже и авторизуйтесь:\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Авторизоваться в Threads", url=auth_url)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="menu")]
        ])
    )

@router.callback_query(F.data == "oauth_connect")
async def cb_oauth_connect(callback: CallbackQuery):
    state = str(uuid.uuid4())[:8]
    pending_auth[state] = callback.from_user.id
    auth_url = get_auth_url(state)
    await callback.message.edit_text(
        "🔗 <b>Подключить аккаунт Threads</b>\n\n"
        "Нажмите кнопку ниже и авторизуйтесь через Threads:\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Авторизоваться", url=auth_url)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="accounts")]
        ])
    )

# ============ AUTOMATION ============

@router.callback_query(F.data == "automation")
async def cb_automation(callback: CallbackQuery):
    count = len(auto_jobs)
    await callback.message.edit_text(
        f"🤖 <b>Автоматизация</b>\n\n"
        f"🔄 Активных задач: <b>{count}</b>\n\n"
        "Настрой автопостинг — бот будет публиковать\nпосты с заданным интервалом автоматически.",
        reply_markup=automation_kb()
    )

@router.callback_query(F.data == "auto_setup")
async def cb_auto_setup(callback: CallbackQuery):
    accounts = await db.get_accounts("active")
    if not accounts:
        await callback.message.edit_text("❌ Нет активных аккаунтов", reply_markup=automation_kb())
        return
    btns = [[InlineKeyboardButton(text=f"@{a['username']}", callback_data=f"autorun_acc_{a['id']}")] for a in accounts]
    btns.append([InlineKeyboardButton(text="📣 Все аккаунты", callback_data="autorun_acc_all")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="automation")])
    await callback.message.edit_text(
        "🤖 <b>Автопостинг</b>\n\nВыберите аккаунт:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=btns)
    )

@router.callback_query(F.data.startswith("autorun_acc_"))
async def cb_autorun_acc(callback: CallbackQuery):
    target = callback.data.replace("autorun_acc_", "")
    set_state(callback.from_user.id, "waiting_auto_text", {"target": target})
    await callback.message.edit_text(
        "🤖 <b>Шаг 1/2 — Текст поста</b>\n\n"
        "Напишите текст (Spintax поддерживается):\n"
        "<code>{Привет|Хей|Здравствуйте}! {🔥|⚡|🚀}</code>\n\n"
        "Каждый автопост генерирует уникальный вариант.",
        reply_markup=back_kb()
    )

@router.callback_query(F.data == "auto_list")
async def cb_auto_list(callback: CallbackQuery):
    if not auto_jobs:
        await callback.message.edit_text("📋 Нет активных задач", reply_markup=automation_kb())
        return
    text = "📋 <b>Активные задачи автопостинга:</b>\n\n"
    btns = []
    for job_id, info in list(auto_jobs.items()):
        text += f"▶️ {info['desc']}\n"
        btns.append([InlineKeyboardButton(text=f"⏹ Стоп: {info['desc'][:25]}", callback_data=f"auto_kill_{job_id}")])
    btns.append([InlineKeyboardButton(text="◀️ Назад", callback_data="automation")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))

@router.callback_query(F.data.startswith("auto_kill_"))
async def cb_auto_kill(callback: CallbackQuery):
    job_id = callback.data.replace("auto_kill_", "")
    if job_id in auto_jobs:
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        del auto_jobs[job_id]
        await callback.answer("✅ Задача остановлена!")
    await cb_auto_list(callback)

@router.callback_query(F.data == "auto_stopall")
async def cb_auto_stopall(callback: CallbackQuery):
    count = len(auto_jobs)
    for job_id in list(auto_jobs.keys()):
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
    auto_jobs.clear()
    await callback.answer(f"✅ Остановлено {count} задач!")
    await cb_automation(callback)

# ============ TEXT HANDLERS (STATE) ============

@router.message(F.text)
async def handle_text(message: Message):
    if not is_admin(message.from_user.id): return
    state = get_state(message.from_user.id)

    if state["state"] == "waiting_account":
        clear_state(message.from_user.id)
        parts = message.text.split(":")
        if len(parts) < 2:
            await message.answer("❌ Неверный формат. Нужно: <code>username:token</code>", reply_markup=accounts_kb())
            return
        username = parts[0].strip().lstrip("@")
        token = parts[1].strip()
        uid = parts[2].strip() if len(parts) > 2 else ""
        acc_id = await db.add_account(username, token, uid)
        await message.answer(f"✅ Аккаунт @{username} добавлен! (ID: {acc_id})", reply_markup=accounts_kb())

    elif state["state"] == "waiting_import":
        clear_state(message.from_user.id)
        lines = message.text.strip().split("\n")
        added = 0
        for line in lines:
            parts = line.strip().split(":")
            if len(parts) >= 2:
                await db.add_account(parts[0].strip().lstrip("@"), parts[1].strip(), parts[2].strip() if len(parts) > 2 else "")
                added += 1
        await message.answer(f"✅ Импортировано: {added} аккаунтов", reply_markup=accounts_kb())

    elif state["state"] == "waiting_post":
        clear_state(message.from_user.id)
        target = state["data"].get("target", "all")
        text = message.text

        if target == "all":
            accounts = await db.get_accounts("active")
            if not accounts:
                await message.answer("❌ Нет активных аккаунтов", reply_markup=posting_kb())
                return
            msg = await message.answer(f"⏳ Публикую в {len(accounts)} аккаунтов...")
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
                await asyncio.sleep(3)
            await msg.edit_text(f"📣 Готово! ✅ {ok} | ❌ {fail}", reply_markup=posting_kb())
        else:
            acc = await db.get_account(int(target))
            if not acc:
                await message.answer("❌ Аккаунт не найден", reply_markup=posting_kb())
                return
            msg = await message.answer(f"⏳ Публикую в @{acc['username']}...")
            result = await publish_thread(acc["threads_user_id"], acc["access_token"], text)
            if result["success"]:
                await db.increment_posts_today(acc["id"])
                await db.log_post(acc["id"], text, "success", result.get("thread_id"))
                await msg.edit_text(f"✅ Опубликовано в @{acc['username']}!", reply_markup=posting_kb())
            else:
                await db.log_post(acc["id"], text, "failed", error=result.get("error"))
                await msg.edit_text(f"❌ Ошибка: {result.get('error','')}", reply_markup=posting_kb())

    elif state["state"] == "waiting_proxy":
        clear_state(message.from_user.id)
        import re
        m = re.match(r'^(https?|socks5)://(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$', message.text.strip())
        if not m:
            await message.answer("❌ Неверный формат. Нужно: <code>protocol://user:pass@host:port</code>", reply_markup=proxies_kb())
            return
        pid = await db.add_proxy(m.group(4), int(m.group(5)), m.group(2) or "", m.group(3) or "", m.group(1))
        await message.answer(f"✅ Прокси добавлен! (ID: {pid})", reply_markup=proxies_kb())

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
        await message.answer(f"✅ Импортировано: {added} прокси", reply_markup=proxies_kb())

    elif state["state"] == "waiting_template_name":
        set_state(message.from_user.id, "waiting_template_content", {"name": message.text})
        await message.answer("📝 Теперь введите <b>контент</b> шаблона:\n\nSpintax: <code>{вариант1|вариант2}</code>", reply_markup=back_kb())

    elif state["state"] == "waiting_template_content":
        name = state["data"]["name"]
        content = message.text
        clear_state(message.from_user.id)
        tid = await db.add_template(name, content)
        await message.answer(f"✅ Шаблон «{name}» создан! (ID: {tid})", reply_markup=templates_kb())

    elif state["state"] == "waiting_spintax_test":
        clear_state(message.from_user.id)
        results = [process_spintax(message.text) for _ in range(3)]
        text = "🎲 <b>Результаты Spintax:</b>\n\n"
        for i, r in enumerate(results, 1):
            text += f"  {i}. {r}\n\n"
        await message.answer(text, reply_markup=templates_kb())

    elif state["state"] == "waiting_sched_text":
        set_state(message.from_user.id, "waiting_sched_time", {**state["data"], "text": message.text})
        await message.answer(
            "⏰ <b>Шаг 2/2 — Время публикации</b>\n\n"
            "Введите дату и время:\n"
            "Формат: <code>ДД.ММ ЧЧ:ММ</code>\n"
            "Пример: <code>07.04 15:30</code>",
            reply_markup=back_kb()
        )

    elif state["state"] == "waiting_sched_time":
        clear_state(message.from_user.id)
        try:
            dt = datetime.strptime(message.text.strip(), "%d.%m %H:%M").replace(year=datetime.now().year)
            target = state["data"]["target"]
            text = state["data"]["text"]
            use_spintax = 1 if "{" in text and "|" in text else 0
            if target == "all":
                accounts = await db.get_accounts("active")
                account_ids = [a["id"] for a in accounts]
            else:
                account_ids = [int(target)]
            post_id = await db.add_scheduled_post(account_ids, text, dt.isoformat(), use_spintax=use_spintax)
            await message.answer(
                f"✅ <b>Пост запланирован!</b>\n\n"
                f"🆔 ID: <code>{post_id}</code>\n"
                f"📅 Время: {dt.strftime('%d.%m.%Y %H:%M')}\n"
                f"📝 {text[:80]}\n\n"
                "Бот автоматически опубликует в указанное время.",
                reply_markup=posting_kb()
            )
        except ValueError:
            await message.answer(
                "❌ Неверный формат. Используйте: <code>ДД.ММ ЧЧ:ММ</code>\n"
                "Пример: <code>07.04 15:30</code>",
                reply_markup=back_kb()
            )

    elif state["state"] == "waiting_auto_text":
        set_state(message.from_user.id, "waiting_auto_interval", {**state["data"], "text": message.text})
        await message.answer(
            "⏱️ <b>Шаг 2/2 — Интервал</b>\n\n"
            "Введите интервал в минутах:\n"
            "• Диапазон: <code>60_180</code> — каждые 1-3 часа\n"
            "• Точный: <code>120</code> — каждые 2 часа ровно\n\n"
            "Минимум: 5 минут",
            reply_markup=back_kb()
        )

    elif state["state"] == "waiting_auto_interval":
        clear_state(message.from_user.id)
        try:
            import random
            interval_str = message.text.strip()
            if "_" in interval_str:
                parts_i = interval_str.split("_")
                min_i, max_i = max(5, int(parts_i[0])), max(5, int(parts_i[1]))
            else:
                min_i = max_i = max(5, int(interval_str))

            target = state["data"]["target"]
            text = state["data"]["text"]
            use_spintax = "{" in text and "|" in text
            job_id = str(uuid.uuid4())[:8]

            async def auto_post_job(jid=job_id, tgt=target, txt=text, usp=use_spintax, mn=min_i, mx=max_i):
                try:
                    if tgt == "all":
                        accounts = await db.get_accounts("active")
                    else:
                        acc = await db.get_account(int(tgt))
                        accounts = [acc] if acc else []
                    for acc in accounts:
                        if not acc: continue
                        post_text = process_spintax(txt) if usp else txt
                        result = await publish_thread(acc["threads_user_id"], acc["access_token"], post_text)
                        if result["success"]:
                            await db.increment_posts_today(acc["id"])
                            await db.log_post(acc["id"], post_text, "success", result.get("thread_id"))
                        else:
                            await db.log_post(acc["id"], post_text, "failed", error=result.get("error"))
                        await asyncio.sleep(3)
                    if mn != mx and jid in auto_jobs:
                        new_interval = random.randint(mn, mx)
                        job = scheduler.get_job(jid)
                        if job:
                            from apscheduler.triggers.interval import IntervalTrigger
                            job.reschedule(trigger=IntervalTrigger(minutes=new_interval))
                except Exception as e:
                    logging.error(f"Autopost {jid} error: {e}")

            first_interval = random.randint(min_i, max_i)
            scheduler.add_job(auto_post_job, "interval", minutes=first_interval, id=job_id)

            if target == "all":
                target_name = "все аккаунты"
            else:
                acc_obj = await db.get_account(int(target))
                target_name = f"@{acc_obj['username']}" if acc_obj else f"#{target}"

            auto_jobs[job_id] = {"desc": f"{target_name} | {min_i}-{max_i}мин"}
            await message.answer(
                f"✅ <b>Автопостинг запущен!</b>\n\n"
                f"👤 Аккаунт: {target_name}\n"
                f"⏱️ Интервал: {min_i}–{max_i} мин\n"
                f"📝 {text[:60]}\n"
                f"🔧 ID задачи: <code>{job_id}</code>\n\n"
                "Управление: Автоматизация → Активные задачи",
                reply_markup=automation_kb()
            )
        except (ValueError, TypeError):
            await message.answer(
                "❌ Неверный формат. Примеры: <code>60_180</code> или <code>120</code>",
                reply_markup=back_kb()
            )

    else:
        await message.answer("🏭 Используйте /start для главного меню", reply_markup=main_menu_kb())

# ============ HELPERS ============

async def show_accounts_menu(message: Message):
    await message.answer("👥 <b>Аккаунты</b>\n\nУправление аккаунтами Threads:", reply_markup=accounts_kb())

async def show_stats(message: Message, edit=False):
    stats = await db.get_post_stats()
    text = (
        "📊 <b>Статистика</b>\n\n"
        f"👥 Аккаунтов: <b>{stats['total_accounts']}</b> (🟢 {stats['active_accounts']} активных)\n"
        f"🛡️ Активных прокси: <b>{stats['active_proxies']}</b>\n\n"
        f"📝 Всего постов: <b>{stats['total_posts']}</b>\n"
        f"📅 Сегодня: <b>{stats['today_posts']}</b>\n"
        f"✅ Успешность: <b>{stats['success_rate']}%</b>\n"
    )
    if edit:
        await message.edit_text(text, reply_markup=back_kb())
    else:
        await message.answer(text, reply_markup=back_kb())

# ============ SCHEDULER ============

async def check_scheduled_posts():
    """Проверка и публикация запланированных постов"""
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
            await asyncio.sleep(3)
        await db.update_post_status(post["id"], "published")

async def reset_daily_counters():
    """Сброс дневных счётчиков постов"""
    await db.reset_daily_posts()

# ============ WEB SERVER (Health + OAuth) для Pella ============

async def health_handler(request):
    return web.Response(text="OK", status=200)

async def start_web_server():
    """Единый веб-сервер: health-check + OAuth callback (для Pella)"""
    app = web.Application()
    app.router.add_get("/health", health_handler)
    app.router.add_get("/", health_handler)
    app.router.add_get("/callback", handle_callback)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"🌐 Веб-сервер запущен на порту {port} (health + OAuth)")
    return runner

# ============ MAIN ============

async def main():
    await db.init_db()
    dp.include_router(router)

    # Авто-регистрация основного аккаунта
    existing = await db.get_accounts()
    if not existing:
        await db.add_account(
            "qarapaiym2026",
            "THAFg1uMAVvw1BUVM3eVhWcHNlNlJia2dIeTNrblBBYnFrdzVaODdTQVhQNTNUdmN3eGZAGRUF6ZAEpza1NCQzhpQmFVV2NleTZA2NHRfVzdicHoyMnlhVEs2V2tvLUtCVUZA0ODRLU1RYWnhoaGVTZA2ZA2LTNoOFdlQmJoMVdwbHhHejhvanMzSXZASRHpfcXI5eUEZD",
            "26435788272727491"
        )
        logging.info("✅ Аккаунт qarapaiym2026 добавлен автоматически!")

    # Единый веб-сервер (health + OAuth) для Pella
    await start_web_server()

    # Планировщик
    scheduler.add_job(check_scheduled_posts, 'interval', minutes=1)
    scheduler.add_job(reset_daily_counters, 'cron', hour=0, minute=0)
    scheduler.start()

    logging.info("🏭 Threads Bot Factory запущен на Pella!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
