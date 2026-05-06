"""
bot.py — Threads Bot Factory (SaaS Multi-User Edition)
Telegram bot for managing Threads accounts via web dashboard
"""
import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


class AddAccount(StatesGroup):
    username = State()
    password = State()
    proxy = State()
    ai_topic = State()


class PostState(StatesGroup):
    account_id = State()
    text = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мои аккаунты"), KeyboardButton(text="➕ Добавить аккаунт")],
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📅 Расписание")],
            [KeyboardButton(text="🌐 Открыть дашборд"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        f"🤖 <b>Threads Bot Factory</b> — SaaS платформа для автоматизации Threads.\n\n"
        f"📌 Твой Telegram ID: <code>{user.id}</code>\n\n"
        f"Используй кнопки ниже для управления:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: types.Message):
    text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start — Главное меню\n"
        "/accounts — Список аккаунтов\n"
        "/add — Добавить Threads аккаунт\n"
        "/post — Опубликовать пост\n"
        "/stats — Статистика\n"
        "/schedule — Управление расписанием\n"
        "/dashboard — Открыть веб-дашборд\n\n"
        "💡 Или используй кнопки меню снизу."
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("dashboard"))
@dp.message(F.text == "🌐 Открыть дашборд")
async def cmd_dashboard(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🌐 Открыть дашборд", url=f"{WEBAPP_URL}/dashboard")
    ]])
    await message.answer(
        f"🌐 Твой персональный дашборд:\n{WEBAPP_URL}/dashboard",
        reply_markup=kb
    )


@dp.message(Command("accounts"))
@dp.message(F.text == "👤 Мои аккаунты")
async def cmd_accounts(message: types.Message):
    from database import Database
    db = Database()
    try:
        accounts = await db.get_user_accounts(message.from_user.id)
        if not accounts:
            await message.answer(
                "📭 У тебя нет аккаунтов.\n\nНажми <b>➕ Добавить аккаунт</b>",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
            return

        text = f"👤 <b>Твои аккаунты ({len(accounts)}):</b>\n\n"
        buttons = []
        for acc in accounts:
            status = "🟢" if acc.is_active else "🔴"
            text += f"{status} <code>{acc.username}</code> — постов: {acc.post_count or 0}\n"
            buttons.append([
                InlineKeyboardButton(text=f"▶ {acc.username}", callback_data=f"start_{acc.id}"),
                InlineKeyboardButton(text="⏹", callback_data=f"stop_{acc.id}"),
                InlineKeyboardButton(text="🗑", callback_data=f"del_{acc.id}"),
            ])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"accounts error: {e}")
        await message.answer("❌ Ошибка получения аккаунтов")


@dp.message(Command("add"))
@dp.message(F.text == "➕ Добавить аккаунт")
async def cmd_add_start(message: types.Message, state: FSMContext):
    await state.set_state(AddAccount.username)
    await message.answer(
        "➕ <b>Добавление Threads аккаунта</b>\n\n"
        "Шаг 1/4: Введи <b>username</b> от Threads/Instagram:",
        parse_mode="HTML"
    )


@dp.message(AddAccount.username)
async def add_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text.strip().lstrip("@"))
    await state.set_state(AddAccount.password)
    await message.answer("Шаг 2/4: Введи <b>пароль</b>:", parse_mode="HTML")


@dp.message(AddAccount.password)
async def add_password(message: types.Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await state.set_state(AddAccount.proxy)
    await message.answer(
        "Шаг 3/4: Введи <b>прокси</b> (или напиши <code>нет</code>):\n"
        "Формат: <code>http://user:pass@host:port</code>",
        parse_mode="HTML"
    )


@dp.message(AddAccount.proxy)
async def add_proxy(message: types.Message, state: FSMContext):
    proxy = message.text.strip()
    await state.update_data(proxy=None if proxy.lower() in ["нет", "no", "-"] else proxy)
    await state.set_state(AddAccount.ai_topic)
    await message.answer(
        "Шаг 4/4: Укажи <b>тему для AI постов</b>:\n"
        "Например: <i>мотивация, бизнес, лайфстайл</i>",
        parse_mode="HTML"
    )


@dp.message(AddAccount.ai_topic)
async def add_ai_topic(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    from database import Database
    db = Database()
    try:
        acc = await db.add_account(
            telegram_id=message.from_user.id,
            username=data["username"],
            password=data["password"],
            proxy_url=data.get("proxy"),
            ai_topic=message.text.strip()
        )
        await message.answer(
            f"✅ Аккаунт <b>@{data['username']}</b> добавлен!\n\n"
            f"ID: <code>{acc.id}</code>\n"
            f"Тема: {message.text.strip()}\n\n"
            f"Используй кнопки для управления:",
            parse_mode="HTML",
            reply_markup=main_keyboard()
        )
    except Exception as e:
        logger.error(f"add account error: {e}")
        await message.answer(f"❌ Ошибка: {e}")


@dp.callback_query(F.data.startswith("start_"))
async def cb_start_bot(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[1])
    from scheduler import post_for_account
    from database import Database
    db = Database()
    try:
        acc = await db.get_account(acc_id)
        if acc:
            await db.set_account_active(acc_id, True)
            await callback.answer("▶ Бот запущен!", show_alert=True)
            asyncio.create_task(post_for_account(acc))
        else:
            await callback.answer("❌ Аккаунт не найден")
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data.startswith("stop_"))
async def cb_stop_bot(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[1])
    from database import Database
    db = Database()
    try:
        await db.set_account_active(acc_id, False)
        await callback.answer("⏹ Бот остановлен", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data.startswith("del_"))
async def cb_delete_acc(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{acc_id}"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"),
    ]])
    await callback.message.edit_reply_markup(reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("confirm_del_"))
async def cb_confirm_delete(callback: types.CallbackQuery):
    acc_id = int(callback.data.split("_")[2])
    from database import Database
    db = Database()
    try:
        await db.delete_account(acc_id)
        await callback.message.edit_text("🗑 Аккаунт удалён")
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data == "cancel")
async def cb_cancel(callback: types.CallbackQuery):
    await callback.answer("Отменено")


@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message):
    from database import Database
    db = Database()
    try:
        accounts = await db.get_user_accounts(message.from_user.id)
        total_posts = sum(a.post_count or 0 for a in accounts)
        total_comments = sum(a.comment_count or 0 for a in accounts)
        active = sum(1 for a in accounts if a.is_active)

        text = (
            f"📊 <b>Твоя статистика:</b>\n\n"
            f"👤 Аккаунтов: <b>{len(accounts)}</b> (активных: {active})\n"
            f"📝 Всего постов: <b>{total_posts}</b>\n"
            f"💬 Всего комментариев: <b>{total_comments}</b>\n\n"
            f"🌐 Подробнее на дашборде: {WEBAPP_URL}/dashboard"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


@dp.message(Command("schedule"))
@dp.message(F.text == "📅 Расписание")
async def cmd_schedule(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Настроить расписание", url=f"{WEBAPP_URL}/dashboard")]
    ])
    await message.answer(
        "📅 <b>Управление расписанием</b>\n\n"
        "Настрой время автопостинга в веб-дашборде:",
        parse_mode="HTML",
        reply_markup=kb
    )


# Admin commands
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return
    from database import Database
    db = Database()
    try:
        all_accounts = await db.get_all_accounts()
        text = (
            f"🔧 <b>Admin панель</b>\n\n"
            f"👥 Всего аккаунтов: {len(all_accounts)}\n"
            f"🟢 Активных: {sum(1 for a in all_accounts if a.is_active)}\n"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ {e}")


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
