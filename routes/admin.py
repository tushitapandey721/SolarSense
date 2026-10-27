"""Admin dashboard routes (no auth for demo; add before production)."""
from flask import Blueprint, render_template, jsonify, request, redirect, url_for, abort
from services.lead_store import get_all_leads, get_lead, update_lead_status

admin_bp = Blueprint("admin", __name__)

VALID_STATUSES = ["new", "qualified", "contacted", "converted"]


@admin_bp.route("/")
def dashboard():
    leads = get_all_leads()
    # Sort newest first
    leads.sort(key=lambda l: l.created_at or "", reverse=True)

    stats = {
        "total": len(leads),
        "new": sum(1 for l in leads if l.status == "new"),
        "qualified": sum(1 for l in leads if l.status == "qualified"),
        "contacted": sum(1 for l in leads if l.status == "contacted"),
        "converted": sum(1 for l in leads if l.status == "converted"),
    }
    return render_template("admin/dashboard.html", leads=leads, stats=stats)


@admin_bp.route("/lead/<lead_id>")
def lead_detail(lead_id):
    lead = get_lead(lead_id)
    if not lead:
        abort(404)
    return render_template("admin/lead_detail.html", lead=lead)


@admin_bp.route("/lead/<lead_id>/status", methods=["POST"])
def update_status(lead_id):
    data = request.get_json(silent=True) or request.form
    status = data.get("status", "")
    if status not in VALID_STATUSES:
        return jsonify({"success": False, "error": "Invalid status."}), 400
    lead = update_lead_status(lead_id, status)
    if not lead:
        return jsonify({"success": False, "error": "Lead not found."}), 404
    if request.is_json:
        return jsonify({"success": True, "status": status})
    return redirect(url_for("admin.lead_detail", lead_id=lead_id))


@admin_bp.route("/api/leads")
def api_leads():
    """JSON endpoint for leads data (for AJAX refresh)."""
    leads = get_all_leads()
    leads.sort(key=lambda l: l.created_at or "", reverse=True)
    return jsonify([l.to_dict() for l in leads])
