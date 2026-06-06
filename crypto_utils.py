import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(ENV_PATH)

ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    # Generate a new key and save it to .env or environment
    key = Fernet.generate_key().decode()
    os.environ["ENCRYPTION_KEY"] = key
    ENCRYPTION_KEY = key
    try:
        if not os.path.exists(ENV_PATH):
            with open(ENV_PATH, "w", encoding="utf-8") as f:
                f.write(f"ENCRYPTION_KEY={key}\n")
        else:
            # Simple append or insert to avoid importing dotenv's set_key which might fail
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                content = f.read()
            if "ENCRYPTION_KEY" not in content:
                divider = "\n" if not content.endswith("\n") else ""
                with open(ENV_PATH, "a", encoding="utf-8") as f:
                    f.write(f"{divider}ENCRYPTION_KEY={key}\n")
        print("[crypto] Generated and saved new ENCRYPTION_KEY to .env")
    except Exception as e:
        print(f"[crypto] Failed to write key to .env: {e}")

try:
    _cipher = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    print(f"[crypto] Invalid ENCRYPTION_KEY. Generating a temporary key. Error: {e}")
    _cipher = Fernet(Fernet.generate_key())

def encrypt_token(plain_text: str) -> str:
    if not plain_text:
        return ""
    return _cipher.encrypt(plain_text.encode()).decode()

def decrypt_token(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        return _cipher.decrypt(cipher_text.encode()).decode()
    except Exception as e:
        print(f"[crypto] Decryption error: {e}")
        return ""
