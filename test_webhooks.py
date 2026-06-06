import asyncio
import os
import json
import sys
from unittest.mock import AsyncMock, patch

if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Set mock env variables before importing anything
os.environ["DB_PATH"] = "test_bot_factory.db"
os.environ["BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
os.environ["ADMIN_TELEGRAM_ID"] = "999888"
os.environ["ENCRYPTION_KEY"] = "wLdZ0kTwi3_5NiV9vuq4rfkdO3PMOOKA8yHb9Do7jNQ="

# Wiping the file and ensuring it exists so database.py doesn't copy the production/dev DB
if os.path.exists("test_bot_factory.db"):
    try:
        os.remove("test_bot_factory.db")
    except Exception:
        pass
with open("test_bot_factory.db", "w") as f:
    pass

from fastapi.testclient import TestClient
import database as db
from webapp import app

# Create FastAPI TestClient
client = TestClient(app)

async def test_webhook_flow():
    print("=== INITIALIZING DATABASE FOR WEBHOOK TESTS ===")
    await db.init_db()
    
    # 1. Create a mock user
    user = await db.get_or_create_user(telegram_id=999888, username="test_owner", first_name="TestOwner")
    user_id = user["id"]
    print(f"Created test user with ID: {user_id}")
    
    # 2. Create mock social accounts (WhatsApp and Threads)
    wa_account_id = await db.add_social_account(
        user_id=user_id,
        platform="whatsapp",
        platform_user_id="10928374656", # phone number ID
        username="79998887766", # phone number as username
        access_token="mock_whatsapp_token"
    )
    print(f"Created mock WhatsApp account with ID: {wa_account_id}")

    threads_account_id = await db.add_social_account(
        user_id=user_id,
        platform="threads",
        platform_user_id="888123456", # Threads user ID
        username="threads_test_user",
        access_token="mock_threads_token"
    )
    print(f"Created mock Threads account with ID: {threads_account_id}")

    # Patch the aiogram bot's send_message method to intercept notifications
    mock_send = AsyncMock()
    
    print("\n=== SIMULATING INCOMING WHATSAPP MESSAGE ===")
    # WhatsApp webhook payload structure
    wa_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "wa_biz_acc_123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "15550000000",
                        "phone_number_id": "10928374656"
                    },
                    "contacts": [{
                        "profile": {
                            "name": "Customer User"
                        },
                        "wa_id": "79112223344"
                    }],
                    "messages": [{
                        "from": "79112223344",
                        "id": "ABGGFlKwvUFQApqy_abc123",
                        "timestamp": "1672531199",
                        "text": {
                            "body": "Hello, I want to request pricing info!"
                        },
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    with patch("bot.bot.send_message", mock_send):
        response = client.post("/api/webhook/whatsapp", json=wa_payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        
    print("WhatsApp Webhook processed successfully.")
    
    # Verify database entry for conversation and message
    wa_conv = await db.get_or_create_conversation(social_account_id=wa_account_id, platform="whatsapp", external_thread_id="79112223344")
    assert wa_conv is not None, "WhatsApp conversation not found in database!"
    print(f"Found conversation in DB: {wa_conv}")
    
    wa_messages = await db.get_conversation_messages(wa_conv["id"])
    assert len(wa_messages) == 1, f"Expected 1 message, got {len(wa_messages)}"
    assert wa_messages[0]["message_text"] == "Hello, I want to request pricing info!"
    print(f"Found message in DB: {wa_messages[0]}")
    
    # Verify Telegram notification dispatching
    assert mock_send.called
    tg_args, tg_kwargs = mock_send.call_args
    sent_text = tg_kwargs.get("text", "")
    print(f"Intercepted TG Notification: \n{sent_text}")
    assert "WhatsApp" in sent_text
    assert f"[ID: c_{wa_conv['id']}]" in sent_text
    print("Telegram notification for WhatsApp: SUCCESS")
    
    # Reset mock_send
    mock_send.reset_mock()

    print("\n=== SIMULATING INCOMING THREADS COMMENT ===")
    threads_payload = {
        "object": "threads",
        "entry": [{
            "id": "888123456",
            "time": 1672531199,
            "changes": [{
                "value": {
                    "id": "threads_comment_abc987",
                    "text": "Great post! How do I sign up?",
                    "from": {
                        "id": "customer_threads_999",
                        "username": "happy_threads_client"
                    },
                    "media_id": "112233445566"
                },
                "field": "comments"
            }]
        }]
    }

    with patch("bot.bot.send_message", mock_send):
        response = client.post("/api/webhook/meta", json=threads_payload)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    print("Threads Webhook processed successfully.")

    # Verify database entry for conversation and message
    threads_conv = await db.get_or_create_conversation(social_account_id=threads_account_id, platform="threads", external_thread_id="threads_comment_abc987")
    assert threads_conv is not None, "Threads conversation not found in database!"
    print(f"Found conversation in DB: {threads_conv}")

    threads_messages = await db.get_conversation_messages(threads_conv["id"])
    assert len(threads_messages) == 1, f"Expected 1 message, got {len(threads_messages)}"
    assert threads_messages[0]["message_text"] == "Great post! How do I sign up?"
    print(f"Found message in DB: {threads_messages[0]}")

    # Verify Telegram notification dispatching
    assert mock_send.called
    tg_args, tg_kwargs = mock_send.call_args
    sent_text = tg_kwargs.get("text", "")
    print(f"Intercepted TG Notification: \n{sent_text}")
    assert "Threads" in sent_text
    assert f"[ID: c_{threads_conv['id']}]" in sent_text
    print("Telegram notification for Threads: SUCCESS")

    print("\n=== CLEANING UP DATABASE ===")
    # Sleep to let sqlite close connections
    await asyncio.sleep(0.5)
    
    # Try deleting the test database file
    if os.path.exists("test_bot_factory.db"):
        try:
            # We must close default connections in db module if active
            # For this test, we can just delete it next time or try now
            os.remove("test_bot_factory.db")
            print("Database file deleted: SUCCESS")
        except Exception as e:
            print(f"Could not delete database file (will be wiped on next start): {e}")

if __name__ == "__main__":
    asyncio.run(test_webhook_flow())
