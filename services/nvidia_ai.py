"""
Thin wrapper around NVIDIA NIM's OpenAI-compatible chat completion API.

Get a free API key at: https://build.nvidia.com
(sign in -> pick any chat model, e.g. "Llama 3.1 8B Instruct" -> "Get API Key")

Set it as an environment variable before running the app:
    export NVIDIA_API_KEY="nvapi-xxxxxxxx"

If the key is missing or the call fails for any reason, functions here
return None so callers can fall back to the existing rule-based text —
the app must keep working even with zero AI configured.
"""
import os
import requests

NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY")
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")

REQUEST_TIMEOUT_SECONDS = 12

SYSTEM_PROMPT = (
    "You are the AI assistant for SolarSense AI, a solar installation company "
    "serving customers in Pakistan. A customer is in the middle of a guided "
    "assessment form (answering questions about their electricity bill, roof, "
    "etc.) and instead of answering directly, they asked you something. "
    "Answer their question in 1-3 short, friendly sentences. Stay strictly on "
    "topics related to solar power, electricity bills, roofs, batteries, "
    "installation, cost, savings, or Pakistan's power situation. If the "
    "question is unrelated to any of that, politely say you can only help "
    "with solar questions right now. Do NOT ask the customer any new "
    "question yourself and do NOT repeat their original assessment question "
    "-- the app will re-show that separately. Keep it brief, no markdown, "
    "plain text only, may use one emoji at most."
)


def is_configured() -> bool:
    return bool(NVIDIA_API_KEY)


def answer_customer_question(user_message: str) -> "str | None":
    """
    Ask the LLM to answer an off-topic/side question the customer asked
    while in the middle of the assessment flow. Returns None on any
    failure so the caller can fall back to canned validation text.
    """
    if not NVIDIA_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": NVIDIA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.4,
        "max_tokens": 180,
        "stream": False,
    }

    try:
        resp = requests.post(
            NVIDIA_API_URL, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"].strip()
        return text or None
    except Exception as exc:  # network error, bad key, rate limit, malformed response...
        print(f"[nvidia_ai] LLM call failed, falling back to rule-based text: {exc}")
        return None
