"""
Multi-Agent Tourism System

Project Summary
- Approach: Coordinator `parent_tourism_agent` interprets free-text via `parse_user_query`, then routes to live APIs: `get_coordinates` (Nominatim), `get_weather` (Open-Meteo), and `get_tourist_places` (Overpass). No LLM knowledge for facts.
- Key decisions: LangChain for orchestration, geocoding first as shared prerequisite, Gradio for a simple web UI, environment variables for configuration (User-Agent), no hardcoded secrets.
- Resilience: Child calls run in parallel (weather + places) with timeouts, lightweight retries/backoff, and a simple circuit breaker to handle transient API failures.
- Formatting: Natural-language weather summary and bullet-listed attractions, separated by blank lines.
- Challenges: Correct Overpass QL for tourism=attraction within 20km, Nominatim rate limits and User-Agent requirements, user-friendly error handling (“I don't think this place exists.”), and aligning precipitation probability to the current time slot.
- Workflow: user input → `parse_user_query` → `get_coordinates` → parallel `get_weather` & `get_tourist_places` → compile → Gradio UI output.
"""

import os
from typing import Optional, Tuple, List
import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor
import gradio as gr

CB_STATE = {
    'weather': {'failures': 0, 'opened_until': 0.0},
    'places': {'failures': 0, 'opened_until': 0.0},
}


def get_coordinates(city_name: str) -> Optional[Tuple[float, float]]:
    """
    Calls the Nominatim API to convert a place name to coordinates.
    Returns (lat, lon) or None if not found or on error.
    """
    user_agent = os.getenv("NOMINATIM_USER_AGENT", "multi-agent-tourism/0.1")
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": city_name,
        "format": "json",
        "limit": 1,
    }
    headers = {
        "User-Agent": user_agent,
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            return None
        first = data[0]
        lat_str = first.get("lat")
        lon_str = first.get("lon")
        if lat_str is None or lon_str is None:
            return None
        lat = float(lat_str)
        lon = float(lon_str)
        return (lat, lon)
    except (requests.RequestException, ValueError, TypeError):
        return None


def get_weather(lat: float, lon: float) -> Optional[str]:
    """
    Calls the Open-Meteo API to get current temperature and rain probability.
    Returns a user-friendly string like "24°C with a chance of 35% to rain".
    Implements simple retries with backoff and a circuit breaker.
    """
    now = time.time()
    cb = CB_STATE['weather']
    if now < cb['opened_until']:
        return None

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "hourly": "precipitation_probability",
        "forecast_days": 1,
        "timezone": "auto",
    }

    attempts = 3
    backoff = 0.7
    for i in range(attempts):
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})
            temp = current.get("temperature_2m")
            current_time = current.get("time")

            prob = None
            hourly = data.get("hourly", {})
            times = hourly.get("time") or []
            probs = hourly.get("precipitation_probability") or []
            if current_time and isinstance(times, list) and isinstance(probs, list) and len(times) == len(probs) and len(times) > 0:
                try:
                    idx = times.index(current_time) if current_time in times else 0
                    if 0 <= idx < len(probs):
                        prob = probs[idx]
                except (ValueError, TypeError):
                    pass

            if temp is None:
                return None

            temp_rounded = int(round(float(temp)))
            prob_val = None
            if prob is not None:
                try:
                    prob_val = int(round(float(prob)))
                except (ValueError, TypeError):
                    prob_val = None

            prob_str = f"{prob_val}%" if prob_val is not None else "N/A"
            # success: reset breaker state
            cb['failures'] = 0
            cb['opened_until'] = 0.0
            return f"{temp_rounded}°C with a chance of {prob_str} to rain"
        except requests.RequestException:
            # failure: increment and possibly open breaker
            cb['failures'] += 1
            if cb['failures'] >= 3:
                cb['opened_until'] = time.time() + 30.0
            if i < attempts - 1:
                time.sleep(backoff * (i + 1))
            else:
                return None


def get_tourist_places(lat: float, lon: float, limit: int = 5) -> List[str]:
    """
    Queries Overpass API for nodes with tourism=attraction within 20km.
    Returns up to `limit` place names (handles fewer results gracefully).
    Implements simple retries with backoff and a circuit breaker.
    """
    now = time.time()
    cb = CB_STATE['places']
    if now < cb['opened_until']:
        return []

    url = "https://overpass-api.de/api/interpreter"
    user_agent = os.getenv("OVERPASS_USER_AGENT", "multi-agent-tourism/0.1")
    headers = {"User-Agent": user_agent}
    query = f"""
    [out:json][timeout:25];
    node(around:20000,{lat},{lon})["tourism"="attraction"];
    out tags;
    """

    attempts = 3
    backoff = 0.7
    for i in range(attempts):
        try:
            resp = requests.post(url, data={"data": query}, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])
            names: List[str] = []
            seen = set()
            for el in elements:
                tags = el.get("tags", {})
                name = tags.get("name")
                if name and name not in seen:
                    names.append(name)
                    seen.add(name)
                if len(names) >= limit:
                    break
            # success: reset breaker state
            cb['failures'] = 0
            cb['opened_until'] = 0.0
            return names
        except (requests.RequestException, ValueError, TypeError):
            cb['failures'] += 1
            if cb['failures'] >= 3:
                cb['opened_until'] = time.time() + 30.0
            if i < attempts - 1:
                time.sleep(backoff * (i + 1))
            else:
                return []

    return []


