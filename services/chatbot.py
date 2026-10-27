"""Conversation state machine — Python controls all flow, no AI decisions.

AI (NVIDIA NIM) is used only as an *optional* layer to answer side
questions a customer asks mid-flow (e.g. "why do I need battery backup?").
It never decides state transitions and never parses/validates lead data —
that stays 100% deterministic so leads can't be corrupted by a bad LLM
response.
"""
import re
from typing import Tuple

from services import nvidia_ai

# Words/patterns that suggest the user asked a question rather than
# attempting to answer the current prompt.
_QUESTION_HINTS = re.compile(
    r"\?|^(why|how|what|which|when|where|who|can|does|is|are|do|will|should)\b",
    re.IGNORECASE,
)


def _looks_like_question(text: str) -> bool:
    return bool(_QUESTION_HINTS.search(text.strip()))

# ---------------------------------------------------------------------------
# State constants
# ---------------------------------------------------------------------------
STATE_GREETING = "greeting"
STATE_ASK_BILL = "ask_bill"
STATE_ASK_NAME = "ask_name"
STATE_ASK_PHONE = "ask_phone"
STATE_ASK_CITY = "ask_city"
STATE_ASK_OWNERSHIP = "ask_ownership"
STATE_ASK_ROOF_TYPE = "ask_roof_type"
STATE_ASK_ROOF_AREA = "ask_roof_area"
STATE_ASK_BATTERY = "ask_battery"
STATE_COMPLETE = "complete"

# Step ordering (for progress tracking)
STEPS = [
    STATE_ASK_BILL,
    STATE_ASK_NAME,
    STATE_ASK_PHONE,
    STATE_ASK_CITY,
    STATE_ASK_OWNERSHIP,
    STATE_ASK_ROOF_TYPE,
    STATE_ASK_ROOF_AREA,
    STATE_ASK_BATTERY,
    STATE_COMPLETE,
]

# ---------------------------------------------------------------------------
# Messages Python generates for each state
# ---------------------------------------------------------------------------
STATE_PROMPTS = {
    STATE_ASK_BILL: (
        "What is your average monthly electricity bill in PKR? "
        "(e.g. 5000, 12000)"
    ),
    STATE_ASK_NAME: "Great! What is your full name?",
    STATE_ASK_PHONE: "Please share your phone number so our advisor can reach you.",
    STATE_ASK_CITY: "Which city are you located in?",
    STATE_ASK_OWNERSHIP: (
        "Do you own or rent your home? "
        "Please reply with <strong>owned</strong> or <strong>rented</strong>."
    ),
    STATE_ASK_ROOF_TYPE: (
        "What type of roof does your property have? "
        "Reply with <strong>flat</strong>, <strong>sloped</strong>, or <strong>mixed</strong>."
    ),
    STATE_ASK_ROOF_AREA: (
        "Approximately what is the usable roof area in square metres? "
        "(e.g. 40, 80, 150)"
    ),
    STATE_ASK_BATTERY: (
        "Do you require battery backup for load-shedding? "
        "Reply <strong>yes</strong> or <strong>no</strong>."
    ),
}

# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_bill(text: str) -> Tuple[bool, str, float]:
    digits = re.sub(r"[,\s]", "", text.strip())
    try:
        value = float(digits)
        if value < 100:
            return False, "Please enter a valid monthly bill amount (minimum PKR 100).", 0
        if value > 500_000:
            return False, "That seems very high. Please double-check your monthly bill amount.", 0
        return True, "", value
    except ValueError:
        return False, "Please enter a numeric value for your electricity bill (e.g. 8000).", 0


def _validate_name(text: str) -> Tuple[bool, str, str]:
    name = text.strip()
    if len(name) < 2:
        return False, "Please enter your full name (at least 2 characters).", ""
    if re.search(r"\d", name):
        return False, "Name should not contain numbers. Please enter your full name.", ""
    return True, "", name.title()


def _validate_phone(text: str) -> Tuple[bool, str, str]:
    digits = re.sub(r"[\s\-\(\)\+]", "", text.strip())
    if not digits.isdigit():
        return False, "Please enter a valid phone number (digits only).", ""
    if len(digits) < 10 or len(digits) > 13:
        return False, "Phone number should be 10–13 digits. Please try again.", ""
    return True, "", digits


