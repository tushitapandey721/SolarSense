"""
Sends a WhatsApp notification to the sales owner (Anit Pandey) whenever a
new lead registers — either by completing the full AI assessment or by
submitting the "Quick Enquiry" form on the homepage.

Uses CallMeBot (https://www.callmebot.com/blog/free-api-whatsapp-messages/),
a free personal-notification API. It does NOT require Meta Business
approval — it's meant for exactly this "ping my own WhatsApp" use case.

One-time setup for Anit Pandey (or whoever should receive alerts):
  1. Save this contact on your phone: +34 644 59 71 65 (CallMeBot's number)
  2. Send it a WhatsApp message: "I allow callmebot to send me messages"
  3. You'll get a reply with your personal apikey (a number)
  4. Put that apikey + your own WhatsApp number in .env (see below)

If not configured, this fails silently (logs only) — a missing
notification must never block someone from submitting a lead.
"""
import os
import urllib.parse

import requests

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE")  # e.g. 918005004777 (no + or spaces)
CALLMEBOT_API_KEY = os.environ.get("CALLMEBOT_API_KEY")

REQUEST_TIMEOUT_SECONDS = 10


def is_configured() -> bool:
    return bool(CALLMEBOT_PHONE and CALLMEBOT_API_KEY)


def _send(text: str) -> bool:
    if not is_configured():
        print("[whatsapp_notify] Not configured (missing CALLMEBOT_PHONE/CALLMEBOT_API_KEY) — skipping.")
        return False
    try:
        params = {
            "phone": CALLMEBOT_PHONE,
            "text": text,
            "apikey": CALLMEBOT_API_KEY,
        }
        url = f"{CALLMEBOT_URL}?{urllib.parse.urlencode(params)}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        resp.raise_for_status()
        return True
    except Exception as exc:
        print(f"[whatsapp_notify] Failed to send WhatsApp notification: {exc}")
        return False


def notify_new_assessment_lead(lead) -> bool:
    """Notify about a lead who completed the full AI solar assessment."""
    bill = f"PKR {int(lead.monthly_bill):,}" if lead.monthly_bill else "N/A"
    system_kw = None
    monthly_savings = None
    if lead.recommendation:
        system_kw = lead.recommendation.get("system_size_kw")
        monthly_savings = lead.recommendation.get("monthly_savings_pkr")

    lines = [
        "🌞 New SolarSense Lead (Full Assessment)",
        f"Name: {lead.name or 'N/A'}",
        f"Phone: {lead.phone or 'N/A'}",
        f"City: {lead.city or 'N/A'}",
        f"Monthly bill: {bill}",
    ]
    if system_kw:
        lines.append(f"Recommended system: {system_kw} kW")
    if monthly_savings:
        lines.append(f"Est. monthly savings: PKR {int(monthly_savings):,}")

    return _send("\n".join(lines))


def notify_new_quick_enquiry(lead, message: str = "") -> bool:
    """Notify about a lead from the homepage 'Quick Enquiry' contact form."""
    lines = [
        "📩 New SolarSense Quick Enquiry",
        f"Name: {lead.name or 'N/A'}",
        f"Phone: {lead.phone or 'N/A'}",
        f"City: {lead.city or 'N/A'}",
    ]
    if message:
        lines.append(f"Message: {message}")

    return _send("\n".join(lines))
