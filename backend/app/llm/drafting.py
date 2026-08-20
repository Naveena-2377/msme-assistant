"""
LLM-assisted drafting layer (Dev Step 10).

IMPORTANT per project spec: draft-only outputs. Never auto-sent.
Always shown to the owner for review before any external action.
Nothing in this module or the API routes that call it should ever
send an email, message, or notification directly — every function
here returns a draft string, full stop.

Uses the Gemini API (gemini-1.5-flash) via the current `google-genai`
SDK — chosen over Claude here specifically for its free tier, since
this project's spec allows "Claude API (or equivalent)". Swap this
module for a different provider by changing only _get_client() and
the .text extractions below; every calling route (app/api/drafts.py)
is provider-agnostic.

Requires GEMINI_API_KEY to be set (in a .env file in backend/, or as
an environment variable) to actually generate text. Without it, these
functions raise a clear RuntimeError rather than failing silently or
faking a response.
"""

import os
import json
from google import genai
from google.genai import types

_client = None

MODEL_NAME = "gemini-3.6-flash"


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it to a .env file in "
                "backend/ or export it as an environment variable to use "
                "LLM-assisted drafting."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def draft_collections_reminder(customer_name: str, amount: float, days_overdue: int) -> str:
    """
    Drafts a polite payment reminder for an overdue invoice. Returns
    plain text for the owner to review and send themselves — this
    function never sends anything.
    """
    prompt = (
        f"Write a short, polite payment reminder message (for WhatsApp or email) "
        f"to a business customer named '{customer_name}'. They have an invoice "
        f"that is {days_overdue} days overdue, for an amount of ₹{amount:,.2f}. "
        f"Keep it professional and not aggressive — this is a business relationship "
        f"worth preserving. Keep it under 80 words. Output only the message text, "
        f"no preamble or explanation."
    )
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text.strip()


def draft_vendor_email(supplier_name: str, context: str) -> str:
    """
    Drafts a vendor negotiation / communication email. `context`
    describes what the owner wants to say (e.g. "asking for a 5% bulk
    discount on a 500-unit order" or "asking about a delayed delivery").
    Returns plain text for review — never sent automatically.
    """
    prompt = (
        f"Write a short, professional business email to a supplier named "
        f"'{supplier_name}'. Context for what needs to be communicated: {context}. "
        f"Keep it concise and businesslike. Output only the email body text "
        f"(no subject line, no preamble)."
    )
    client = _get_client()
    response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
    return response.text.strip()


def parse_order_message(raw_text: str) -> dict:
    """
    Parses a free-form WhatsApp-style order message into a structured
    order (product name + quantity guesses). This is a parsing aid,
    not a database write — the caller is responsible for matching the
    parsed product names to real product_ids and confirming before
    anything is recorded.
    """
    prompt = (
        f"Extract the product name(s) and quantity from this informal order "
        f"message: \"{raw_text}\". Respond ONLY with valid JSON in this exact "
        f'format, nothing else: {{"items": [{{"product_name": "...", "quantity": 0}}]}}'
    )
    client = _get_client()
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    text = response.text.strip()
    # Defensive: strip markdown fences if the model adds them despite the
    # JSON mime type request.
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)
