"""Simple JSON file–based lead persistence (no external DB required)."""
import json
import os
import threading
from typing import List, Optional
from models.lead import Lead

_LOCK = threading.Lock()
_DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "leads.json")


def _read_all() -> List[dict]:
    if not os.path.exists(_DATA_FILE):
        return []
    with open(_DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _write_all(leads: List[dict]) -> None:
    os.makedirs(os.path.dirname(_DATA_FILE), exist_ok=True)
    with open(_DATA_FILE, "w") as f:
        json.dump(leads, f, indent=2, default=str)


def save_lead(lead: Lead) -> Lead:
    with _LOCK:
        leads = _read_all()
        # Upsert by id
        updated = False
        for i, l in enumerate(leads):
            if l.get("id") == lead.id:
                leads[i] = lead.to_dict()
                updated = True
                break
        if not updated:
            leads.append(lead.to_dict())
        _write_all(leads)
    return lead


def get_lead(lead_id: str) -> Optional[Lead]:
    for l in _read_all():
        if l.get("id") == lead_id:
            return Lead.from_dict(l)
    return None


def get_all_leads() -> List[Lead]:
    return [Lead.from_dict(l) for l in _read_all()]


def update_lead_status(lead_id: str, status: str) -> Optional[Lead]:
    with _LOCK:
        leads = _read_all()
        for l in leads:
            if l.get("id") == lead_id:
                l["status"] = status
                _write_all(leads)
                return Lead.from_dict(l)
    return None