def _validate_city(text: str) -> Tuple[bool, str, str]:
    city = text.strip()
    if len(city) < 2:
        return False, "Please enter a valid city name.", ""
    if re.search(r"\d", city):
        return False, "City name should not contain numbers. Please enter your city.", ""
    return True, "", city.title()


def _validate_ownership(text: str) -> Tuple[bool, str, str]:
    val = text.strip().lower()
    if val in ("owned", "own", "yes", "owner", "mine"):
        return True, "", "owned"
    if val in ("rented", "rent", "tenant", "renter", "no"):
        return True, "", "rented"
    return False, "Please reply with <strong>owned</strong> or <strong>rented</strong>.", ""


def _validate_roof_type(text: str) -> Tuple[bool, str, str]:
    val = text.strip().lower()
    if val in ("flat", "flat roof"):
        return True, "", "flat"
    if val in ("sloped", "slope", "pitched", "angled"):
        return True, "", "sloped"
    if val in ("mixed", "both", "combination"):
        return True, "", "mixed"
    return False, "Please reply with <strong>flat</strong>, <strong>sloped</strong>, or <strong>mixed</strong>.", ""


def _validate_roof_area(text: str) -> Tuple[bool, str, float]:
    digits = re.sub(r"[,\s]", "", text.strip())
    # Strip common unit suffixes
    digits = re.sub(r"(sqm|sq\.m|m2|sqft|sq\.ft|ft2|square.*)", "", digits, flags=re.I).strip()
    try:
        value = float(digits)
        if value < 5:
            return False, "Roof area seems too small. Please enter area in square metres (e.g. 40).", 0
        if value > 10_000:
            return False, "That seems very large. Please enter area in square metres.", 0
        return True, "", value
    except ValueError:
        return False, "Please enter the roof area as a number in square metres (e.g. 80).", 0


def _validate_battery(text: str) -> Tuple[bool, str, bool]:
    val = text.strip().lower()
    if val in ("yes", "y", "yeah", "yep", "sure", "needed", "required", "ha", "haan"):
        return True, "", True
    if val in ("no", "n", "nope", "not needed", "not required", "nahi"):
        return True, "", False
    return False, "Please reply with <strong>yes</strong> or <strong>no</strong>.", False


# ---------------------------------------------------------------------------
# State machine processor
# ---------------------------------------------------------------------------

VALIDATORS = {
    STATE_ASK_BILL: _validate_bill,
    STATE_ASK_NAME: _validate_name,
    STATE_ASK_PHONE: _validate_phone,
    STATE_ASK_CITY: _validate_city,
    STATE_ASK_OWNERSHIP: _validate_ownership,
    STATE_ASK_ROOF_TYPE: _validate_roof_type,
    STATE_ASK_ROOF_AREA: _validate_roof_area,
    STATE_ASK_BATTERY: _validate_battery,
}

FIELD_MAP = {
    STATE_ASK_BILL: "monthly_bill",
    STATE_ASK_NAME: "name",
    STATE_ASK_PHONE: "phone",
    STATE_ASK_CITY: "city",
    STATE_ASK_OWNERSHIP: "house_ownership",
    STATE_ASK_ROOF_TYPE: "roof_type",
    STATE_ASK_ROOF_AREA: "roof_area",
    STATE_ASK_BATTERY: "battery_required",
}

NEXT_STATE = {
    STATE_GREETING: STATE_ASK_BILL,
    STATE_ASK_BILL: STATE_ASK_NAME,
    STATE_ASK_NAME: STATE_ASK_PHONE,
    STATE_ASK_PHONE: STATE_ASK_CITY,
    STATE_ASK_CITY: STATE_ASK_OWNERSHIP,
    STATE_ASK_OWNERSHIP: STATE_ASK_ROOF_TYPE,
    STATE_ASK_ROOF_TYPE: STATE_ASK_ROOF_AREA,
    STATE_ASK_ROOF_AREA: STATE_ASK_BATTERY,
    STATE_ASK_BATTERY: STATE_COMPLETE,
}


def get_progress(state: str) -> dict:
    total = len(STEPS) - 1  # exclude COMPLETE from count
    if state in (STATE_GREETING, STATE_COMPLETE):
        current = total if state == STATE_COMPLETE else 0
    else:
        current = STEPS.index(state) if state in STEPS else 0
    return {"current": current, "total": total, "percent": int(current / total * 100)}


