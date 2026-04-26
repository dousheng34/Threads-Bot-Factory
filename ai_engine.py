"""
AI Engine — Gemini / Groq / OpenRouter
Free-tier providers for generating posts and replies.

Docs:
  Gemini:     https://aistudio.google.com/apikey   (15 RPM, 1500/day free)
  Groq:       https://console.groq.com             (fast, free tier)
  OpenRouter: https://openrouter.ai                (free models with :free suffix)
"""
import os, json, asyncio, random, logging
import aiohttp

log = logging.getLogger(__name__)

PROVIDER = os.getenv("AI_PROVIDER", "gemini").lower()
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")


async def _gemini(prompt: str, system: str = "") -> str:
    if not GEMINI_KEY:
        return ""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}"
    body = {
        "contents": [{"parts": [{"text": (system + "\n\n" + prompt).strip()}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 256},
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=body, timeout=aiohttp.ClientTimeout(total=30)) as r:
            d = await r.json()
            try:
                return d["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                log.warning("Gemini error: %s", d)
                return ""


async def _groq(prompt: str, system: str = "") -> str:
    if not GROQ_KEY:
        return ""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}"}
    body = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9, "max_tokens": 256,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
            d = await r.json()
            try:
                return d["choices"][0]["message"]["content"].strip()
            except Exception:
                log.warning("Groq error: %s", d)
                return ""


async def _openrouter(prompt: str, system: str = "") -> str:
    if not OPENROUTER_KEY:
        return ""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"}
    body = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system or "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.9, "max_tokens": 256,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as r:
            d = await r.json()
            try:
                return d["choices"][0]["message"]["content"].strip()
            except Exception:
                log.warning("OpenRouter error: %s", d)
                return ""


async def chat(prompt: str, system: str = "") -> str:
    """Provider-agnostic chat call. Falls back across providers if primary fails."""
    order = [PROVIDER] + [p for p in ("gemini", "groq", "openrouter") if p != PROVIDER]
    for p in order:
        try:
            if p == "gemini":
                t = await _gemini(prompt, system)
            elif p == "groq":
                t = await _groq(prompt, system)
            elif p == "openrouter":
                t = await _openrouter(prompt, system)
            else:
                t = ""
            if t:
                return t
        except Exception as e:
            log.warning("%s failed: %s", p, e)
    return ""


# ---------- High-level helpers ----------

REPLY_SYSTEM = (
    "You write short, natural replies for the social network Threads. "
    "Match the language of the comment. 1-2 sentences max. "
    "Sound like a real person, not a brand. No hashtags, no excessive emojis, no ads."
)

POST_SYSTEM = (
    "You write engaging Threads posts. Keep them under 500 chars. "
    "Hook in first line. Casual tone. Optional 1 emoji. No hashtag spam."
)


async def generate_reply(comment_text: str, post_context: str = "", style: str = "friendly") -> str:
    prompt = (
        f"Style: {style}.\n"
        f"Original post: {post_context or '(unknown)'}\n"
        f"Comment to reply to: {comment_text}\n\n"
        "Write the reply only, no quotes, no preamble."
    )
    return await chat(prompt, REPLY_SYSTEM)


async def generate_post(topic: str, niche: str = "", language: str = "ru") -> str:
    prompt = (
        f"Niche: {niche or 'general'}\n"
        f"Language: {language}\n"
        f"Topic: {topic}\n\n"
        "Write one Threads post. Output the post text only."
    )
    return await chat(prompt, POST_SYSTEM)


async def generate_post_batch(topic: str, count: int = 5, niche: str = "", language: str = "ru"):
    out = []
    for _ in range(count):
        t = await generate_post(topic, niche, language)
        if t:
            out.append(t)
        await asyncio.sleep(random.uniform(1.0, 2.5))
    return out


async def analyze_sentiment(text: str) -> str:
    """Returns one of: positive / neutral / negative / toxic."""
    p = (
        f"Classify the sentiment of this comment in ONE word "
        f"(positive, neutral, negative, toxic):\n{text}"
    )
    r = (await chat(p)).lower().strip().split()[0:1]
    return r[0] if r else "neutral"
