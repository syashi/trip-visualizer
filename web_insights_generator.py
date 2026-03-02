# Web-Based Dynamic Insights Generator
# Fetches real-time weather, travel tips, and destination info from the web

from datetime import datetime
from typing import Dict, List, Optional
import json

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

def get_month_name(month: int) -> str:
    """Convert month number to name."""
    months = ['', 'January', 'February', 'March', 'April', 'May', 'June',
              'July', 'August', 'September', 'October', 'November', 'December']
    return months[month] if 1 <= month <= 12 else ''

def generate_web_insights_prompt(trip_data: Dict) -> str:
    """
    Generate a prompt for AI to create destination insights.
    This prompt can be used with ChatGPT/Claude to get real-time insights.
    """

    if not trip_data or 'days' not in trip_data:
        return ""

    days = trip_data['days']

    # Extract unique locations and date range
    locations = []
    seen_locations = set()
    dates = []

    for day_key, day_data in sorted(days.items()):
        location = day_data.get('location', '')
        location_display = day_data.get('location_display', location.replace('_', ' ').title())

        if location and location not in seen_locations:
            locations.append(location_display)
            seen_locations.add(location)

        try:
            dates.append(datetime.strptime(day_key, '%Y-%m-%d'))
        except:
            pass

    if not locations or not dates:
        return ""

    start_date = min(dates)
    end_date = max(dates)
    trip_month = start_date.strftime('%B')
    trip_year = start_date.year

    # Build the prompt
    prompt = f"""Generate 10-15 travel insights for this trip:

**Trip Details:**
- Destinations: {', '.join(locations)}
- Travel Dates: {start_date.strftime('%B %d')} - {end_date.strftime('%B %d, %Y')}
- Month: {trip_month} {trip_year}

**Required Format (JSON):**
Return ONLY a JSON array with this exact structure:

[
  {{"icon": "🌤️", "text": "**Weather in Paris:** Mild spring weather, 10-18°C, pack layers and rain jacket"}},
  {{"icon": "🏛️", "text": "**Louvre Museum:** Book timed tickets online - walk-ins have 2+ hour waits"}},
  {{"icon": "💶", "text": "**Currency:** Euro (EUR) widely accepted, ATMs everywhere, 1-2% foreign transaction fee typical"}}
]

**Required Insights (include all):**

1. WEATHER (for each main destination):
   - Current weather patterns for {trip_month}
   - Temperature range in Celsius
   - Precipitation/conditions
   - What to pack

2. TRANSPORTATION:
   - Local transport (metro, buses, taxis)
   - Between cities (trains, flights)
   - Transport passes or cards
   - Typical costs

3. MONEY & COSTS:
   - Currency and exchange rates
   - Typical daily budget
   - Tipping customs
   - Payment methods (cash vs card)

4. TOP ATTRACTIONS:
   - Must-see landmarks
   - Booking requirements
   - Best times to visit
   - Skip-the-line tips

5. LOCAL TIPS:
   - Cultural norms or etiquette
   - Meal times and dining culture
   - Safety considerations
   - Best neighborhoods
   - Local specialties (food/drink)

6. PRACTICAL INFO:
   - Dress codes for attractions
   - Opening hours patterns
   - Language basics
   - SIM cards or WiFi

**Guidelines:**
- Be SPECIFIC and ACTIONABLE
- Include CURRENT {trip_year} information
- Use exact prices when possible
- Mention TIMINGS (opening hours, best visit times)
- Add BOOKING advice (advance purchase needed?)
- Include SAFETY tips if relevant
- Focus on INSIDER knowledge tourists wouldn't know
- Keep each insight to ONE sentence (max 2 sentences)

**Icons to use:**
🌤️ Weather | 🏛️ Attractions | 💶 Money | 🚇 Transport | 🍷 Food/Drink |
⚠️ Safety | 📱 Practical | 🎫 Tickets | ⏰ Timing | 💡 Tips

Output ONLY the JSON array, no explanations."""

    return prompt

def generate_web_insights_url(trip_data: Dict) -> str:
    """
    Generate a URL to a web service that can provide insights.
    Returns a ChatGPT URL with the prompt pre-filled.
    """
    prompt = generate_web_insights_prompt(trip_data)
    if not prompt:
        return ""

    # For now, return instructions for manual use
    # In the future, this could integrate with OpenAI API or Claude API
    return prompt

def generate_fallback_insights(trip_data: Dict) -> List[Dict]:
    """
    Generate basic fallback insights when web fetch is not available.
    Uses the static data as backup.
    """
    from insights_generator import generate_insights as generate_static_insights
    return generate_static_insights(trip_data)

def fetch_insights_from_web(trip_data: Dict, api_key: Optional[str] = None) -> List[Dict]:
    """
    Fetch insights from web APIs (OpenAI, weather APIs, etc.)
    Falls back to static data if APIs unavailable.

    Args:
        trip_data: The trip data dictionary
        api_key: Optional API key for OpenAI or other services

    Returns:
        List of insight dictionaries with 'icon' and 'text' keys
    """

    # If API key provided, use OpenAI API
    if api_key and REQUESTS_AVAILABLE:
        try:
            insights = fetch_from_openai(trip_data, api_key)
            if insights:
                return insights
        except Exception as e:
            print(f"OpenAI API error: {e}")

    # Fall back to static insights
    return generate_fallback_insights(trip_data)

def fetch_from_openai(trip_data: Dict, api_key: str) -> Optional[List[Dict]]:
    """
    Fetch insights using OpenAI API.
    Requires OPENAI_API_KEY environment variable or parameter.
    """
    if not REQUESTS_AVAILABLE:
        return None

    try:
        prompt = generate_web_insights_prompt(trip_data)

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': 'gpt-4o-mini',  # Fast and cost-effective
            'messages': [
                {'role': 'system', 'content': 'You are a travel expert providing accurate, up-to-date travel insights in JSON format.'},
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }

        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']

            # Parse JSON from response
            # Remove markdown code blocks if present
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()

            insights = json.loads(content)
            return insights

    except Exception as e:
        print(f"Error fetching from OpenAI: {e}")

    return None

def get_insights_instructions_text(trip_data: Dict) -> str:
    """
    Generate instructions for manually fetching insights.
    Returns formatted text to show in the UI.
    """

    prompt = generate_web_insights_prompt(trip_data)

    instructions = f"""
### 🌐 Get Real-Time Travel Insights

To get current weather, prices, and tips for your destinations:

**Option 1: Use ChatGPT/Claude (Recommended)**
1. Copy the prompt below
2. Paste into ChatGPT or Claude
3. Copy the JSON response
4. Click "Load Custom Insights" and paste the JSON

**Option 2: Enable OpenAI API**
Add your OpenAI API key to settings for automatic insights.

---

**Copy this prompt:**

```
{prompt}
```
"""

    return instructions
