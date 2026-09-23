import json
import os
import urllib.parse
import urllib.error
import urllib.request


DEFAULT_RESULT = {
    "category": "other",
    "severity": 1,
    "summary": "Incident requires review.",
    "recommended_action": "Collect more information and notify the response coordinator.",
}

WEATHER_CODES = {
    0: "clear sky",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "freezing fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "showers",
    82: "heavy showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "severe thunderstorm with hail",
}


def analyze_incident(description):
    """Return a stable incident shape using the configured free provider or fallback."""
    description = (description or "").strip()
    if not description:
        return dict(DEFAULT_RESULT)

    provider = os.getenv("RESQAI_LLM_PROVIDER", "gemini").lower()
    try:
        if provider == "gemini":
            result = _call_gemini(description)
        elif provider == "ollama":
            result = _call_ollama(description)
        else:
            return _keyword_fallback(description)
        return _normalise_result(result)
    except (
        OSError,
        TimeoutError,
        TypeError,
        ValueError,
        KeyError,
        IndexError,
        json.JSONDecodeError,
    ):
        return _keyword_fallback(description)


def _call_gemini(description):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _keyword_fallback(description)

    prompt = (
        "Analyze this disaster incident. Return JSON only with exactly these keys: "
        "category, severity (integer 1-5), summary, recommended_action.\n\n"
        f"Incident: {description}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {
        "responseMimeType": "application/json"
    }}
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-2.0-flash:generateContent?key=" + api_key
    )
    response = _post_json(url, payload)
    text = response["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


def _call_ollama(description):
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "stream": False,
        "format": "json",
        "prompt": (
            "Return JSON with category, severity (1-5), summary, "
            f"recommended_action for this incident: {description}"
        ),
    }
    response = _post_json(
        os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"), payload
    )
    return json.loads(response["response"])


