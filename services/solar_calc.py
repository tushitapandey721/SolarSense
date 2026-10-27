"""Solar recommendation engine — pure Python, no AI decisions."""

# Average sun hours by Pakistan city (peak sun hours/day)
CITY_SUN_HOURS = {
    "karachi": 6.5, "lahore": 5.5, "islamabad": 5.0, "rawalpindi": 5.0,
    "faisalabad": 5.8, "multan": 6.2, "peshawar": 5.2, "quetta": 6.8,
    "sialkot": 5.4, "hyderabad": 6.4, "gujranwala": 5.6, "bahawalpur": 6.3,
    "sargodha": 5.7, "sukkur": 6.6, "larkana": 6.5, "sheikhupura": 5.5,
    "default": 5.5,
}

PANEL_WATT_PEAK = 550          # Modern mono-PERC panel (W)
PANEL_PRICE_PKR = 38_000       # Per panel installed
BATTERY_PRICE_PKR = 85_000     # Per 100 Ah / 12 V unit
INVERTER_PRICE_PKR = 55_000    # Hybrid inverter (fixed for sizing)

COST_PER_UNIT_PKR = 25         # Average electricity tariff
UNITS_PER_KWH = 1
MONTHLY_DAYS = 30
EFFICIENCY_FACTOR = 0.80       # System derating


def calculate_recommendation(lead) -> dict:
    bill = lead.monthly_bill or 0
    city = (lead.city or "").lower().strip()
    sun_hours = CITY_SUN_HOURS.get(city, CITY_SUN_HOURS["default"])
    roof_area = lead.roof_area or 0
    battery_required = lead.battery_required or False
    ownership = lead.house_ownership or "owned"
    roof_type = lead.roof_type or "flat"

    # --- Energy calculations ---
    monthly_units = bill / COST_PER_UNIT_PKR if bill else 0
    daily_kwh = monthly_units / MONTHLY_DAYS

    # Required system size (kW)
    required_kw = daily_kwh / (sun_hours * EFFICIENCY_FACTOR)
    required_kw = max(required_kw, 1.0)  # Minimum 1 kW

    # Cap by available roof area (1 panel ≈ 2.0 m²)
    max_panels_by_area = int(roof_area / 2.0) if roof_area > 0 else 999
    panels_needed = max(1, round(required_kw * 1000 / PANEL_WATT_PEAK))
    panels_installed = min(panels_needed, max_panels_by_area)

    system_kw = round(panels_installed * PANEL_WATT_PEAK / 1000, 2)
    annual_gen_kwh = round(system_kw * sun_hours * 365 * EFFICIENCY_FACTOR, 0)
    monthly_savings = round(min(monthly_units, system_kw * sun_hours * 30 * EFFICIENCY_FACTOR) * COST_PER_UNIT_PKR, 0)
    annual_savings = monthly_savings * 12

    # --- Cost estimation ---
    panel_cost = panels_installed * PANEL_PRICE_PKR
    battery_count = max(1, round(daily_kwh / 1.2)) if battery_required else 0
    battery_cost = battery_count * BATTERY_PRICE_PKR
    total_cost = panel_cost + battery_cost + INVERTER_PRICE_PKR

    payback_years = round(total_cost / annual_savings, 1) if annual_savings > 0 else 0

    # --- Suitability score (0–100) ---
    score = 50
    if bill >= 5000:
        score += 20
    elif bill >= 2000:
        score += 10
    if ownership == "owned":
        score += 15
    if roof_type in ("flat", "sloped"):
        score += 10
    if roof_area >= 30:
        score += 5
    score = min(score, 100)

    # Suitability label
    if score >= 80:
        suitability = "Excellent"
        suitability_msg = "Your property is an ideal candidate for solar!"
    elif score >= 60:
        suitability = "Good"
        suitability_msg = "Solar will work very well for your property."
    else:
        suitability = "Moderate"
        suitability_msg = "Solar can still help reduce your bills."

    # Roof type note
    roof_notes = {
        "flat": "Flat roofs allow optimal panel tilt adjustment for maximum yield.",
        "sloped": "Sloped roofs often align naturally with ideal south-facing orientation.",
        "mixed": "Mixed roof configurations can be optimised with careful panel placement.",
    }

    return {
        "suitability_score": score,
        "suitability_label": suitability,
        "suitability_message": suitability_msg,
        "system_size_kw": system_kw,
        "panels_count": panels_installed,
        "annual_generation_kwh": int(annual_gen_kwh),
        "monthly_savings_pkr": int(monthly_savings),
        "annual_savings_pkr": int(annual_savings),
        "total_cost_pkr": int(total_cost),
        "payback_years": payback_years,
        "battery_units": battery_count,
        "sun_hours_per_day": sun_hours,
        "roof_note": roof_notes.get(roof_type, ""),
        "co2_saved_kg_per_year": round(annual_gen_kwh * 0.4, 0),
    }