def process_message(user_message: str, session_data: dict) -> Tuple[dict, dict]:
    """
    Process one user message given the current session_data.
    Returns (response_dict, updated_session_data).

    session_data keys:
      - state: current state string
      - lead_data: dict of collected fields
    """
    state = session_data.get("state", STATE_GREETING)
    lead_data = session_data.get("lead_data", {})

    # --- Initial greeting ---
    if state == STATE_GREETING:
        next_state = NEXT_STATE[STATE_GREETING]
        session_data["state"] = next_state
        session_data["lead_data"] = lead_data
        response = {
            "message": (
                "👋 Welcome to <strong>SolarSense AI</strong>! I'll help you find the perfect "
                "solar solution for your home in just a few steps.<br><br>"
                + STATE_PROMPTS[next_state]
            ),
            "state": next_state,
            "progress": get_progress(next_state),
            "complete": False,
        }
        return response, session_data

    # --- Validate current input ---
    if state in VALIDATORS:
        # Check for a genuine side question *before* running the validator.
        # Some validators (name, city) are permissive enough that a
        # question like "why do you need my name?" would otherwise pass
        # straight through and get stored as the answer.
        if _looks_like_question(user_message) and nvidia_ai.is_configured():
            llm_answer = nvidia_ai.answer_customer_question(user_message)
            if llm_answer:
                response = {
                    "message": (
                        f"{llm_answer}"
                        f"<br><br>Now, back to your assessment — "
                        f"{STATE_PROMPTS[state]}"
                    ),
                    "state": state,
                    "progress": get_progress(state),
                    "complete": False,
                    "error": False,
                    "ai_answered": True,
                }
                return response, session_data
            # LLM unavailable/failed — fall through to normal validation.

        validator = VALIDATORS[state]
        valid, error_msg, parsed_value = validator(user_message)

        if not valid:
            response = {
                "message": f"⚠️ {error_msg}",
                "state": state,
                "progress": get_progress(state),
                "complete": False,
                "error": True,
            }
            return response, session_data

        # Store validated value
        field = FIELD_MAP[state]
        lead_data[field] = parsed_value
        session_data["lead_data"] = lead_data

        # Advance state
        next_state = NEXT_STATE[state]
        session_data["state"] = next_state

        if next_state == STATE_COMPLETE:
            response = {
                "message": (
                    "✅ Thank you! I've collected all the information needed to generate "
                    "your personalised solar recommendation. Please wait a moment…"
                ),
                "state": STATE_COMPLETE,
                "progress": get_progress(STATE_COMPLETE),
                "complete": True,
                "lead_data": lead_data,
            }
        else:
            # Confirmation + next question.
            # NOTE: build only the confirmation for the *current* state —
            # a dict literal evaluates every value eagerly, so putting all
            # of these in one dict (as before) crashed whenever a later
            # branch's f-string assumed the wrong type for parsed_value.
            confirm_builders = {
                STATE_ASK_BILL: lambda v: f"Got it — PKR {int(v):,}/month.",
                STATE_ASK_NAME: lambda v: f"Nice to meet you, {v}!",
                STATE_ASK_PHONE: lambda v: "Phone number saved. ✓",
                STATE_ASK_CITY: lambda v: f"{v} — a great location for solar!",
                STATE_ASK_OWNERSHIP: lambda v: f"Property status: {v.capitalize()}. ✓",
                STATE_ASK_ROOF_TYPE: lambda v: f"Roof type: {v.capitalize()}. ✓",
                STATE_ASK_ROOF_AREA: lambda v: f"Roof area: {v:.0f} m². ✓",
                STATE_ASK_BATTERY: lambda v: "Battery preference noted. ✓",
            }
            builder = confirm_builders.get(state)
            confirm = builder(parsed_value) if builder else ""
            response = {
                "message": f"{confirm}<br><br>{STATE_PROMPTS[next_state]}",
                "state": next_state,
                "progress": get_progress(next_state),
                "complete": False,
            }

        return response, session_data

    # Fallback — should not happen
    response = {
        "message": "Something went wrong. Please refresh and start again.",
        "state": state,
        "progress": get_progress(state),
        "complete": False,
    }
    return response, session_data
