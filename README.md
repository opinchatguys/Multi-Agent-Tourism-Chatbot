#  Multi-Agent Tourism Chatbot

A smart travel assistant powered by a multi-agent system that provides real-time weather information and tourist attractions for any destination worldwide.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Gradio](https://img.shields.io/badge/Gradio-Chat-orange.svg)](https://gradio.app/)
[![LangChain](https://img.shields.io/badge/LangChain-Orchestration-green.svg)](https://langchain.com/)

##  Features

-  **Intelligent Chatbot Interface** - Natural conversation flow with chat history
-  **Real-Time Weather Data** - Current temperature and precipitation probability via Open-Meteo API
-  **Tourist Attractions** - Top 5 attractions near any destination using OpenStreetMap data
-  **Smart Geocoding** - Converts place names to coordinates using Nominatim
-  **Parallel Processing** - Weather and places fetched simultaneously for faster responses
-  **Resilient Architecture** - Built-in retries, timeouts, and circuit breakers
-  **Free-Text Input** - Understands casual queries like "I'm going to Paris!" or "Weather in Tokyo"

##  Quick Start

### Prerequisites

- Python 3.10 or higher
- Valid email for API User-Agent headers

### Installation

1. Clone the repository:
```bash
git clone https://github.com/opinchatguys/multi-agent-tourism.git
cd multi-agent-tourism
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set environment variables:

**Windows (PowerShell):**
```powershell
$env:NOMINATIM_USER_AGENT = "multi-agent-tourism/0.1 (youremail@example.com)"
$env:OVERPASS_USER_AGENT = "multi-agent-tourism/0.1 (youremail@example.com)"
```

**Linux/Mac:**
```bash
export NOMINATIM_USER_AGENT="multi-agent-tourism/0.1 (youremail@example.com)"
export OVERPASS_USER_AGENT="multi-agent-tourism/0.1 (youremail@example.com)"
```

4. Run the chatbot:
```bash
python app.py
```

5. Open your browser at the URL shown (usually `http://127.0.0.1:7860`)

##  Usage Examples

Try these queries in the chatbot:

- "I'm going to Bangalore"
- "Weather in Paris"
- "What are the top places to visit in Tokyo?"
- "Tell me about London"
- "Things to do in New York"

##  Architecture

### Multi-Agent System

```
User Input → Parent Agent → Geocoding (Nominatim)
                          ↓
              ┌───────────┴───────────┐
              ↓                       ↓
         Weather Agent          Places Agent
       (Open-Meteo API)      (Overpass API)
              ↓                       ↓
              └───────────┬───────────┘
                          ↓
                   Compiled Response
```

### Key Components

- **`parent_tourism_agent`** - Main orchestrator that routes user queries
- **`parse_user_query`** - Intent detection and destination extraction
- **`get_coordinates`** - Geocoding via Nominatim API
- **`get_weather`** - Weather data from Open-Meteo with retry logic
- **`get_tourist_places`** - Attractions from Overpass API with circuit breaker

##  Technical Details

### APIs Used

- **Nominatim (OpenStreetMap)** - Free geocoding service
- **Open-Meteo** - Free weather forecast API (no key required)
- **Overpass API** - OpenStreetMap data for tourist attractions

### Resilience Features

-  Configurable timeouts (10-20s per API)
-  Retry with exponential backoff (3 attempts)
-  Circuit breaker pattern (30s cooldown after 3 failures)
-  Parallel execution for weather and places (ThreadPoolExecutor)

### Response Formatting

- Weather: Natural language summary (e.g., "24°C with a chance of 35% to rain")
- Places: Bullet-point list of top 5 attractions
- Error handling: User-friendly messages ("I don't think this place exists.")

## 📁 Project Structure

```
multi-agent-tourism/
├── app.py                  # Main application with Gradio chatbot
├── requirements.txt        # Python dependencies
├── project summary         # Project documentation
└── README.md              # This file
```

##  Deployment

### Hugging Face Spaces

Deploy for free at [Hugging Face Spaces](https://huggingface.co/spaces):

1. Create a new Space (Gradio SDK)
2. Upload `app.py` and `requirements.txt`
3. Set environment variables in Space settings:
   - `NOMINATIM_USER_AGENT`
   - `OVERPASS_USER_AGENT`
4. Wait for automatic build

### Other Options

- **Local:** Run `python app.py` for personal use
- **Render.com:** Free web service deployment
- **Railway.app:** GitHub-based deployment
- **Self-hosted:** Any VPS with Python 3.10+

##  Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NOMINATIM_USER_AGENT` | Contact info for Nominatim API | `multi-agent-tourism/0.1 (you@example.com)` |
| `OVERPASS_USER_AGENT` | Contact info for Overpass API | `multi-agent-tourism/0.1 (you@example.com)` |

**Note:** User-Agent must include a valid email per API usage policies.

##  License

This project is open source and available under the MIT License.

##  Contributing

Contributions are welcome! Feel free to:

- Report bugs
- Suggest new features
- Submit pull requests

##  Author

Built with ❤️ using LangChain, Gradio, and free public APIs.

##  Acknowledgments

- [Open-Meteo](https://open-meteo.com/) - Free weather API
- [OpenStreetMap](https://www.openstreetmap.org/) - Geocoding and places data
- [Gradio](https://gradio.app/) - Easy-to-use web UI framework
- [LangChain](https://langchain.com/) - Agent orchestration framework

---

**Live Demo:** [Try it on Hugging Face Spaces](https://huggingface.co/spaces/anwiwish/multi-agent-tourism)

