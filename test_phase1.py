import asyncio
import os
import json
from crypto_utils import encrypt_token, decrypt_token
import database as db

async def test_all():
    print("=== TESTING CRYPTOGRAPHY ===")
    token = "EAABsbCS_secret_meta_token_12345"
    encrypted = encrypt_token(token)
    decrypted = decrypt_token(encrypted)
    print(f"Original: {token}")
    print(f"Encrypted: {encrypted[:40]}...")
    print(f"Decrypted: {decrypted}")
    assert token == decrypted, "Crypto validation failed!"
    print("Crypto check: SUCCESS\n")

    print("=== TESTING DATABASE UPGRADES ===")
    # Initialize DB
    await db.init_db()
    
    # Test users
    user = await db.get_or_create_user(telegram_id=999888, username="tester", first_name="Testy")
    print(f"User created: {user}")
    
    # Test social accounts
    settings = {"daily_limit": 50, "auto_reply": 1}
    acc_id = await db.add_social_account(
        user_id=user["id"],
        platform="threads",
        platform_user_id="threads_usr_1",
        username="tester_threads",
        access_token=token,
        token_expires_at="2026-12-31T23:59:59",
        settings=json.dumps(settings)
    )
    print(f"Social account added with ID: {acc_id}")
    
    # Retrieve social account
    acc = await db.get_social_account(acc_id)
    print(f"Retrieved social account: {acc}")
    assert acc["access_token"] == token, "Decrypted token mismatch!"
    print("Token auto-decrypted: SUCCESS")
    
    # Retrieve all accounts
    accs = await db.get_social_accounts(user_id=user["id"])
    print(f"All social accounts for user: {accs}")
    assert len(accs) > 0, "No accounts retrieved!"
    
    # Test conversations
    conv = await db.get_or_create_conversation(
        social_account_id=acc_id,
        platform="threads",
        external_thread_id="thread_abc123",
        external_user_id="customer_999",
        external_username="customer_user"
    )
    print(f"Conversation get/create: {conv}")
    
    # Test messages
    msg_id = await db.add_message(
        conversation_id=conv["id"],
        external_message_id="msg_xyz789",
        direction="inbound",
        message_text="Привет, хочу получить гайд!",
        sentiment="positive"
    )
    print(f"Message added with ID: {msg_id}")
    
    msgs = await db.get_conversation_messages(conv["id"])
    print(f"Conversation messages: {msgs}")
    assert len(msgs) == 1, "Messages count mismatch!"
    
    # Test auto replies configs
    reply_config_id = await db.add_auto_reply_config(
        user_id=user["id"],
        social_account_id=acc_id,
        trigger_keyword="ХОЧУ",
        response_text="Вот ваш гайд: https://example.com/guide.pdf",
        response_type="dm",
        match_type="contains"
    )
    print(f"Auto-reply config added: {reply_config_id}")
    
    configs = await db.get_auto_reply_configs(user["id"])
    print(f"Auto-reply configs: {configs}")
    assert len(configs) > 0, "No configs retrieved!"
    
    # Log lead
    lead_id = await db.log_lead(
        user_id=user["id"],
        auto_reply_id=reply_config_id,
        conversation_id=conv["id"],
        recipient_external_id="customer_999",
        status="sent"
    )
    print(f"Lead logged with ID: {lead_id}")
    
    # Clean up test records
    async with db.aiosqlite.connect(db.DB_PATH) as conn:
        await conn.execute("DELETE FROM lead_logs WHERE id = ?", (lead_id,))
        await conn.execute("DELETE FROM auto_replies_config WHERE id = ?", (reply_config_id,))
        await conn.execute("DELETE FROM messages WHERE id = ?", (msg_id,))
        await conn.execute("DELETE FROM conversations WHERE id = ?", (conv["id"],))
        await conn.execute("DELETE FROM social_accounts WHERE id = ?", (acc_id,))
        await conn.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        await conn.commit()
    print("Database cleanup: COMPLETE")
    print("\n=== ALL TESTS PASSED SUCCESSFULLY ===")

if __name__ == "__main__":
    asyncio.run(test_all())
