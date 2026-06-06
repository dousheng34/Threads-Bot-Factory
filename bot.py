"""
bot.py — Omnichannel SMM & LeadGen Platform
Telegram bot for managing social accounts and responding to comment replies.
"""
import os
import asyncio
import logging
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

import database as db
from meta_service import meta_service
from whatsapp_service import whatsapp_service

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
WEBAPP_URL = os.getenv("WEBAPP_URL", "http://localhost:8000")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher(storage=MemoryStorage())


@dp.startup()
async def on_startup(bot: Bot):
    await db.init_db()
    logger.info("Database initialized on bot startup")



class AddAccount(StatesGroup):
    username = State()
    password = State()
    proxy = State()
    ai_topic = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Мои аккаунты"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🌐 Открыть дашборд"), KeyboardButton(text="ℹ️ Помощь")],
        ],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_tg = message.from_user
    # Ensure user exists in DB
    await db.get_or_create_user(
        telegram_id=user_tg.id,
        username=user_tg.username or "",
        first_name=user_tg.first_name or ""
    )
    text = (
        f"👋 Привет, <b>{user_tg.first_name}</b>!\n\n"
        f"🤖 <b>Omnichannel SMM & LeadGen Platform</b> — управление вашими Threads, Instagram и WhatsApp в один клик.\n\n"
        f"📌 Твой Telegram ID: <code>{user_tg.id}</code>\n\n"
        f"Используй кнопки ниже для управления:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=main_keyboard())


@dp.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: types.Message):
    text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start — Главное меню\n"
        "/accounts — Список подключенных страниц\n"
        "/stats — Статистика публикаций\n"
        "/dashboard — Ссылка на личный кабинет TWA\n\n"
        "💬 <b>Ответы на комментарии:</b>\n"
        "Когда вам придет уведомление о новом комментарии/сообщении, просто ответьте (Reply) на него в этом чате, чтобы отослать ответ клиенту."
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
    try:
        user = await db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("📭 У тебя нет привязанных страниц.")
            return
            
        accounts = await db.get_social_accounts(user_id=user["id"])
        if not accounts:
            await message.answer(
                "📭 У тебя нет подключенных страниц.\n\nПодключите Threads/Instagram/WhatsApp на дашборде TWA!",
                parse_mode="HTML",
                reply_markup=main_keyboard()
            )
            return

        text = f"👤 <b>Подключенные страницы ({len(accounts)}):</b>\n\n"
        buttons = []
        for acc in accounts:
            status = "🟢" if acc["status"] == "active" else "🔴"
            platform = acc["platform"].upper()
            text += f"{status} <code>{acc['username']}</code> ({platform}) — подписчиков: {acc['followers_count'] or 0}\n"
            buttons.append([
                InlineKeyboardButton(text=f"🗑 Удалить {acc['username']}", callback_data=f"del_{acc['id']}"),
            ])

        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        logger.error(f"accounts error: {e}")
        await message.answer("❌ Ошибка получения аккаунтов")


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
    try:
        await db.delete_social_account(acc_id)
        await callback.message.edit_text("🗑 Аккаунт удалён")
    except Exception as e:
        await callback.answer(f"❌ {e}", show_alert=True)


@dp.callback_query(F.data == "cancel")
async def cb_cancel(callback: types.CallbackQuery):
    await callback.answer("Отменено")


@dp.message(Command("stats"))
@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message):
    try:
        user = await db.get_user_by_telegram(message.from_user.id)
        if not user:
            await message.answer("📊 У вас пока нет статистики.")
            return
            
        stats = await db.get_post_stats(user_id=user["id"])
        text = (
            f"📊 <b>Статистика публикаций:</b>\n\n"
            f"👤 Подключено страниц: <b>{stats.get('total_accounts', 0)}</b> (активных: {stats.get('active_accounts', 0)})\n"
            f"📝 Опубликовано постов: <b>{stats.get('total_posts', 0)}</b>\n"
            f"💡 Успешность доставок: <b>{stats.get('success_rate', 100)}%</b>\n\n"
            f"🌐 Подробнее на дашборде: {WEBAPP_URL}/dashboard"
        )
        await message.answer(text, parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {e}")


# ── Intercept Telegram Replies (Inbox Response System) ───────────────────────

@dp.message(F.reply_to_message)
async def handle_comment_reply(message: types.Message):
    original_text = message.reply_to_message.text or ""
    # Extract conversation ID from payload text [ID: c_123]
    match = re.search(r'\[ID: c_(\d+)\]', original_text)
    if not match:
        return # Not a reply to a forwarded comment
        
    conv_id = int(match.group(1))
    reply_text = message.text.strip()
    
    if not reply_text:
        await message.reply("❌ Ответ не может быть пустым.")
        return
        
    conv = await db.get_conversation(conv_id)
    if not conv:
        await message.reply("❌ Диалог не найден в базе данных.")
        return
        
    acc = await db.get_social_account(conv["social_account_id"])
    if not acc:
        await message.reply("❌ Социальный аккаунт не найден.")
        return
        
    platform = conv["platform"]
    success = False
    reply_id = None
    err_msg = None
    
    status_msg = await message.reply("🔄 Отправка ответа в соцсеть...")
    
    try:
        if platform == "threads":
            res = await meta_service.reply_to_threads_comment(
                access_token=acc["access_token"],
                parent_id=conv["external_thread_id"],
                reply_text=reply_text
            )
            success = res.get("success", False)
            reply_id = res.get("reply_id")
            err_msg = res.get("error")
            
        elif platform == "instagram":
            res = await meta_service.reply_to_instagram_comment(
                access_token=acc["access_token"],
                comment_id=conv["external_thread_id"],
                reply_text=reply_text
            )
            success = res.get("success", False)
            reply_id = res.get("reply_id")
            err_msg = res.get("error")
            
        elif platform == "whatsapp":
            res = await whatsapp_service.send_whatsapp_message(
                phone_number_id=acc["threads_user_id"],
                access_token=acc["access_token"],
                recipient_phone=conv["external_thread_id"],
                message_text=reply_text
            )
            success = res.get("success", False)
            reply_id = res.get("message_id")
            err_msg = res.get("error")
            
        if success:
            await db.add_message(
                conversation_id=conv_id,
                external_message_id=reply_id or f"out_{int(asyncio.get_event_loop().time())}",
                direction="outbound",
                message_text=reply_text
            )
            await status_msg.edit_text(f"✅ Ответ успешно опубликован в {platform.capitalize()}!")
        else:
            await status_msg.edit_text(f"❌ Ошибка публикации: {err_msg or 'неизвестная ошибка API'}")
            
    except Exception as e:
        logger.error(f"Reply routing failed: {e}")
        await status_msg.edit_text(f"❌ Системная ошибка отправки: {str(e)}")


if __name__ == "__main__":
    if not BOT_TOKEN:
        print("BOT_TOKEN is not set!")
    else:
        asyncio.run(dp.start_polling(bot))