def parse_user_query(user_input: str) -> Tuple[str, str]:
    """
    Infer intent (weather/places/both) and extract destination from free text.
    Handles punctuation like "Bangalore!" and phrases like "I'm going to bangalore".
    """
    text = user_input.strip()
    # Normalize punctuation to spaces and lowercase for intent detection
    norm = re.sub(r"[^A-Za-z\s\-]", " ", text).lower()
    # Intent heuristics
    weather_keywords = ["weather", "forecast", "temperature", "rain", "umbrella"]
    places_keywords = ["places", "attractions", "sights", "things to do", "poi", "tourist"]

    has_weather = any(k in norm for k in weather_keywords)
    has_places = any(k in norm for k in places_keywords)

    if has_weather and not has_places:
        intent = "weather"
    elif has_places and not has_weather:
        intent = "places"
    else:
        intent = "both"

    # Destination extraction patterns
    patterns = [
        r"going to\s+([a-z\-\s]+)",
        r"go to\s+([a-z\-\s]+)",
        r"travel to\s+([a-z\-\s]+)",
        r"visit\s+([a-z\-\s]+)",
        r"in\s+([a-z\-\s]+)",
        r"at\s+([a-z\-\s]+)",
        r"to\s+([a-z\-\s]+)",
    ]
    destination = None
    for pat in patterns:
        m = re.search(pat, norm)
        if m:
            destination = m.group(1)
            break
    if not destination:
        # Fallback: use original text minus punctuation
        destination = re.sub(r"[^A-Za-z\s\-]", " ", text).strip()
    # Collapse extra spaces and strip
    destination = re.sub(r"\s+", " ", destination).strip()
    return destination, intent


def parent_tourism_agent(user_input: str, intent: Optional[str] = None) -> str:
    """
    Core routing logic over free text with parallel child calls and resilience:
    - Parse intent and destination from user_input (overridable via intent arg).
    - Geocode destination; if missing, return the required friendly message.
    - Based on intent, call child helpers (parallel when both) and format final response.
    """
    dest_extracted, auto_intent = parse_user_query(user_input)
    dest = dest_extracted
    use_intent = (intent or auto_intent or "both").strip().lower()

    coords = get_coordinates(dest)
    if not coords:
        return "I don't think this place exists."

    lat, lon = coords

    weather_text: Optional[str] = None
    places: List[str] = []

    if use_intent == "weather":
        weather_text = get_weather(lat, lon)
    elif use_intent == "places":
        places = get_tourist_places(lat, lon)
    else:
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_weather = ex.submit(get_weather, lat, lon)
            f_places = ex.submit(get_tourist_places, lat, lon)
            try:
                weather_text = f_weather.result(timeout=15)
            except Exception:
                weather_text = None
            try:
                places = f_places.result(timeout=20)
            except Exception:
                places = []

    parts: List[str] = []
    if weather_text:
        parts.append(f"Weather in {dest}: {weather_text}.")
    if places:
        parts.append("Top attractions near " + dest + ":\n" + "\n".join(f"- {p}" for p in places))

    if not parts:
        return "Sorry, I couldn't retrieve weather or places right now."
    return "\n\n".join(parts)


def gradio_predict(user_input: str, history: List[List[str]]) -> str:
    """
    Chatbot interface: takes user message and chat history, returns bot response.
    """
    if not user_input or not user_input.strip():
        return "Please enter a destination or travel query."
    
    response = parent_tourism_agent(user_input)
    return response


def handle_user_input(destination: str) -> None:
    """
    Accepts a destination string and prints it.
    """
    print(f"Destination received: {destination}")


demo = gr.ChatInterface(
    fn=gradio_predict,
    title="Multi-Agent Tourism Chatbot",
    description="Ask me about any destination! I'll provide weather info and top attractions.",
    examples=[
        "I'm going to Bangalore",
        "Weather in Paris",
        "What are the top places to visit in Tokyo?",
        "Tell me about London"
    ],
)

if __name__ == "__main__":
    demo.launch()