def _post_json(url, payload):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status >= 400:
            raise OSError(f"LLM request failed with status {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _normalise_result(result):
    if not isinstance(result, dict):
        raise TypeError("LLM response must be a JSON object")
    normalised = dict(DEFAULT_RESULT)
    normalised.update({key: result[key] for key in normalised if key in result})
    normalised["severity"] = max(1, min(5, int(normalised["severity"])))
    return normalised


def _keyword_fallback(description):
    text = description.lower()
    categories = {
        "fire": ("fire", 4),
        "flood": ("flood", 4),
        "medical": ("medical", 3),
        "earthquake": ("earthquake", 5),
        "collapse": ("structural_damage", 5),
        "trapped": ("rescue", 5),
    }
    category, severity = "other", 1
    for keyword, match in categories.items():
        if keyword in text:
            category, severity = match
            break
    return _normalise_result({
        "category": category,
        "severity": severity,
        "summary": description[:200],
        "recommended_action": "Contact local emergency services and provide the exact location.",
    })


def analyze_weather(location):
    """Predict near-term weather hazards for a place using Open-Meteo data."""
    location = (location or "").strip()
    if not location:
        raise ValueError("location is required")

    place = _geocode_location(location)
    forecast = _weather_forecast(place["latitude"], place["longitude"])
    days = _score_weather_days(forecast)
    peak = max(days, key=lambda day: day["risk_score"])
    risk = peak["risk_level"]
    hazards = sorted({hazard for day in days for hazard in day["hazards"]})
    actions = _weather_actions(hazards, risk)
    return {
        "agent": "ResQAI Preventive Weather Agent",
        "location": place["name"],
        "latitude": place["latitude"],
        "longitude": place["longitude"],
        "timezone": forecast.get("timezone"),
        "risk_level": risk,
        "risk_score": peak["risk_score"],
        "hazards": hazards or ["no significant hazard detected"],
        "headline": _weather_headline(risk, hazards, peak),
        "reasoning": _weather_reasoning(peak, days),
        "recommended_actions": actions,
        "forecast": days,
        "source": "Open-Meteo forecast model (free, no API key)",
    }


def _geocode_location(location):
    query = urllib.parse.quote(location)
    response = _get_json(
        "https://geocoding-api.open-meteo.com/v1/search?name="
        f"{query}&count=1&language=en&format=json"
    )
    results = response.get("results") or []
    if not results:
        raise ValueError(f"could not find a location named '{location}'")
    result = results[0]
    return {
        "name": ", ".join(filter(None, [result.get("name"), result.get("country")])),
        "latitude": float(result["latitude"]),
        "longitude": float(result["longitude"]),
    }


def _weather_forecast(latitude, longitude):
    query = urllib.parse.urlencode({
        "latitude": latitude,
        "longitude": longitude,
        "forecast_days": 5,
        "timezone": "auto",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,wind_speed_10m_max",
    })
    return _get_json(f"https://api.open-meteo.com/v1/forecast?{query}")


def _get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "ResQAI/1.0"})
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status >= 400:
            raise OSError(f"weather request failed with status {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _score_weather_days(forecast):
    daily = forecast.get("daily") or {}
    days = []
    for index, date in enumerate(daily.get("time", [])):
        code = int(daily["weather_code"][index])
        rain_probability = int(daily["precipitation_probability_max"][index] or 0)
        rain_amount = float(daily["precipitation_sum"][index] or 0)
        wind = float(daily["wind_speed_10m_max"][index] or 0)
        hazards = []
        score = 0
        description = WEATHER_CODES.get(code, "changing weather")
        if code >= 95:
            hazards.append("thunderstorm")
            score += 5
        elif code >= 80 or rain_amount >= 30 or rain_probability >= 80:
            hazards.append("heavy rain")
            score += 3
        elif code >= 51 or rain_probability >= 55:
            hazards.append("rain")
            score += 1
        if wind >= 60:
            hazards.append("damaging wind")
            score += 4
        elif wind >= 40:
            hazards.append("strong wind")
            score += 2
        if code in {71, 73, 75}:
            hazards.append("snow")
            score += 3
        level = "high" if score >= 5 else "moderate" if score >= 2 else "low"
        days.append({
            "date": date,
            "condition": description,
            "temperature_max": daily["temperature_2m_max"][index],
            "temperature_min": daily["temperature_2m_min"][index],
            "rain_probability": rain_probability,
            "precipitation_mm": rain_amount,
            "wind_kmh": wind,
            "hazards": hazards,
            "risk_score": score,
            "risk_level": level,
        })
    if not days:
        raise ValueError("weather provider returned no forecast days")
    return days


def _weather_headline(risk, hazards, peak):
    if hazards:
        return f"{risk.title()} weather risk: {', '.join(hazards)} expected around {peak['date']}."
    return "Low weather risk in the five-day planning window."


def _weather_reasoning(peak, days):
    return (
        f"The agent scored each of {len(days)} forecast days using precipitation, "
        f"wind, snow, and thunderstorm signals. The highest score was {peak['risk_score']} "
        f"on {peak['date']}, with {peak['condition']}, {peak['rain_probability']}% rain "
        f"probability, and maximum wind of {peak['wind_kmh']} km/h."
    )


def _weather_actions(hazards, risk):
    actions = ["Keep monitoring the forecast and confirm local emergency contacts."]
    if "heavy rain" in hazards or "rain" in hazards:
        actions.extend(["Clear drainage routes and avoid driving through floodwater.", "Prepare a flashlight, charged phone, and drinking water."])
    if "thunderstorm" in hazards or "damaging wind" in hazards:
        actions.extend(["Move loose outdoor objects indoors and shelter away from windows.", "Pause outdoor work and avoid exposed high ground."])
    if "snow" in hazards:
        actions.append("Prepare warm shelter, blankets, and a safe travel route.")
    if risk == "high":
        actions.append("Coordinate a readiness check with local responders before the peak day.")
    return list(dict.fromkeys(actions))