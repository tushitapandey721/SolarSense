"""Chat API routes — /api/chat, /api/start-assessment, /api/submit-lead."""
from flask import Blueprint, request, jsonify, session
from services.chatbot import process_message, STATE_GREETING
from services.lead_store import save_lead, get_lead
from services.solar_calc import calculate_recommendation
from services.bill_ocr import extract_bill_details
from services import whatsapp_notify
from models.lead import Lead

chat_bp = Blueprint("chat", __name__)

ALLOWED_BILL_TYPES = {"image/jpeg", "image/png", "image/webp", "application/pdf"}
ALLOWED_BILL_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".pdf")
MAX_BILL_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 MB


@chat_bp.route("/start-assessment", methods=["POST"])
def start_assessment():
    """Initialise a fresh conversation session."""
    session.clear()
    session["state"] = STATE_GREETING
    session["lead_data"] = {}

    # Send greeting
    response, updated_session = process_message("", session)
    session["state"] = updated_session["state"]
    session["lead_data"] = updated_session["lead_data"]
    session.modified = True

    return jsonify({"success": True, "response": response})


@chat_bp.route("/chat", methods=["POST"])
def chat():
    """Handle one user message in the conversation state machine."""
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"success": False, "error": "Message cannot be empty."}), 400

    if "state" not in session:
        return jsonify({
            "success": False,
            "error": "Session expired. Please start a new assessment."
        }), 400

    response, updated_session = process_message(user_message, dict(session))
    session["state"] = updated_session["state"]
    session["lead_data"] = updated_session["lead_data"]
    session.modified = True

    # If conversation is complete, persist lead and generate recommendation
    if response.get("complete"):
        lead_data = updated_session.get("lead_data", {})
        lead = Lead(
            monthly_bill=lead_data.get("monthly_bill"),
            name=lead_data.get("name"),
            phone=lead_data.get("phone"),
            city=lead_data.get("city"),
            house_ownership=lead_data.get("house_ownership"),
            roof_type=lead_data.get("roof_type"),
            roof_area=lead_data.get("roof_area"),
            battery_required=lead_data.get("battery_required"),
        )
        rec = calculate_recommendation(lead)
        lead.recommendation = rec
        lead.status = "qualified"
        save_lead(lead)
        session["lead_id"] = lead.id
        response["recommendation"] = rec
        response["lead_id"] = lead.id

        whatsapp_notify.notify_new_assessment_lead(lead)

    return jsonify({"success": True, "response": response})


@chat_bp.route("/submit-lead", methods=["POST"])
def submit_lead():
    """Submit additional contact info or update an existing lead."""
    data = request.get_json(silent=True) or {}
    lead_id = data.get("lead_id") or session.get("lead_id")

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    city = data.get("city", "").strip()
    message = data.get("message", "").strip()

    errors = {}
    if not name or len(name) < 2:
        errors["name"] = "Please enter your full name."
    if not phone or len(phone) < 10:
        errors["phone"] = "Please enter a valid phone number."
    if not city:
        errors["city"] = "Please enter your city."

    if errors:
        return jsonify({"success": False, "errors": errors}), 422

    if lead_id:
        lead = get_lead(lead_id)
    else:
        lead = None

    if lead is None:
        lead = Lead(name=name, phone=phone, city=city)
    else:
        lead.name = name
        lead.phone = phone
        lead.city = city

    if message:
        lead.recommendation = lead.recommendation or {}
        lead.recommendation["contact_message"] = message

    save_lead(lead)

    whatsapp_notify.notify_new_quick_enquiry(lead, message)

    return jsonify({
        "success": True,
        "message": "Thank you! Anit Pandey has been notified and will call you soon — you can also call him directly at +91 80050 04777 (9 AM – 6 PM).",
        "lead_id": lead.id,
    })


@chat_bp.route("/upload-bill", methods=["POST"])
def upload_bill():
    """Accepts a photo/scan/PDF of an electricity bill and returns extracted details."""
    if "bill" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded."}), 400

    file = request.files["bill"]
    if not file.filename:
        return jsonify({"success": False, "error": "No file selected."}), 400

    file_bytes = file.read()
    if len(file_bytes) > MAX_BILL_UPLOAD_BYTES:
        return jsonify({"success": False, "error": "File is too large (max 8MB)."}), 400

    mime = (file.mimetype or "").lower()
    is_allowed = mime in ALLOWED_BILL_TYPES or file.filename.lower().endswith(ALLOWED_BILL_EXTENSIONS)
    if not is_allowed:
        return jsonify({"success": False, "error": "Please upload a JPG, PNG, or PDF file."}), 400

    result = extract_bill_details(file_bytes, mime, file.filename)
    if not result["success"]:
        return jsonify({"success": False, "error": result["error"]}), 422

    return jsonify({"success": True, "data": result["data"]})
