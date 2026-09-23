from functools import wraps
import os

from flask import Blueprint, jsonify, session
from flask import request

from app import db
from app.agent import analyze_incident, analyze_weather
from app.model import IncidentReport


incidents_bp = Blueprint("incidents", __name__, url_prefix="/incidents")

weather_bp = Blueprint("weather", __name__, url_prefix="/weather")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return jsonify(error="login required"), 401
        return view(*args, **kwargs)

    return wrapped


def _incident_json(incident):
    return {
        "id": incident.id,
        "description": incident.description,
        "location": incident.location,
        "latitude": incident.latitude,
        "longitude": incident.longitude,
        "reported_by": incident.reported_by,
        "severity": incident.severity,
        "category": incident.category,
        "status": incident.status,
        "summary": incident.summary,
        "recommended_action": incident.recommended_action,
        "analysis_provider": incident.analysis_provider,
        "created_at": incident.created_at.isoformat() if incident.created_at else None,
    }


@incidents_bp.post("")
@login_required
def create_incident():
    data = request.get_json(silent=True) or request.form
    description = (data.get("description") or "").strip()
    if not description:
        return jsonify(error="description is required"), 400

    analysis = analyze_incident(description)
    try:
        latitude, longitude = _coordinates(data)
    except ValueError as error:
        return jsonify(error=str(error)), 400

    incident = IncidentReport(
        description=description,
        location=(data.get("location") or "").strip() or None,
        latitude=latitude,
        longitude=longitude,
        reported_by=session["user_id"],
        severity=analysis["severity"],
        category=analysis["category"],
        status="reported",
        summary=analysis["summary"],
        recommended_action=analysis["recommended_action"],
        analysis_provider=_provider_name(),
    )
    db.session.add(incident)
    db.session.commit()
    response = _incident_json(incident)
    return jsonify(response), 201


def _coordinates(data):
    coordinates = []
    for field, minimum, maximum in (
        ("latitude", -90, 90),
        ("longitude", -180, 180),
    ):
        value = data.get(field)
        if value in (None, ""):
            coordinates.append(None)
            continue
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be a number")
        if not minimum <= value <= maximum:
            raise ValueError(f"{field} must be between {minimum} and {maximum}")
        coordinates.append(value)
    return coordinates


def _provider_name():
    provider = os.getenv("RESQAI_LLM_PROVIDER", "gemini").lower()
    return provider if provider in {"gemini", "ollama"} else "fallback"


@incidents_bp.get("")
@login_required
def list_incidents():
    incidents = IncidentReport.query.order_by(IncidentReport.created_at.desc()).all()
    return jsonify(incidents=[_incident_json(incident) for incident in incidents])


@incidents_bp.get("/<int:incident_id>")
@login_required
def get_incident(incident_id):
    incident = db.get_or_404(IncidentReport, incident_id)
    return jsonify(_incident_json(incident))


@incidents_bp.patch("/<int:incident_id>")
@login_required
def update_incident(incident_id):
    incident = db.get_or_404(IncidentReport, incident_id)
    data = request.get_json(silent=True) or request.form
    status = (data.get("status") or "").strip().lower()
    allowed_statuses = {"reported", "acknowledged", "in_progress", "resolved"}
    if status not in allowed_statuses:
        return jsonify(error="status must be reported, acknowledged, in_progress, or resolved"), 400
    incident.status = status
    db.session.commit()
    return jsonify(_incident_json(incident))


@weather_bp.post("/analyze")
@login_required
def weather_analysis():
    data = request.get_json(silent=True) or request.form
    try:
        return jsonify(analyze_weather(data.get("location")))
    except (OSError, TimeoutError, ValueError, KeyError, IndexError):
        return jsonify(error="The weather agent could not analyze that location right now."), 502