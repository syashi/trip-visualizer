"""
Trip Visualizer - Streamlit App
A beautiful visual itinerary generator from Gmail bookings
With Map Simulation and Illustrative Journey views
"""

import streamlit as st
import streamlit.components.v1 as components
import folium
from streamlit_folium import st_folium
import json
from datetime import datetime, timedelta
from icalendar import Calendar, Event
import io
import base64
import urllib.parse
from travel_extractor import TravelExtractor
from insights_generator import generate_insights, get_top_insights, get_remaining_insights
from web_insights_generator import generate_web_insights_prompt, get_insights_instructions_text

# Import PDF export functions
try:
    from export_pdf_functions import generate_full_journey_pdf, generate_day_by_day_pdf, SELENIUM_AVAILABLE, SELENIUM_ERROR
    PDF_EXPORT_AVAILABLE = True
except ImportError:
    PDF_EXPORT_AVAILABLE = False
    SELENIUM_AVAILABLE = False
    SELENIUM_ERROR = "PDF export not available"

# AI Formatting Function
def format_with_ai(messy_notes, api_key, api_provider="Hyperspace AI"):
    """Format messy trip notes using AI API (Hyperspace AI, OpenAI, or Anthropic)."""
    try:
        from openai import OpenAI
        import httpx

        # System prompt for formatting
        system_prompt = """You are a trip planning assistant. Convert travel itinerary information into structured text format for Trip Visualizer.

OUTPUT ONLY THE STRUCTURED TEXT - NO EXPLANATIONS OR EXTRA TEXT.

═══════════════════════════════════════════════════════════════════
CRITICAL RULE #1: SPLIT COMPLEX DAYS INTO MULTIPLE BOOKINGS
═══════════════════════════════════════════════════════════════════
When a day has MULTIPLE distinct activities (especially with different times/locations), create SEPARATE booking entries for each:
- Flights/arrivals → separate entry
- Meals at restaurants → separate Dining entries
- Tours/activities → separate Tour entries
- Hotel check-ins → separate Hotel entry
- Transportation changes → separate Transport entries

BAD (everything jammed into one entry):
DAY 1 - Apr 18, 2026 - Paris
10:25 AM | Tour | Paris Day | Paris | — | Confirmed
Notes: 🎂 Birthday. Land at CDG at 10:25. Take RER B + Line 1 to hotel (~12:30). Hotel near Gare de Lyon. Lunch at La Pause Verte (veg). Pick up bikes after lunch. 14:30 cycle Right Bank → Trocadéro (~8 km). See Eiffel Tower. Walk Champ de Mars. 19:30 birthday dinner at Les Ombres (Eiffel terrace)

GOOD (split into proper bookings):
DAY 1 - Apr 18, 2026 - Paris
10:25 AM | Flight | Arrive CDG Airport | Paris CDG Airport | — | Confirmed
Notes: 🎂 Birthday day! Take RER B + Line 1 to hotel (~12:30)
12:30 PM | Hotel | Check-in Gare de Lyon | Near Gare de Lyon, Paris | — | Confirmed
1:30 PM | Dining | Lunch at La Pause Verte | Paris | — | Confirmed
Notes: Vegetarian restaurant
2:30 PM | Tour | Bike Tour Right Bank | Trocadéro, Paris | — | Confirmed
Notes: ~8 km route. See Eiffel Tower, Walk Champ de Mars, Cross Pont d'Iéna
7:30 PM | Dining | Birthday Dinner at Les Ombres | Eiffel Tower terrace, Paris | — | Confirmed
Notes: ⭐ Special birthday dinner. Sister joins today 👯

═══════════════════════════════════════════════════════════════════
CRITICAL RULE #2: NOTES ARE FOR LOGISTICS, NOT ITINERARIES
═══════════════════════════════════════════════════════════════════
Notes should ONLY contain:
✅ Todo items with [ ] checkboxes
✅ @mentions (e.g., @Syashi Gupta)
✅ Reminders ("Remember to...", "Don't forget...")
✅ Important tips/warnings
✅ Booking links and confirmation numbers
✅ Brief context (vegetarian, special occasion, etc.)

Notes should NOT contain:
❌ Full activity descriptions (make separate bookings instead)
❌ Lists of things to see (put in activity name or brief note)
❌ Detailed timelines (create separate time-based bookings)
❌ Multiple unrelated activities jammed together

═══════════════════════════════════════════════════════════════════
REQUIRED FORMAT
═══════════════════════════════════════════════════════════════════

TRIP: [Trip Name]
DATES: [Month Day] - [Month Day, Year]

DAY [#] - [Month Day, Year] - [Location]
[Time] | [Type] | [Activity Name] | [Address/Location] | [Platform #Ref] | [Status]
Notes: [Brief logistics, todos, reminders only]

...more days...

KEY_INSIGHTS:
[{"icon": "emoji", "text": "insight text"}, ...]

═══════════════════════════════════════════════════════════════════
BOOKING TYPES (use the most specific one):
═══════════════════════════════════════════════════════════════════
- Flight: Air travel, airport arrivals/departures
- Hotel: Accommodation, check-in/check-out
- Tour: Guided tours, activities, bike tours, walking tours, sightseeing
- Dining: Restaurants, meals, cafes, food experiences
- Transport: Trains, buses, car rentals, ferries, taxis, transfers
- Spa: Wellness, spa treatments
- Ferry: Boat/ferry travel (also can use Transport)

STATUS: Confirmed, Pending, Optional, Cancelled
TIME FORMAT: 12-hour (e.g., "2:30 PM" or "9:00 AM - 12:00 PM")

═══════════════════════════════════════════════════════════════════
KEY_INSIGHTS SECTION (REQUIRED AT END)
═══════════════════════════════════════════════════════════════════
After all days, add a KEY_INSIGHTS section with a JSON array of insights about the trip.
Each insight has "icon" (single emoji) and "text" (brief insight).

Include 5-8 insights covering:
- 🎯 Trip theme/highlights (e.g., "Island hopping adventure", "Romantic getaway")
- 📸 Best photo opportunities at specific locations
- 🎂 Special occasions (birthdays, anniversaries, celebrations)
- 🌤️ Weather/season tips for the destination
- 💰 Budget tips (free attractions, money-saving suggestions)
- 🏛️ Cultural notes (local customs, dress codes, etiquette)
- 🎒 Packing suggestions (specific to activities planned)
- ⚡ Pro tips (best times to visit attractions, skip-the-line advice)

Example KEY_INSIGHTS:
KEY_INSIGHTS:
[{"icon": "🏝️", "text": "Hawaii island hopping adventure - experiencing Kauai's natural beauty"},
{"icon": "📸", "text": "Best sunrise shots at Waimea Canyon (arrive by 6am)"},
{"icon": "🌊", "text": "Snorkeling at Poipu Beach - sea turtles often spotted in mornings"},
{"icon": "🌧️", "text": "North shore gets more rain - pack a light rain jacket"},
{"icon": "🚗", "text": "Rent a Jeep for unpaved roads to hidden beaches"},
{"icon": "🍽️", "text": "Try poke bowls at local markets - fresher and cheaper than restaurants"},
{"icon": "🌺", "text": "Respect sacred Hawaiian sites - remove shoes when requested"}]

═══════════════════════════════════════════════════════════════════
EXTRACTION EXAMPLES
═══════════════════════════════════════════════════════════════════

INPUT: "Day 3: Morning train to Florence (9am), check into hotel, lunch at Trattoria Mario, afternoon Uffizi Gallery tour 3pm, dinner at Osteria dell'Enoteca 8pm. [ ] Book Uffizi tickets @Maria"

OUTPUT:
DAY 3 - [Date] - Florence
9:00 AM | Transport | Train to Florence | Train Station | — | Confirmed
12:00 PM | Hotel | Florence Hotel Check-in | Florence | — | Confirmed
1:00 PM | Dining | Lunch at Trattoria Mario | Florence | — | Confirmed
3:00 PM | Tour | Uffizi Gallery Tour | Florence | — | Pending
Notes: [ ] Book Uffizi tickets @Maria
8:00 PM | Dining | Dinner at Osteria dell'Enoteca | Florence | — | Confirmed

INPUT: "Arrive Tokyo 6pm, take Narita Express to Shinjuku. Remember to get JR Pass activated. Hotel is Park Hyatt. Dinner at nearby izakaya."

OUTPUT:
DAY [#] - [Date] - Tokyo
6:00 PM | Flight | Arrive Tokyo Narita | Tokyo Narita Airport | — | Confirmed
Notes: Remember to get JR Pass activated
7:00 PM | Transport | Narita Express to Shinjuku | Narita → Shinjuku | — | Confirmed
8:30 PM | Hotel | Park Hyatt Tokyo | Shinjuku, Tokyo | — | Confirmed
9:00 PM | Dining | Dinner at local izakaya | Near Park Hyatt, Shinjuku | — | Optional

KEY_INSIGHTS:
[{"icon": "🗾", "text": "Classic Tokyo experience - blend of ancient temples and modern tech"},
{"icon": "🚄", "text": "JR Pass essential - covers Narita Express and city trains"},
{"icon": "📸", "text": "Shibuya Crossing at night - iconic Tokyo photo spot"},
{"icon": "🍜", "text": "Izakayas offer best value - order multiple small dishes to share"},
{"icon": "🎌", "text": "Bow slightly when greeting - common courtesy in Japan"}]"""

        user_prompt = f"""Convert this messy travel information:\n\n{messy_notes}"""

        if api_provider == "Hyperspace AI":
            # Hyperspace AI uses OpenAI-compatible API with longer timeout
            http_client = httpx.Client(timeout=60.0)
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.hyperspace.ai/v1",
                http_client=http_client
            )
            response = client.chat.completions.create(
                model="gpt-4o",  # Hyperspace AI model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()

        elif api_provider == "OpenAI":
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            return response.choices[0].message.content.strip()

        elif api_provider == "Anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": system_prompt + "\n\n" + user_prompt}
                ]
            )
            return response.content[0].text.strip()

    except Exception as e:
        raise Exception(f"AI formatting failed: {str(e)}")

# Page config
st.set_page_config(
    page_title="Trip Visualizer - Smart Travel Itinerary Manager",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/YOUR_USERNAME/trip-visualizer',
        'Report a bug': 'https://github.com/YOUR_USERNAME/trip-visualizer/issues',
        'About': """
        ## Trip Visualizer 🗺️

        **Transform messy travel plans into beautiful interactive timelines**

        Paste any itinerary format and get:
        - 🗺️ Interactive maps with exact locations worldwide
        - 📅 Visual day-by-day timeline
        - ⚠️ Smart alerts for booking issues
        - 💡 AI-powered travel insights
        - 📄 PDF export with maps

        **Built for modern travelers. Free & Open Source.**

        Version 2.0 | MIT License
        """
    }
)

# Custom CSS - SF Pro + Modern Glassy Design
st.markdown("""
<style>
    /* ==================================================================
       SF PRO FONT + MODERN GLASSY DESIGN
       ================================================================== */

    /* SF Pro Font for text only (not icons or symbols) */
    body, p, div:not([class*="icon"]), li, a, button, input, textarea, select, label {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", sans-serif !important;
    }

    /* Thin, modern typography */
    body, p, div, li {
        font-weight: 300 !important;
    }

    /* Headings - elegant and thin (no size changes) */
    h1 { font-weight: 600 !important; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important; }
    h2 { font-weight: 500 !important; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important; }
    h3 { font-weight: 500 !important; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important; }
    h4 { font-weight: 400 !important; font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif !important; }
    h5, h6 { font-weight: 400 !important; }

    /* Modern gradient background */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #fafbfc 100%) !important;
    }

    /* Glassy cards with more rounded corners */
    [data-testid="stExpander"] {
        backdrop-filter: blur(20px) !important;
        background: rgba(255, 255, 255, 0.75) !important;
        border-radius: 24px !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.08) !important;
    }

    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.8) !important;
        border-radius: 20px !important;
        padding: 16px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04) !important;
        border: 1px solid rgba(0, 0, 0, 0.05) !important;
        backdrop-filter: blur(10px) !important;
    }

    /* Buttons - glassy and rounded */
    .stButton > button,
    button {
        border-radius: 16px !important;
        font-weight: 400 !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.3s ease !important;
    }

    /* Reduce gap between view toggle buttons - make them closer */
    [data-testid="column"]:has(button) {
        padding-left: 0.25rem !important;
        padding-right: 0.25rem !important;
    }

    /* Hide action required issue buttons - they're triggered by HTML cards */
    button[key^="action_req_issue_card_"] {
        display: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
        position: absolute !important;
        opacity: 0 !important;
    }

    /* Main background - match Figma */
    .stApp {
        background-color: #fbfbfb;
    }

    /* Fix text colors to be dark and visible in main content */
    [data-testid="stMain"] .stMarkdown,
    [data-testid="stMain"] .stMarkdown p,
    [data-testid="stMain"] .stMarkdown span,
    [data-testid="stMain"] .stMarkdown div,
    [data-testid="stMain"] p,
    [data-testid="stMain"] span,
    [data-testid="stMain"] div {
        color: #1d1d1f !important;
    }

    /* ========================================================================
       TRIP VISUALIZER COLOR THEME - UPDATED WITH BACKGROUNDS v2.2
       CACHE BUST: 2026-03-01-13:32
       ======================================================================== */

    /* Color Palette */
    /* Blue: #4A7C9E | Green: #6B9654 | Yellow: #E8C547 | Pink: #E8989B | Tan: #8B7B68 */
    /* Light Yellow BG: #FFF9E6 | Light Green BG: #F4F8F1 */

    /* Main trip title - Blue from palette */
    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2 {
        color: #4A7C9E !important;
        font-weight: 700 !important;
        font-size: 2rem !important;
        margin-bottom: 0.5rem !important;
    }

    /* Section headings - Green from palette with enhanced styling */
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4 {
        color: #6B9654 !important;
        font-size: 1.3rem !important;
        font-weight: 700 !important;
        margin-bottom: 1rem !important;
        margin-top: 1.5rem !important;
        padding-bottom: 0.5rem !important;
        border-bottom: 2px solid #E8C547 !important;
    }

    /* Subheadings and captions - Blue */
    [data-testid="stMain"] h5,
    [data-testid="stMain"] h6 {
        color: #4A7C9E !important;
    }

    /* Links and interactive text - Blue */
    [data-testid="stMain"] a {
        color: #4A7C9E !important;
    }

    /* Body text - Keep dark for readability (Lower specificity - comes after headings) */
    [data-testid="stMain"] p,
    [data-testid="stMain"] span:not(h1 span):not(h2 span):not(h3 span):not(h4 span),
    [data-testid="stMain"] div:not(.stMarkdown):not([data-testid]) {
        color: #2d2d2d !important;
    }

    /* Date/subtitle text - Tan for subtle contrast */
    [data-testid="stMain"] .trip-dates {
        color: #8B7B68 !important;  /* Darker tan for readability */
    }

    /* Warning/alert text - No border */
    [data-testid="stMain"] .stAlert,
    [data-testid="stMain"] [data-testid="stNotification"] {
        border-left: none !important;
    }

    /* Success elements - No border */
    [data-testid="stMain"] .stSuccess {
        border-left: none !important;
    }

    /* Info elements - No border */
    [data-testid="stMain"] .stInfo {
        border-left: none !important;
        border: none !important;
        background-color: #E8F4F8 !important;  /* Very light blue background */
        border-radius: 8px !important;
    }

    /* Text areas - make text visible with dark color */
    textarea,
    [data-baseweb="textarea"],
    .stTextArea textarea,
    textarea[aria-label*="Paste"] {
        color: #2d2d2d !important;
        font-weight: 400 !important;
        background-color: #ffffff !important;
    }

    /* Text area placeholder */
    textarea::placeholder {
        color: #999 !important;
        font-weight: 300 !important;
    }

    /* Text inputs */
    input[type="text"],
    input[type="email"],
    input[type="password"],
    .stTextInput input {
        color: #2d2d2d !important;
        font-weight: 400 !important;
    }

    /* Accent elements - Use yellow from palette */
    [data-testid="stMain"] .highlight,
    [data-testid="stMain"] mark {
        background-color: #E8C547 !important;
        color: #2d2d2d !important;
    }

    /* Ensure metric labels and values use palette colors */
    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        color: #1E88E5 !important;  /* Bright blue for labels */
        font-weight: 600 !important;
    }

    [data-testid="stMain"] [data-testid="stMetricValue"] {
        color: #4A7C9E !important;  /* Blue for values */
        font-weight: 700 !important;
    }

    /* Remove border from help icon (?) */
    .stTooltipIcon,
    [data-testid="stTooltipIcon"],
    button[data-testid="baseButton-header"] {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    /* Style primary buttons using blue from palette */
    button[kind="primary"],
    button[kind="primary"] *,
    button[kind="primary"] > div,
    button[kind="primary"] div,
    button[kind="primary"] p {
        background-color: #4A7C9E !important;  /* Blue background */
        color: white !important;
        font-weight: 600 !important;
        border: none !important;
        border-left: none !important;
        border-right: none !important;
        border-top: none !important;
        border-bottom: none !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* Exception: Journey day selector primary buttons get light yellow */
    button[kind="primary"][key*="select_day_"],
    button[kind="primary"][key*="select_day_"] *,
    button[kind="primary"][key*="select_day_"] > div,
    button[kind="primary"][key*="select_day_"] div,
    button[kind="primary"][key*="select_day_"] p {
        background-color: #FFF9E6 !important;  /* Light yellow for selected day */
        color: #1d1d1f !important;  /* Dark text */
        border: 2px solid #E8C547 !important;  /* Yellow border */
    }

    button[kind="primary"] {
        padding: 8px 16px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        font-size: 1rem !important;
        line-height: 1rem !important;
        box-sizing: border-box !important;
        width: auto !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        vertical-align: middle !important;
        border: none !important;
        outline: none !important;
    }

    button[kind="primary"] > div {
        padding: 0 !important;
        margin: 0 !important;
        height: 100% !important;
        display: flex !important;
        align-items: center !important;
    }

    button[kind="primary"]:hover,
    button[kind="primary"]:hover * {
        background-color: #3a6480 !important;  /* Darker blue on hover */
        color: white !important;
    }

    /* Light Yellow Card Backgrounds for Expanders Only */
    [data-testid="stExpander"] {
        background-color: #FFF9E6 !important;  /* Very light yellow */
        border-radius: 12px !important;
        border: 1px solid #E8C547 !important;  /* Yellow border */
    }

    /* Individual metric styling with subtle border */
    [data-testid="stMetric"] {
        background-color: white !important;
        border-radius: 8px !important;
        padding: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
        border: 1px solid #E8E8E8 !important;
    }

    /* Expander header styling */
    [data-testid="stExpander"] summary {
        background-color: #FFF9E6 !important;
        font-weight: 600 !important;
        color: #4A7C9E !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }

    /* Expander content area */
    [data-testid="stExpander"] > div > div {
        background-color: white !important;
        border-radius: 8px !important;
        padding: 16px !important;
        margin-top: 8px !important;
    }

    /* Style secondary buttons - FIX ALL INTERNAL ELEMENTS */
    button[kind="secondary"],
    button[kind="secondary"] *,
    button[kind="secondary"] > div,
    button[kind="secondary"] div,
    button[kind="secondary"] p {
        background-color: white !important;
        color: #333 !important;
        font-weight: 600 !important;
        border: none !important;
        border-left: none !important;
        border-right: none !important;
        border-top: none !important;
        border-bottom: none !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* Fix visibility for Get Real-Time Insights button specifically */
    button[key="get_web_insights_btn"],
    button[key="get_web_insights_btn"] *,
    button[key="get_web_insights_btn"] p {
        color: #1d1d1f !important;
    }

    button[kind="secondary"] {
        padding: 8px 16px !important;
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        font-size: 1rem !important;
        line-height: 1rem !important;
        box-sizing: border-box !important;
        width: auto !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        vertical-align: middle !important;
        border: none !important;
        outline: none !important;
    }

    button[kind="secondary"] > div {
        padding: 0 !important;
        margin: 0 !important;
        height: 100% !important;
        display: flex !important;
        align-items: center !important;
    }

    button[kind="secondary"]:hover,
    button[kind="secondary"]:hover * {
        background-color: #f8f9fa !important;
        color: #1d1d1f !important;
    }

    /* Override any Streamlit default padding/margin differences */
    /* CRITICAL FIX: Force exact same height for primary and secondary buttons */
    [data-testid="stMain"] button[kind="primary"],
    [data-testid="stMain"] button[kind="secondary"] {
        height: 42px !important;
        min-height: 42px !important;
        max-height: 42px !important;
        padding: 0 16px !important;
        margin: 0 !important;
        box-sizing: border-box !important;
        line-height: 1 !important;
    }

    [data-testid="stMain"] button[kind="primary"] > div,
    [data-testid="stMain"] button[kind="secondary"] > div,
    [data-testid="stMain"] button[kind="primary"] div[data-testid="stMarkdownContainer"],
    [data-testid="stMain"] button[kind="secondary"] div[data-testid="stMarkdownContainer"] {
        height: 42px !important;
        line-height: 42px !important;
        padding: 0 !important;
        margin: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    [data-testid="stMain"] button[kind="primary"] p,
    [data-testid="stMain"] button[kind="secondary"] p {
        margin: 0 !important;
        padding: 0 !important;
        line-height: 1 !important;
    }

    button[kind="primary"],
    button[kind="secondary"] {
        margin: 0 !important;
    }

    /* Ensure dialog buttons are visible and styled correctly */
    button[key*="_btn"] div,
    button[key*="_btn"] p,
    button[key*="_btn"] span {
        display: inline !important;
        visibility: visible !important;
    }

    /* Remove all borders from input boxes */
    input[type="text"],
    input[type="date"],
    input[type="number"],
    textarea,
    [data-testid="stTextInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTextArea"] textarea {
        border: none !important;
        border-radius: 4px !important;
        background-color: #f8f9fa !important;
        color: #1d1d1f !important;
    }

    input[type="text"]:focus,
    input[type="date"]:focus,
    input[type="number"]:focus,
    textarea:focus {
        border: none !important;
        outline: none !important;
        background-color: #e8eaed !important;
        color: #1d1d1f !important;
    }

    /* Ensure text in paste itinerary textarea is black and visible */
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-testid="stTextArea"] textarea {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    [data-testid="stSidebar"] textarea::placeholder {
        color: #666666 !important;
    }

    /* Make all day selector buttons the same width - set to accommodate longest text */
    button[key*="select_day_"],
    button[key*="select_day_"]:hover,
    button[key*="select_day_"]:focus,
    button[key*="select_day_"]:active {
        width: 100% !important;
        min-width: 100% !important;
        max-width: 100% !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        display: flex !important;
        border-radius: 8px !important;
        padding: 10px 12px !important;
        margin-bottom: 8px !important;
        text-align: left !important;
        color: #1d1d1f !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        height: auto !important;
        min-height: 60px !important;
        justify-content: flex-start !important;
        align-items: center !important;
    }

    /* Selected day styling - Light yellow background */
    button[key*="select_day_"][key*="selected-day"],
    button[key*="select_day_"][key*="selected-day"]:hover,
    button[key*="select_day_"][key*="selected-day"]:focus,
    button[key*="select_day_"][key*="selected-day"]:active {
        background: #FFF9E6 !important;  /* Very light yellow */
        background-color: #FFF9E6 !important;
        border: 2px solid #E8C547 !important;  /* Yellow border */
        box-shadow: 0 2px 8px rgba(232, 197, 71, 0.2) !important;
    }

    button[key*="select_day_"][key*="selected-day"] *,
    button[key*="select_day_"][key*="selected-day"] p,
    button[key*="select_day_"][key*="selected-day"] div {
        background: transparent !important;
        background-color: transparent !important;
    }

    /* Unselected day styling */
    button[key*="select_day_"][key*="unselected-day"],
    button[key*="select_day_"][key*="unselected-day"]:hover {
        background: white !important;
        background-color: white !important;
        border: 2px solid #e0e0e0 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }

    /* Style issue card buttons to look like cards - FULL WIDTH LEFT ALIGNED */
    button[key*="issue_card_"] {
        background: white !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        margin: 0 0 6px 0 !important;
        text-align: left !important;
        font-size: 13px !important;
        white-space: normal !important;
        overflow: visible !important;
        height: auto !important;
        line-height: 1.4 !important;
        width: 100% !important;
        max-width: 100% !important;
        min-width: 100% !important;
        display: block !important;
    }

    button[key*="issue_card_"] > div {
        text-align: left !important;
        justify-content: flex-start !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    button[key*="issue_card_"] p,
    button[key*="issue_card_"] div[data-testid="stMarkdownContainer"] {
        text-align: left !important;
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    button[key*="issue_card_"]:hover {
        background: #f8f9fa !important;
        box-shadow: 0 2px 6px rgba(250, 82, 82, 0.15) !important;
    }

    /* Force left alignment for issue card button content */
    button[key*="issue_card_"] * {
        text-align: left !important;
        justify-content: flex-start !important;
        white-space: normal !important;
        word-wrap: break-word !important;
    }

    /* Force issue card button wrapper to full width */
    button[key*="issue_card_"] > div {
        width: 100% !important;
        text-align: left !important;
        justify-content: flex-start !important;
    }

    /* Force the parent container of issue cards to be left-aligned */
    div:has(> button[key*="issue_card_"]) {
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
        width: 100% !important;
    }

    /* Ensure issue card buttons don't get centered */
    [data-testid="column"]:has(button[key*="issue_card_"]) {
        align-items: stretch !important;
    }

    [data-testid="stVerticalBlock"]:has(button[key*="issue_card_"]) {
        align-items: stretch !important;
        display: flex !important;
        flex-direction: column !important;
    }

    /* Force button container divs to stretch */
    div[data-testid="stVerticalBlock"] > div:has(button[key*="issue_card_"]) {
        width: 100% !important;
        display: flex !important;
    }

    /* ISSUE CARDS - Remove ALL padding from parent containers */
    /* Target the stElementToolbar and all wrapper divs */
    div[data-testid="stElementToolbar"]:has(button[key*="issue_card_"]),
    div[data-testid="stElementToolbarContent"]:has(button[key*="issue_card_"]),
    div.stElementToolbar:has(button[key*="issue_card_"]),
    div:has(> button[key*="issue_card_"]),
    div:has(> div > button[key*="issue_card_"]) {
        padding: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin: 0 !important;
        margin-left: 0 !important;
        width: 100% !important;
    }

    /* Target ALL ancestor containers of issue cards up to the column */
    [data-testid="column"]:has(button[key*="issue_card_"]) > div,
    [data-testid="column"]:has(button[key*="issue_card_"]) > div > div,
    [data-testid="column"]:has(button[key*="issue_card_"]) [data-testid="stVerticalBlock"],
    [data-testid="column"]:has(button[key*="issue_card_"]) [data-testid="stVerticalBlock"] > div {
        padding-left: 0 !important;
        margin-left: 0 !important;
    }

    /* Force issue card button itself to be flush left */
    button[key*="issue_card_"] {
        margin-left: 0 !important;
        padding-left: 12px !important;
    }

    /* Remove any gap from button containers */
    [data-testid="stVerticalBlock"]:has(button[key*="issue_card_"]) {
        gap: 0 !important;
    }

    /* Hide all horizontal rules */
    hr,
    [data-testid="stMarkdownContainer"]:has(hr) {
        display: none !important;
    }

    /* Fix dialog/modal buttons - target by kind attribute and key */
    button[kind="secondary"][key="cancel_export_btn"],
    button[kind="primary"][key="generate_pdf_btn"],
    button[key="download_pdf_btn"],
    div[data-testid="stVerticalBlock"] button[key="cancel_export_btn"],
    div[data-testid="stVerticalBlock"] button[key="generate_pdf_btn"],
    div[data-testid="stVerticalBlock"] button[key="download_pdf_btn"],
    button[key="cancel_export_btn"],
    button[key="generate_pdf_btn"],
    button[key="download_pdf_btn"] {
        width: 220px !important;
        min-width: 220px !important;
        max-width: 220px !important;
        white-space: nowrap !important;
    }

    /* Ensure button inner elements also respect width */
    button[key="cancel_export_btn"] div,
    button[key="generate_pdf_btn"] div,
    button[key="download_pdf_btn"] div,
    button[key="cancel_export_btn"] span,
    button[key="generate_pdf_btn"] span,
    button[key="download_pdf_btn"] span,
    button[key="cancel_export_btn"] p,
    button[key="generate_pdf_btn"] p,
    button[key="download_pdf_btn"] p {
        white-space: nowrap !important;
        overflow: visible !important;
    }

    /* Ensure the button wrapper is also full width */
    button[key*="select_day_"] > div,
    button[key*="select_day_"] > div > div {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* Force the container column to stretch to full width */
    div:has(> button[key*="select_day_"]) {
        width: 100% !important;
        max-width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
    }

    [data-testid="stVerticalBlock"]:has(button[key*="select_day_"]) {
        width: 100% !important;
        max-width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: stretch !important;
    }

    /* REMOVE ALL VERTICAL LINES FROM ENTIRE APP - AGGRESSIVE */
    * {
        border-left: none !important;
        border-right: none !important;
    }

    /* Only allow specific elements to have borders */
    [data-testid="stExpander"],
    .booking-item,
    .day-card,
    button,
    input,
    textarea,
    select {
        border: revert !important;
    }

    /* But still remove left/right borders from columns and blocks */
    [data-testid="column"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stVerticalBlock"],
    div[data-testid="column"],
    div[class*="col"],
    .row-widget.stHorizontalBlock > div {
        border: none !important;
        border-left: none !important;
        border-right: none !important;
    }

    /* Remove borders from all button parent containers */
    button[kind="primary"]::before,
    button[kind="primary"]::after,
    button[kind="secondary"]::before,
    button[kind="secondary"]::after,
    button::before,
    button::after {
        display: none !important;
    }

    /* Fix expander/accordion styling - IMPORTANT FOR VISIBILITY */
    /* Target all possible selectors with high specificity */
    .streamlit-expanderHeader,
    div[data-testid="stExpander"] > details > summary,
    div[data-testid="stExpander"] > details > summary:not([open]) {
        background-color: #e8e8ed !important;  /* Light gray background when collapsed */
        border: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 17px !important;
        color: #1d1d1f !important;  /* Dark text for contrast */
        font-weight: 500 !important;
        padding: 16px !important;
        box-shadow: 0px 1px 3px 0px rgba(0,0,0,0.15), 0px 1px 2px -1px rgba(0,0,0,0.1) !important;
    }

    .streamlit-expanderHeader:hover,
    div[data-testid="stExpander"] > details > summary:hover {
        background-color: #d2d2d7 !important;
    }

    /* When expanded, make it white with dark text - higher specificity */
    details[open] > .streamlit-expanderHeader,
    div[data-testid="stExpander"] > details[open] > summary,
    details[open] > summary.streamlit-expanderHeader {
        background-color: white !important;
        color: #1d1d1f !important;  /* Dark text when expanded */
        border-bottom: none !important;
        border-radius: 17px 17px 0 0 !important;
    }

    /* Override any inline styles */
    [data-testid="stExpander"] summary {
        background-color: #e8e8ed !important;
        color: #1d1d1f !important;
    }

    [data-testid="stExpander"][open] summary {
        background-color: white !important;
        color: #1d1d1f !important;
    }

    .streamlit-expanderContent {
        background-color: white !important;
        border: 1px solid rgba(0,0,0,0.06) !important;
        border-top: none !important;
        border-radius: 0 0 17px 17px !important;
        padding: 16px !important;
    }

    /* ========== DAY ACTION BUTTONS STYLES ========== */
    /* Style the edit and add day buttons */
    button[key*="edit_day_"],
    button[key*="add_booking_"] {
        background: white !important;
        border: 1px solid rgba(0,0,0,0.15) !important;
        border-radius: 8px !important;
        width: 36px !important;
        height: 36px !important;
        min-width: 36px !important;
        max-width: 36px !important;
        min-height: 36px !important;
        max-height: 36px !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 16px !important;
        cursor: pointer !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
    }

    button[key*="edit_day_"]:hover,
    button[key*="add_booking_"]:hover {
        background: #f0f0f0 !important;
        border-color: rgba(0,0,0,0.25) !important;
    }

    /* ========== END DAY ACTION BUTTONS STYLES ========== */

    /* Main container */
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1d1d1f;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-top: 0;
    }

    /* Stat cards */
    .stat-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin: 5px;
    }
    .stat-number {
        font-size: 2.2rem;
        font-weight: 700;
        color: #4A90A4;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Day cards */
    .day-card {
        background: white;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border-left: 5px solid #4A90A4;
    }
    .day-header {
        display: flex;
        align-items: center;
        margin-bottom: 16px;
    }
    .day-badge {
        background: linear-gradient(135deg, #4A90A4 0%, #357ABD 100%);
        color: white;
        border-radius: 12px;
        padding: 8px 16px;
        font-weight: 700;
        font-size: 0.9rem;
        margin-right: 12px;
    }
    .day-location {
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
    }
    .day-date {
        font-size: 0.9rem;
        color: #666;
        margin-left: auto;
    }

    /* Booking items */
    .booking-item {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        border-left: 4px solid #e0e0e0;
    }
    .booking-item.flight { border-left-color: #FF6B6B; }
    .booking-item.hotel { border-left-color: #4ECDC4; }
    .booking-item.tour { border-left-color: #FFE66D; }
    .booking-item.transport { border-left-color: #95E1D3; }
    .booking-item.dining { border-left-color: #F38181; }

    .booking-type {
        font-size: 0.75rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .booking-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 8px;
    }
    .booking-detail {
        font-size: 0.85rem;
        color: #666;
        margin: 4px 0;
    }
    .booking-ref {
        background: #e8f4f8;
        color: #4A90A4;
        padding: 4px 10px;
        border-radius: 6px;
        font-family: monospace;
        font-size: 0.85rem;
        display: inline-block;
    }

    /* Illustrative journey */
    .journey-container {
        display: flex;
        flex-direction: column;
        gap: 0;
    }
    .journey-stop {
        display: flex;
        align-items: flex-start;
        position: relative;
    }
    .journey-line {
        width: 4px;
        background: linear-gradient(180deg, #4A90A4 0%, #357ABD 100%);
        position: absolute;
        left: 23px;
        top: 50px;
        bottom: -20px;
    }
    .journey-dot {
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, #4A90A4 0%, #357ABD 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1.2rem;
        z-index: 1;
        flex-shrink: 0;
        box-shadow: 0 4px 15px rgba(74, 144, 164, 0.4);
    }
    .journey-content {
        margin-left: 20px;
        flex: 1;
        padding-bottom: 40px;
    }
    .journey-location {
        font-size: 1.5rem;
        font-weight: 700;
        color: #333;
        margin-bottom: 4px;
    }
    .journey-date {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 12px;
    }
    .journey-activities {
        background: white;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }

    /* View toggle */
    .view-toggle {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 4px;
        display: inline-flex;
        margin-bottom: 20px;
    }
    .toggle-btn {
        padding: 8px 20px;
        border-radius: 8px;
        border: none;
        background: transparent;
        cursor: pointer;
        font-weight: 500;
        transition: all 0.2s;
    }
    .toggle-btn.active {
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* Alert */
    .alert-warning {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 16px;
        border-radius: 8px;
        margin: 16px 0;
    }

    /* Key Insights Section */
    .insights-card {
        background: white;
        border: 1px solid rgba(0,0,0,0.06);
        border-radius: 17px;
        padding: 20px;
        margin: 20px 0;
        box-shadow: 0px 1px 3px 0px rgba(0,0,0,0.1), 0px 1px 2px -1px rgba(0,0,0,0.1);
    }
    .insights-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
    }
    .insights-title {
        font-size: 20px;
        font-weight: 600;
        color: #1d1d1f;
        letter-spacing: -0.95px;
    }
    .insight-item {
        display: flex;
        align-items: flex-start;
        gap: 12px;
        margin-bottom: 16px;
    }
    .insight-icon {
        font-size: 18px;
        margin-top: 2px;
        flex-shrink: 0;
    }
    .insight-text {
        font-size: 15px;
        color: #1d1d1f;
        letter-spacing: -0.23px;
        line-height: 21px;
    }
    .insight-subtext {
        font-size: 15px;
        color: #86868b;
        letter-spacing: -0.23px;
        line-height: 21px;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Fix sidebar text visibility */
    [data-testid="stSidebar"] {
        background-color: #1e1e1e;
    }

    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    [data-testid="stSidebar"] .stMarkdown,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
    }

    /* Ensure main content buttons and text are dark/visible */
    [data-testid="stMain"] button {
        color: #1d1d1f !important;
        border: none !important;
        outline: none !important;
    }

    [data-testid="stMain"] .stButton button {
        color: #1d1d1f !important;
        white-space: nowrap !important;
        min-width: fit-content !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* Remove focus outline from all buttons */
    [data-testid="stMain"] button:focus,
    [data-testid="stMain"] button:focus-visible {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    [data-testid="stMain"] .stDownloadButton button {
        color: #1d1d1f !important;
        white-space: nowrap !important;
        min-width: fit-content !important;
        padding: 0.5rem 1rem !important;
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* Remove borders from download button on focus */
    [data-testid="stMain"] .stDownloadButton button:focus,
    [data-testid="stMain"] .stDownloadButton button:focus-visible {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* Fix primary buttons to have white text */
    button[kind="primary"],
    button[data-testid="baseButton-primary"] {
        color: white !important;
        white-space: nowrap !important;
        min-width: fit-content !important;
        padding: 0.5rem 1rem !important;
    }

    /* Style icon-only buttons to contain icons properly - minimum 150px width */
    button[kind="secondary"] {
        background: white !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 8px !important;
        padding: 6px 10px !important;
        min-height: 36px !important;
        height: auto !important;
        min-width: 150px !important;
        width: auto !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: visible !important;
        white-space: nowrap !important;
    }

    button[kind="secondary"]:hover {
        background: #f5f5f5 !important;
        border-color: rgba(0,0,0,0.2) !important;
    }

    /* Fix button text to be centered and contained */
    button[kind="secondary"] p {
        font-size: 16px !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    button[kind="secondary"] div[data-testid="stMarkdownContainer"] {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    /* OVERRIDE: Export dialog buttons should be 150px wide - MAXIMUM SPECIFICITY */
    button[kind="secondary"][key="cancel_export_btn"][data-testid="stBaseButton-secondary"] {
        width: 150px !important;
        min-width: 150px !important;
        max-width: 150px !important;
        height: auto !important;
        min-height: 40px !important;
        padding: 8px 16px !important;
    }

    button[kind="primary"][key="generate_pdf_btn"][data-testid="stBaseButton-primary"] {
        width: 150px !important;
        min-width: 150px !important;
        max-width: 150px !important;
        height: auto !important;
        min-height: 40px !important;
        padding: 8px 16px !important;
    }

    button[key="download_pdf_btn"] {
        width: 150px !important;
        min-width: 150px !important;
        max-width: 150px !important;
        height: auto !important;
        min-height: 40px !important;
        padding: 8px 16px !important;
    }

    /* Multiple selectors for extra coverage */
    button.st-emotion-cache-1anq8dj[key="cancel_export_btn"],
    button[key="cancel_export_btn"],
    button[aria-label=""][key="cancel_export_btn"] {
        width: 150px !important;
        min-width: 150px !important;
        max-width: 150px !important;
    }

    button[key="generate_pdf_btn"],
    button[key="download_pdf_btn"] {
        width: 150px !important;
        min-width: 150px !important;
        max-width: 150px !important;
    }

    /* Align button columns to top */
    [data-testid="column"] {
        vertical-align: top !important;
    }

    /* Fix Streamlit's markdown container that adds dark background to HTML */
    [data-testid="stMarkdownContainer"] {
        background: transparent !important;
    }

    [data-testid="stMarkdownContainer"] > div {
        background: transparent !important;
    }

    /* Specifically fix the dark box covering booking cards */
    .element-container [data-testid="stMarkdownContainer"] > div:first-child {
        background: transparent !important;
    }

    /* Modal overlay styles */
    .modal-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: fadeIn 0.2s ease;
    }

    .modal-content {
        background: white;
        border-radius: 16px;
        padding: 24px;
        max-width: 600px;
        width: 90%;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        animation: slideUp 0.3s ease;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>
""", unsafe_allow_html=True)

# Location coordinates
LOCATION_COORDS = {
    # Hawaii (USA)
    'kauai': {'lat': 22.0964, 'lon': -159.5261, 'name': 'Kauai', 'country': 'Hawaii, USA', 'icon': '🏝️'},
    'oahu': {'lat': 21.4389, 'lon': -158.0001, 'name': 'Oahu', 'country': 'Hawaii, USA', 'icon': '🏝️'},
    'honolulu': {'lat': 21.3069, 'lon': -157.8583, 'name': 'Honolulu', 'country': 'Hawaii, USA', 'icon': '🌴'},
    'maui': {'lat': 20.7984, 'lon': -156.3319, 'name': 'Maui', 'country': 'Hawaii, USA', 'icon': '🏝️'},
    'big_island': {'lat': 19.5429, 'lon': -155.6659, 'name': 'Big Island', 'country': 'Hawaii, USA', 'icon': '🌋'},
    # Thailand
    'phuket': {'lat': 7.8804, 'lon': 98.3923, 'name': 'Phuket', 'country': 'Thailand', 'icon': '🏝️'},
    'krabi': {'lat': 8.0863, 'lon': 98.9063, 'name': 'Krabi', 'country': 'Thailand', 'icon': '🏖️'},
    'koh_samui': {'lat': 9.5120, 'lon': 100.0134, 'name': 'Koh Samui', 'country': 'Thailand', 'icon': '🌴'},
    'koh_phangan': {'lat': 9.7500, 'lon': 100.0667, 'name': 'Koh Phangan', 'country': 'Thailand', 'icon': '🎉'},
    'bangkok': {'lat': 13.7563, 'lon': 100.5018, 'name': 'Bangkok', 'country': 'Thailand', 'icon': '🏙️'},
    'phi_phi': {'lat': 7.7407, 'lon': 98.7784, 'name': 'Phi Phi Islands', 'country': 'Thailand', 'icon': '🏝️'},
    'hong_islands': {'lat': 8.0667, 'lon': 98.7167, 'name': 'Hong Islands', 'country': 'Thailand', 'icon': '🌊'},
    # Italy
    'rome': {'lat': 41.9028, 'lon': 12.4964, 'name': 'Rome', 'country': 'Italy', 'icon': '🏛️'},
    'florence': {'lat': 43.7696, 'lon': 11.2558, 'name': 'Florence', 'country': 'Italy', 'icon': '🎨'},
    'venice': {'lat': 45.4408, 'lon': 12.3155, 'name': 'Venice', 'country': 'Italy', 'icon': '🚣'},
    'milan': {'lat': 45.4642, 'lon': 9.1900, 'name': 'Milan', 'country': 'Italy', 'icon': '👗'},
    'naples': {'lat': 40.8518, 'lon': 14.2681, 'name': 'Naples', 'country': 'Italy', 'icon': '🍕'},
    'cinque_terre': {'lat': 44.1270, 'lon': 9.7100, 'name': 'Cinque Terre', 'country': 'Italy', 'icon': '🏘️'},
    'sicily': {'lat': 37.5999, 'lon': 14.0154, 'name': 'Sicily', 'country': 'Italy', 'icon': '🌋'},
    'bologna': {'lat': 44.4949, 'lon': 11.3426, 'name': 'Bologna', 'country': 'Italy', 'icon': '🍝'},
    'pisa': {'lat': 43.7228, 'lon': 10.4017, 'name': 'Pisa', 'country': 'Italy', 'icon': '🗼'},
    'lake_como': {'lat': 45.9930, 'lon': 9.2573, 'name': 'Lake Como', 'country': 'Italy', 'icon': '⛵'},
    'amalfi': {'lat': 40.6340, 'lon': 14.6027, 'name': 'Amalfi Coast', 'country': 'Italy', 'icon': '🌅'},
    # Europe
    'paris': {'lat': 48.8566, 'lon': 2.3522, 'name': 'Paris', 'country': 'France', 'icon': '🗼'},
    'versailles': {'lat': 48.8049, 'lon': 2.1204, 'name': 'Versailles', 'country': 'France', 'icon': '👑'},
    'lyon': {'lat': 45.7640, 'lon': 4.8357, 'name': 'Lyon', 'country': 'France', 'icon': '🍷'},
    'vienna': {'lat': 48.2082, 'lon': 16.3738, 'name': 'Vienna', 'country': 'Austria', 'icon': '🎻'},
    'salzburg': {'lat': 47.8095, 'lon': 13.0550, 'name': 'Salzburg', 'country': 'Austria', 'icon': '🎵'},
    'innsbruck': {'lat': 47.2692, 'lon': 11.4041, 'name': 'Innsbruck', 'country': 'Austria', 'icon': '⛷️'},
    'hallstatt': {'lat': 47.5622, 'lon': 13.6493, 'name': 'Hallstatt', 'country': 'Austria', 'icon': '🏔️'},
    'london': {'lat': 51.5074, 'lon': -0.1278, 'name': 'London', 'country': 'UK', 'icon': '🎡'},
    'barcelona': {'lat': 41.3851, 'lon': 2.1734, 'name': 'Barcelona', 'country': 'Spain', 'icon': '⛪'},
    'amsterdam': {'lat': 52.3676, 'lon': 4.9041, 'name': 'Amsterdam', 'country': 'Netherlands', 'icon': '🌷'},
    # Asia
    'tokyo': {'lat': 35.6762, 'lon': 139.6503, 'name': 'Tokyo', 'country': 'Japan', 'icon': '🗾'},
    'singapore': {'lat': 1.3521, 'lon': 103.8198, 'name': 'Singapore', 'country': 'Singapore', 'icon': '🦁'},
    'bali': {'lat': -8.3405, 'lon': 115.0920, 'name': 'Bali', 'country': 'Indonesia', 'icon': '🌺'},
    # Alaska (USA)
    'anchorage': {'lat': 61.2181, 'lon': -149.9003, 'name': 'Anchorage', 'country': 'Alaska, USA', 'icon': '🏔️'},
    'seward': {'lat': 60.1042, 'lon': -149.4422, 'name': 'Seward', 'country': 'Alaska, USA', 'icon': '🚢'},
    'wasilla': {'lat': 61.5814, 'lon': -149.4394, 'name': 'Wasilla', 'country': 'Alaska, USA', 'icon': '🏞️'},
    'glacier_view': {'lat': 61.7800, 'lon': -147.4500, 'name': 'Glacier View', 'country': 'Alaska, USA', 'icon': '🧊'},
    'healy': {'lat': 63.8614, 'lon': -148.9681, 'name': 'Healy', 'country': 'Alaska, USA', 'icon': '🏕️'},
    'chena_hot_springs': {'lat': 65.0539, 'lon': -146.0542, 'name': 'Chena Hot Springs', 'country': 'Alaska, USA', 'icon': '♨️'},
    'talkeetna': {'lat': 62.3203, 'lon': -150.1064, 'name': 'Talkeetna', 'country': 'Alaska, USA', 'icon': '✈️'},
    # California (USA)
    'mendocino': {'lat': 39.3077, 'lon': -123.7994, 'name': 'Mendocino', 'country': 'California, USA', 'icon': '🌊'},
    'albion': {'lat': 39.2241, 'lon': -123.7686, 'name': 'Albion', 'country': 'California, USA', 'icon': '🏖️'},
    'fort_bragg': {'lat': 39.4457, 'lon': -123.8053, 'name': 'Fort Bragg', 'country': 'California, USA', 'icon': '🚂'},
    'little_river': {'lat': 39.2691, 'lon': -123.7883, 'name': 'Little River', 'country': 'California, USA', 'icon': '🛶'},
    'sonoma': {'lat': 38.2919, 'lon': -122.4580, 'name': 'Sonoma', 'country': 'California, USA', 'icon': '�葡'},
    'san_francisco': {'lat': 37.7749, 'lon': -122.4194, 'name': 'San Francisco', 'country': 'California, USA', 'icon': '🌉'},
}

# Initialize session state
if 'trip_data' not in st.session_state:
    st.session_state.trip_data = None
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'map'
if 'location_cache' not in st.session_state:
    st.session_state.location_cache = {}


def geocode_location(location_name):
    """
    Smart location lookup using Nominatim geocoding API.
    Automatically finds coordinates for ANY city/location worldwide.
    Uses caching to avoid repeated API calls.
    """
    import re

    # Check cache first
    if location_name in st.session_state.location_cache:
        return st.session_state.location_cache[location_name]

    # Check if already in LOCATION_COORDS
    if location_name in LOCATION_COORDS:
        result = LOCATION_COORDS[location_name]
        st.session_state.location_cache[location_name] = result
        return result

    try:
        import requests
        import time

        # Clean up location name for better geocoding
        clean_name = location_name.replace('_', ' ').replace('/', ',').strip()

        # Remove parenthetical content like "(Arrival - Sunday)"
        clean_name = re.sub(r'\s*\([^)]*\)\s*', ' ', clean_name).strip()

        # Remove common suffixes like "- Day 1", "- Arrival", "- Sunday", etc.
        clean_name = re.sub(r'\s*[-–]\s*(Day\s*\d+|Arrival|Departure|Morning|Evening|Night|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday).*$', '', clean_name, flags=re.IGNORECASE).strip()

        # Skip empty or invalid location names
        if not clean_name or clean_name.lower() in ['home', '—', '-', 'n/a', '']:
            return None

        # Check if the cleaned name matches a known location in LOCATION_COORDS (exact match)
        clean_key = clean_name.lower().replace(' ', '_').replace(',', '')
        if clean_key in LOCATION_COORDS:
            result = LOCATION_COORDS[clean_key]
            st.session_state.location_cache[location_name] = result
            return result

        # Try partial matching - check if any known location is contained in the clean_name
        # This handles cases like "San Francisco Bay Area" -> "san_francisco"
        # or "Poipu / Princeville Resort" -> "kauai" (via poipu)
        clean_lower = clean_name.lower()

        # Location aliases for partial matching (same logic as text_parser.normalize_location)
        location_aliases = {
            # Hawaii
            'kauai': 'kauai', 'lihue': 'kauai', 'poipu': 'kauai', 'princeville': 'kauai', 'hanalei': 'kauai',
            'south shore': 'kauai', 'north shore kauai': 'kauai', 'waimea canyon': 'kauai',
            # Oahu
            'oahu': 'oahu', 'honolulu': 'honolulu', 'waikiki': 'honolulu',
            # Maui
            'maui': 'maui', 'lahaina': 'maui', 'kaanapali': 'maui', 'wailea': 'maui', 'hana': 'maui',
            # Big Island
            'big island': 'big_island', 'hawaii island': 'big_island', 'kona': 'big_island', 'hilo': 'big_island',
            # California
            'san francisco': 'san_francisco', 'sf': 'san_francisco', 'sfo': 'san_francisco',
            'los angeles': 'los_angeles', 'la': 'los_angeles', 'lax': 'los_angeles',
            'san diego': 'san_diego', 'mendocino': 'mendocino', 'sonoma': 'sonoma', 'napa': 'napa',
            'fort bragg': 'fort_bragg', 'little river': 'little_river', 'albion': 'albion',
            # Thailand
            'phuket': 'phuket', 'krabi': 'krabi', 'koh samui': 'koh_samui', 'samui': 'koh_samui',
            'bangkok': 'bangkok', 'phi phi': 'phi_phi', 'koh phangan': 'koh_phangan', 'chiang mai': 'chiang_mai',
            # Italy
            'rome': 'rome', 'florence': 'florence', 'venice': 'venice', 'milan': 'milan',
            'naples': 'naples', 'amalfi': 'amalfi', 'positano': 'amalfi', 'sicily': 'sicily',
            'cinque terre': 'cinque_terre', 'bologna': 'bologna', 'pisa': 'pisa', 'lake como': 'lake_como',
            # Europe
            'paris': 'paris', 'versailles': 'versailles', 'lyon': 'lyon',
            'vienna': 'vienna', 'salzburg': 'salzburg', 'innsbruck': 'innsbruck', 'hallstatt': 'hallstatt',
            'london': 'london', 'barcelona': 'barcelona', 'amsterdam': 'amsterdam',
            # Alaska
            'anchorage': 'anchorage', 'seward': 'seward', 'talkeetna': 'talkeetna', 'wasilla': 'wasilla',
            'healy': 'healy', 'fairbanks': 'fairbanks', 'juneau': 'juneau',
            # Asia
            'tokyo': 'tokyo', 'singapore': 'singapore', 'bali': 'bali',
        }

        # Check partial matches (longest match first to be more specific)
        for alias, coord_key in sorted(location_aliases.items(), key=lambda x: -len(x[0])):
            if alias in clean_lower and coord_key in LOCATION_COORDS:
                result = LOCATION_COORDS[coord_key]
                st.session_state.location_cache[location_name] = result
                return result

        # Try adding state/country hints for better geocoding accuracy
        search_queries = [clean_name]

        # If it looks like a US location (contains Hawaii-related terms), try appending hints
        hawaii_terms = ['kauai', 'oahu', 'maui', 'honolulu', 'hilo', 'kona', 'lahaina', 'lihue', 'poipu', 'princeville', 'hanalei', 'waimea', 'hawaii']
        if any(term in clean_lower for term in hawaii_terms):
            search_queries = [f"{clean_name}, Hawaii, USA", clean_name]

        for search_query in search_queries:
            # Use Nominatim API (OpenStreetMap) - free, no API key needed
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': search_query,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'TripVisualizer/1.0'
            }

            response = requests.get(url, params=params, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    result = data[0]
                    lat = float(result['lat'])
                    lon = float(result['lon'])

                    # Extract location details
                    address = result.get('address', {})
                    city = address.get('city') or address.get('town') or address.get('village') or address.get('island') or address.get('county') or clean_name.title()
                    country = address.get('country', 'Unknown')
                    state = address.get('state', '')

                    # Include state for US locations
                    if state and country == 'United States':
                        country = f"{state}, USA"

                    # Determine icon based on location type
                    location_type = result.get('type', '')
                    class_type = result.get('class', '')

                    if 'island' in location_type.lower() or 'island' in str(address).lower():
                        icon = '🏝️'
                    elif 'beach' in clean_name.lower():
                        icon = '🏖️'
                    elif 'mountain' in location_type.lower() or 'peak' in clean_name.lower():
                        icon = '🏔️'
                    elif 'airport' in class_type.lower():
                        icon = '✈️'
                    elif 'natural' in class_type.lower() or 'park' in clean_name.lower():
                        icon = '🏞️'
                    elif 'city' in location_type.lower() or 'town' in location_type.lower():
                        icon = '🏙️'
                    else:
                        icon = '📍'

                    location_data = {
                        'lat': lat,
                        'lon': lon,
                        'name': city,
                        'country': country,
                        'icon': icon
                    }

                    # Cache the result
                    st.session_state.location_cache[location_name] = location_data

                    # Add small delay to respect Nominatim usage policy
                    time.sleep(1)

                    return location_data

            # Add delay between retries
            time.sleep(0.5)

    except Exception as e:
        print(f"Geocoding failed for {location_name}: {e}")

    # Fallback: return None if geocoding fails
    return None


def create_map(locations_sequence):
    """Create an interactive map with route markers. Now supports ANY location via smart geocoding."""
    if not locations_sequence:
        m = folium.Map(location=[41.9, 12.5], zoom_start=5)
        return m

    coords = []
    for loc in locations_sequence:
        # Try smart geocoding for any location
        location_data = geocode_location(loc)
        if location_data:
            coords.append(location_data)

    if not coords:
        m = folium.Map(location=[41.9, 12.5], zoom_start=5)
        return m

    avg_lat = sum(c['lat'] for c in coords) / len(coords)
    avg_lon = sum(c['lon'] for c in coords) / len(coords)

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=6)

    # Add markers
    for i, coord in enumerate(coords, 1):
        icon_html = f'''
        <div style="
            background: linear-gradient(135deg, #4A90A4 0%, #357ABD 100%);
            color: white;
            border-radius: 50%;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 16px;
            border: 3px solid white;
            box-shadow: 0 3px 10px rgba(0,0,0,0.3);
        ">{i}</div>
        '''

        folium.Marker(
            [coord['lat'], coord['lon']],
            popup=f"<b>{i}. {coord['name']}</b><br>{coord.get('country', '')}",
            icon=folium.DivIcon(html=icon_html, icon_size=(36, 36), icon_anchor=(18, 18))
        ).add_to(m)

    # Route line
    if len(coords) > 1:
        route = [[c['lat'], c['lon']] for c in coords]
        folium.PolyLine(route, weight=3, color='#4A90A4', opacity=0.8, dash_array='10').add_to(m)

    return m


def parse_time_string(time_str):
    """Parse time string like '9:00 AM' or '14:30' into hour and minute integers."""
    if not time_str:
        return None, None

    time_str = time_str.strip().upper()

    # Try 12-hour format (9:00 AM, 2:30 PM)
    for fmt in ['%I:%M %p', '%I:%M%p', '%I %p', '%I%p']:
        try:
            parsed = datetime.strptime(time_str, fmt)
            return parsed.hour, parsed.minute
        except ValueError:
            continue

    # Try 24-hour format (14:30, 09:00)
    for fmt in ['%H:%M', '%H%M']:
        try:
            parsed = datetime.strptime(time_str, fmt)
            return parsed.hour, parsed.minute
        except ValueError:
            continue

    return None, None


def generate_ical_block_trip(trip_data):
    """Generate iCal file with a single event spanning the entire trip."""
    cal = Calendar()
    cal.add('prodid', '-//Trip Visualizer//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')

    trip_name = trip_data.get('trip_name', 'My Trip')
    start_date = trip_data.get('start_date', '')
    end_date = trip_data.get('end_date', '')

    try:
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, '%B %d, %Y')
        else:
            start_dt = start_date

        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, '%B %d, %Y')
        else:
            end_dt = end_date

        # Add one day to end for all-day event (exclusive end)
        end_dt = end_dt + timedelta(days=1)
    except Exception:
        return None

    # Build comprehensive description
    description_parts = [f"Trip: {trip_name}", ""]

    for day_key in sorted(trip_data.get('days', {}).keys()):
        day = trip_data['days'][day_key]
        day_num = day.get('day_num', '')
        location = day.get('location_display') or day.get('location', '')
        description_parts.append(f"Day {day_num} - {location}")

        for booking in day.get('bookings', []):
            activity = booking.get('activity_name', 'Activity')
            booking_type = booking.get('booking_type', booking.get('type', ''))
            time_info = booking.get('time_info', {})
            time_str = time_info.get('start_time', '')
            if time_str:
                description_parts.append(f"  {time_str}: {activity} ({booking_type})")
            else:
                description_parts.append(f"  - {activity} ({booking_type})")

            # Add booking reference if available
            ref = booking.get('booking_ref', '')
            if ref:
                description_parts.append(f"    Ref: {ref}")

        description_parts.append("")

    event = Event()
    event.add('summary', trip_name)
    event.add('dtstart', start_dt.date())
    event.add('dtend', end_dt.date())
    event.add('description', '\n'.join(description_parts))
    event.add('uid', f"{trip_name.replace(' ', '_')}_{start_dt.strftime('%Y%m%d')}@tripvisualizer")
    event.add('dtstamp', datetime.now())

    cal.add_component(event)

    return cal.to_ical()


def generate_ical_day_by_day(trip_data):
    """Generate iCal file with one event per day."""
    cal = Calendar()
    cal.add('prodid', '-//Trip Visualizer//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')

    trip_name = trip_data.get('trip_name', 'My Trip')

    for day_key in sorted(trip_data.get('days', {}).keys()):
        day = trip_data['days'][day_key]
        day_num = day.get('day_num', '')
        location = day.get('location_display') or day.get('location', '')

        # Parse day date
        day_date = day.get('date')
        if isinstance(day_date, str):
            try:
                day_date = datetime.strptime(day_date, '%Y-%m-%d')
            except ValueError:
                try:
                    day_date = datetime.fromisoformat(day_date.replace('Z', '+00:00'))
                except ValueError:
                    continue

        if not day_date:
            continue

        # Build description with all bookings for the day
        description_parts = [f"Day {day_num} of {trip_name}", f"Location: {location}", ""]

        for booking in day.get('bookings', []):
            activity = booking.get('activity_name', 'Activity')
            booking_type = booking.get('booking_type', booking.get('type', ''))
            time_info = booking.get('time_info', {})
            time_str = time_info.get('start_time', '')

            if time_str:
                description_parts.append(f"{time_str}: {activity} ({booking_type})")
            else:
                description_parts.append(f"- {activity} ({booking_type})")

            # Add location and booking reference
            loc_info = booking.get('location_info', {})
            meeting = loc_info.get('meeting_point') or loc_info.get('hotel', '')
            if meeting:
                description_parts.append(f"  Location: {meeting}")

            ref = booking.get('booking_ref', '')
            if ref:
                description_parts.append(f"  Ref: {ref}")

            description_parts.append("")

        event = Event()
        summary = f"{trip_name} - Day {day_num}: {location}" if location else f"{trip_name} - Day {day_num}"
        event.add('summary', summary)
        event.add('dtstart', day_date.date())
        event.add('dtend', (day_date + timedelta(days=1)).date())
        event.add('description', '\n'.join(description_parts))
        event.add('location', location)
        event.add('uid', f"{trip_name.replace(' ', '_')}_day{day_num}_{day_key}@tripvisualizer")
        event.add('dtstamp', datetime.now())

        cal.add_component(event)

    return cal.to_ical()


def generate_ical_individual_activities(trip_data):
    """Generate iCal file with separate timed events for each activity."""
    cal = Calendar()
    cal.add('prodid', '-//Trip Visualizer//EN')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')
    cal.add('method', 'PUBLISH')

    trip_name = trip_data.get('trip_name', 'My Trip')
    event_count = 0

    for day_key in sorted(trip_data.get('days', {}).keys()):
        day = trip_data['days'][day_key]
        day_num = day.get('day_num', '')
        location = day.get('location_display') or day.get('location', '')

        # Parse day date
        day_date = day.get('date')
        if isinstance(day_date, str):
            try:
                day_date = datetime.strptime(day_date, '%Y-%m-%d')
            except ValueError:
                try:
                    day_date = datetime.fromisoformat(day_date.replace('Z', '+00:00'))
                except ValueError:
                    continue

        if not day_date:
            continue

        for booking in day.get('bookings', []):
            event_count += 1
            activity = booking.get('activity_name', 'Activity')
            booking_type = booking.get('booking_type', booking.get('type', ''))
            time_info = booking.get('time_info', {})
            start_time_str = time_info.get('start_time', '')
            end_time_str = time_info.get('end_time', '')

            # Parse start and end times
            start_hour, start_min = parse_time_string(start_time_str)
            end_hour, end_min = parse_time_string(end_time_str)

            # Build description
            description_parts = [f"Part of: {trip_name}", f"Day {day_num}"]

            loc_info = booking.get('location_info', {})
            meeting = loc_info.get('meeting_point') or loc_info.get('hotel', '')
            if meeting:
                description_parts.append(f"Location: {meeting}")

            ref = booking.get('booking_ref', '')
            if ref:
                description_parts.append(f"Booking Ref: {ref}")

            status = booking.get('status', '')
            if status:
                description_parts.append(f"Status: {status}")

            notes = booking.get('notes', '')
            if notes:
                description_parts.append(f"\nNotes: {notes}")

            event = Event()
            summary = f"{activity} ({booking_type})" if booking_type else activity
            event.add('summary', summary)

            # Set start and end times
            if start_hour is not None:
                event_start = day_date.replace(hour=start_hour, minute=start_min or 0)
                event.add('dtstart', event_start)

                if end_hour is not None:
                    event_end = day_date.replace(hour=end_hour, minute=end_min or 0)
                    # Handle events that end the next day
                    if event_end <= event_start:
                        event_end = event_end + timedelta(days=1)
                    event.add('dtend', event_end)
                else:
                    # Default 1 hour duration if no end time
                    event.add('dtend', event_start + timedelta(hours=1))
            else:
                # All-day event if no time specified
                event.add('dtstart', day_date.date())
                event.add('dtend', (day_date + timedelta(days=1)).date())

            event.add('description', '\n'.join(description_parts))
            if meeting:
                event.add('location', meeting)
            elif location:
                event.add('location', location)
            event.add('uid', f"{trip_name.replace(' ', '_')}_event{event_count}_{day_key}@tripvisualizer")
            event.add('dtstamp', datetime.now())

            cal.add_component(event)

    return cal.to_ical()


def generate_ical(trip_data, mode='block'):
    """Generate iCal file from trip data with different modes.

    Args:
        trip_data: The trip data dictionary
        mode: 'block' (single event), 'day_by_day' (one per day), 'individual' (each activity)
    """
    if mode == 'block':
        return generate_ical_block_trip(trip_data)
    elif mode == 'day_by_day':
        return generate_ical_day_by_day(trip_data)
    elif mode == 'individual':
        return generate_ical_individual_activities(trip_data)
    else:
        return generate_ical_block_trip(trip_data)


def generate_google_calendar_link_block(trip_data):
    """Generate Google Calendar link for a single block event spanning the entire trip."""
    trip_name = trip_data.get('trip_name', 'My Trip')
    start_date = trip_data.get('start_date', '')
    end_date = trip_data.get('end_date', '')

    try:
        if isinstance(start_date, str):
            # Try multiple date formats
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d']:
                try:
                    start_dt = datetime.strptime(start_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format worked, return None
                return None
        else:
            start_dt = start_date

        if isinstance(end_date, str):
            # Try multiple date formats
            for fmt in ['%B %d, %Y', '%b %d, %Y', '%Y-%m-%d']:
                try:
                    end_dt = datetime.strptime(end_date, fmt)
                    break
                except ValueError:
                    continue
            else:
                # If no format worked, return None
                return None
        else:
            end_dt = end_date

        # Add one day to end date for Google Calendar (end date is exclusive)
        end_dt = end_dt + timedelta(days=1)

        start_str = start_dt.strftime('%Y%m%d')
        end_str = end_dt.strftime('%Y%m%d')
    except Exception:
        return None

    # Build description with all bookings
    description_parts = [f"Trip: {trip_name}", ""]
    for day_key in sorted(trip_data.get('days', {}).keys()):
        day = trip_data['days'][day_key]
        day_num = day.get('day_num', '')
        location = day.get('location_display') or day.get('location', '')
        description_parts.append(f"Day {day_num} - {location}")

        for booking in day.get('bookings', []):
            activity = booking.get('activity_name', 'Activity')
            booking_type = booking.get('booking_type', booking.get('type', ''))
            time_info = booking.get('time_info', {})
            time_str = time_info.get('start_time', '')
            if time_str:
                description_parts.append(f"  {time_str}: {activity} ({booking_type})")
            else:
                description_parts.append(f"  - {activity} ({booking_type})")

        description_parts.append("")

    description = '\n'.join(description_parts)

    # Google Calendar URL format
    base_url = "https://calendar.google.com/calendar/render"
    params = {
        'action': 'TEMPLATE',
        'text': trip_name,
        'dates': f"{start_str}/{end_str}",
        'details': description,
        'sf': 'true',
        'output': 'xml'
    }

    return f"{base_url}?{urllib.parse.urlencode(params)}"


def generate_google_calendar_links_day_by_day(trip_data):
    """Generate list of Google Calendar links, one for each day.
    Returns first day's link for the button, or list of all links.
    """
    trip_name = trip_data.get('trip_name', 'My Trip')
    links = []

    for day_key in sorted(trip_data.get('days', {}).keys()):
        day = trip_data['days'][day_key]
        day_num = day.get('day_num', '')
        location = day.get('location_display') or day.get('location', '')

        # Parse day date
        day_date = day.get('date')
        if isinstance(day_date, str):
            try:
                day_date = datetime.strptime(day_date, '%Y-%m-%d')
            except ValueError:
                try:
                    day_date = datetime.fromisoformat(day_date.replace('Z', '+00:00'))
                except ValueError:
                    continue

        if not day_date:
            continue

        start_str = day_date.strftime('%Y%m%d')
        end_str = (day_date + timedelta(days=1)).strftime('%Y%m%d')

        # Build description
        description_parts = [f"Day {day_num} of {trip_name}", f"Location: {location}", ""]
        for booking in day.get('bookings', []):
            activity = booking.get('activity_name', 'Activity')
            booking_type = booking.get('booking_type', booking.get('type', ''))
            time_info = booking.get('time_info', {})
            time_str = time_info.get('start_time', '')
            if time_str:
                description_parts.append(f"{time_str}: {activity} ({booking_type})")
            else:
                description_parts.append(f"- {activity} ({booking_type})")

            ref = booking.get('booking_ref', '')
            if ref:
                description_parts.append(f"  Ref: {ref}")

        description = '\n'.join(description_parts)

        summary = f"{trip_name} - Day {day_num}: {location}" if location else f"{trip_name} - Day {day_num}"

        base_url = "https://calendar.google.com/calendar/render"
        params = {
            'action': 'TEMPLATE',
            'text': summary,
            'dates': f"{start_str}/{end_str}",
            'details': description,
            'location': location,
            'sf': 'true',
            'output': 'xml'
        }

        links.append({
            'day_num': day_num,
            'day_key': day_key,
            'location': location,
            'url': f"{base_url}?{urllib.parse.urlencode(params)}"
        })

    return links


def generate_google_calendar_link(trip_data, mode='block'):
    """Generate Google Calendar link based on mode.

    Args:
        trip_data: The trip data dictionary
        mode: 'block' (single event), 'day_by_day' (one per day)

    Returns:
        For 'block': single URL string
        For 'day_by_day': list of link dictionaries
    """
    if mode == 'block':
        return generate_google_calendar_link_block(trip_data)
    elif mode == 'day_by_day':
        return generate_google_calendar_links_day_by_day(trip_data)
    else:
        return generate_google_calendar_link_block(trip_data)


def generate_share_link(trip_data):
    """Generate shareable link with encoded trip data."""
    # Encode trip data as base64 for URL parameter
    trip_json = json.dumps(trip_data, default=str)
    encoded_data = base64.urlsafe_b64encode(trip_json.encode()).decode()

    # Get current Streamlit app URL (will be replaced with actual deployed URL)
    # For now, return the encoded data that can be added as query parameter
    return encoded_data


def detect_booking_issues(trip_data):
    """Detect problematic bookings that need user attention - ONLY real issues."""
    issues = []
    days = trip_data.get('days', {})

    for day_key in sorted(days.keys()):
        day = days[day_key]
        day_num = day.get('day_num', 'N/A')
        bookings = day.get('bookings', [])

        for booking in bookings:
            booking_name = booking.get('activity_name') or booking.get('subject', 'Unknown')
            issue_list = []

            # Check for TBD or missing/incomplete location - REAL ISSUE
            loc_info = booking.get('location_info', {})
            meeting = loc_info.get('meeting_point', '') or loc_info.get('hotel', '')
            if not meeting or 'TBD' in str(meeting).upper() or 'TO BE DETERMINED' in str(meeting).upper() or 'TO BE DECIDED' in str(meeting).upper():
                issue_list.append("📍 Location missing - needs to be added")

            # Check for missing or TBD times - REAL ISSUE
            time_info = booking.get('time_info', {})
            time_str = time_info.get('start_time', '') or time_info.get('end_time', '')
            if not time_str or 'TBD' in str(time_str).upper():
                issue_list.append("🕐 Time missing - needs to be scheduled")

            # Check notes for EXPLICIT action keywords - REAL ISSUE ONLY
            notes = booking.get('notes', '')
            if notes:
                # Only flag if note explicitly mentions action needed
                action_keywords = ['need to decide', 'need to confirm', 'need to book', 'need to check',
                                  'needs to be decided', 'needs to be confirmed', 'needs to be booked',
                                  'not yet booked', 'must decide', 'must confirm', 'action required',
                                  'pending decision', 'pending confirmation']
                if any(keyword in notes.lower() for keyword in action_keywords):
                    issue_list.append(f"⚠️ Action needed: {notes[:50]}...")

            # Check status - only flag if truly problematic
            status = booking.get('status', '')
            if status.lower() in ['not booked', 'unconfirmed', 'cancelled']:
                issue_list.append(f"❌ Status: {status} - action required")

            # If any REAL issues found, add to list
            if issue_list:
                issues.append({
                    'day_num': day_num,
                    'day_key': day_key,
                    'booking_name': booking_name,
                    'issue': ' • '.join(issue_list),
                    'booking': booking
                })

    return issues


def render_booking_card(booking, show_date=False, edit_button_id=None):
    """Render a single booking as a styled card with optional edit button."""
    type_config = {
        'flights': {'icon': '✈️', 'label': 'FLIGHT', 'color': '#FF6B6B'},
        'hotels': {'icon': '🏨', 'label': 'STAY', 'color': '#4ECDC4'},
        'tours': {'icon': '🎫', 'label': 'ACTIVITY', 'color': '#FFE66D'},
        'ferries': {'icon': '⛴️', 'label': 'TRANSPORT', 'color': '#95E1D3'},
        'dining': {'icon': '🍽️', 'label': 'DINING', 'color': '#F38181'},
        'spa': {'icon': '💆', 'label': 'SPA', 'color': '#DDA0DD'},
    }

    btype = booking.get('type', 'tours')
    config = type_config.get(btype, {'icon': '📋', 'label': 'BOOKING', 'color': '#888'})

    title = booking.get('activity_name') or booking.get('subject', 'Booking')
    if len(title) > 60:
        title = title[:57] + '...'

    time_info = booking.get('time_info', {})
    time_str = time_info.get('start_time', '') or time_info.get('end_time', '')

    loc_info = booking.get('location_info', {})
    meeting = loc_info.get('meeting_point', '') or loc_info.get('hotel', '')
    if meeting and len(meeting) > 80:
        meeting = meeting[:77] + '...'

    ref = booking.get('booking_ref', '')
    notes = booking.get('notes', '')
    status = booking.get('status', '')

    # Get detected date
    trip_date = booking.get('trip_date')
    date_str = ''
    if show_date and trip_date:
        if isinstance(trip_date, str):
            date_str = trip_date[:10]
        else:
            date_str = trip_date.strftime('%Y-%m-%d')

    # Build card HTML - add extra padding on right for button space
    html = f'''
    <div style="background: white; border-radius: 12px; padding: 16px 50px 16px 16px; margin: 4px 0; border-left: 4px solid {config['color']}; position: relative; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
        <div style="font-size: 0.75rem; color: {config['color']}; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
            {config['icon']} {config['label']}
        </div>
        <div style="font-size: 1.05rem; font-weight: 600; color: #333; margin: 6px 0;">
            {title}
        </div>
    '''

    if booking.get('sender'):
        html += f'<div style="font-size: 0.85rem; color: #666;">📧 {booking["sender"]}</div>'

    if show_date and date_str:
        html += f'<div style="font-size: 0.85rem; color: #4A90A4; font-weight: 500;">📅 Detected: {date_str}</div>'
    elif show_date:
        html += f'<div style="font-size: 0.85rem; color: #e74c3c; font-weight: 500;">⚠️ No date found in email</div>'

    if time_str:
        html += f'<div style="font-size: 0.85rem; color: #666;">🕐 {time_str}</div>'

    if meeting:
        html += f'<div style="font-size: 0.85rem; color: #666;">📍 {meeting}</div>'

    if ref and ref != 'ffffff':
        html += f'<div style="margin-top: 8px;"><span style="background: #e8f4f8; color: #4A90A4; padding: 4px 10px; border-radius: 6px; font-family: monospace; font-size: 0.85rem;">{ref}</span></div>'

    if status:
        status_colors = {
            'confirmed': '#28a745',
            'pending': '#ffc107',
            'optional': '#6c757d',
            'cancelled': '#dc3545'
        }
        status_color = status_colors.get(status.lower(), '#6c757d')
        html += f'<div style="margin-top: 8px;"><span style="background: {status_color}; color: white; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; text-transform: uppercase;">{status}</span></div>'

    # Show notes without warning icon - format checkboxes and preserve formatting
    if notes:
        # Convert [ ] to checkbox HTML and preserve line breaks
        formatted_notes = notes.replace('\n', '<br>')
        # Replace [ ] with unchecked checkbox
        formatted_notes = formatted_notes.replace('[ ]', '<input type="checkbox" disabled style="margin-right: 8px; vertical-align: middle;">')
        # Replace [x] with checked checkbox
        formatted_notes = formatted_notes.replace('[x]', '<input type="checkbox" checked disabled style="margin-right: 8px; vertical-align: middle;">')
        formatted_notes = formatted_notes.replace('[X]', '<input type="checkbox" checked disabled style="margin-right: 8px; vertical-align: middle;">')

        html += f'<div style="background: #e7f3ff; border-left: 3px solid #4A90A4; padding: 8px; margin-top: 8px; border-radius: 4px; font-size: 0.8rem; color: #004085; line-height: 1.6;">{formatted_notes}</div>'

    html += '</div>'

    return html


@st.dialog("✏️ Edit Booking", width="medium")
def show_edit_booking_modal():
    """Show modal for editing a booking."""
    if 'edit_booking' not in st.session_state:
        return

    booking_data = st.session_state.edit_booking
    booking = booking_data['booking']

    with st.form(key="edit_booking_form"):
        booking_type = st.selectbox(
            "Type",
            options=['hotels', 'flights', 'tours', 'ferries', 'dining', 'spa'],
            index=['hotels', 'flights', 'tours', 'ferries', 'dining', 'spa'].index(booking.get('type', 'tours'))
        )

        activity_name = st.text_input("Name", value=booking.get('activity_name', ''))

        col1, col2 = st.columns(2)
        with col1:
            start_time = st.text_input("Start Time", value=booking.get('time_info', {}).get('start_time', ''))
        with col2:
            end_time = st.text_input("End Time", value=booking.get('time_info', {}).get('end_time', ''))

        meeting_point = st.text_area("Address/Location", value=booking.get('location_info', {}).get('meeting_point', ''))

        booking_ref = st.text_input("Booking Reference", value=booking.get('booking_ref', ''))

        status = st.selectbox(
            "Status",
            options=['confirmed', 'pending', 'optional', 'cancelled'],
            index=['confirmed', 'pending', 'optional', 'cancelled'].index(booking.get('status', 'confirmed').lower()) if booking.get('status', 'confirmed').lower() in ['confirmed', 'pending', 'optional', 'cancelled'] else 0
        )

        notes = st.text_area("Notes", value=booking.get('notes', ''))

        # File upload
        uploaded_files = st.file_uploader(
            "Attach Files (PDF/Images)",
            accept_multiple_files=True,
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="Upload booking confirmations, tickets, or vouchers"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            # Update booking data
            booking['type'] = booking_type
            booking['activity_name'] = activity_name
            booking['time_info'] = {'start_time': start_time, 'end_time': end_time}
            booking['location_info'] = {'meeting_point': meeting_point}
            booking['booking_ref'] = booking_ref
            booking['status'] = status
            booking['notes'] = notes

            # Handle file uploads
            if uploaded_files:
                attachments = []
                for file in uploaded_files:
                    file_data = file.read()
                    file_b64 = base64.b64encode(file_data).decode()
                    attachments.append({
                        'filename': file.name,
                        'data': file_b64
                    })
                booking['attachments'] = attachments

            # Save to itinerary.json
            save_trip_data(st.session_state.trip_data)

            st.success("✅ Booking updated successfully!")
            del st.session_state.edit_booking
            st.rerun()

        if cancel:
            del st.session_state.edit_booking
            st.rerun()

@st.dialog("➕ Add New Booking", width="small")
def show_add_booking_modal():
    """Show modal for adding a new booking to a day."""
    if 'add_booking_day' not in st.session_state:
        return

    day_key = st.session_state.add_booking_day

    with st.form(key="add_booking_form"):
        booking_type = st.selectbox(
            "Type",
            options=['hotels', 'flights', 'tours', 'ferries', 'dining', 'spa']
        )

        activity_name = st.text_input("Name", placeholder="e.g., Grand Hotel Check-in")

        col1, col2 = st.columns(2)
        with col1:
            start_time = st.text_input("Start Time", placeholder="e.g., 2:00 PM")
        with col2:
            end_time = st.text_input("End Time", placeholder="e.g., 5:00 PM")

        meeting_point = st.text_area("Address/Location", placeholder="Enter full address or location", height=80)

        booking_ref = st.text_input("Booking Reference", placeholder="e.g., ABC123456")

        status = st.selectbox("Status", options=['confirmed', 'pending', 'optional', 'cancelled'])

        notes = st.text_area("Notes", placeholder="Any special instructions or reminders", height=80)

        # File upload
        uploaded_files = st.file_uploader(
            "Attach Files (PDF/Images)",
            accept_multiple_files=True,
            type=['pdf', 'png', 'jpg', 'jpeg'],
            help="Upload booking confirmations, tickets, or vouchers"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("➕ Add Booking", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            if not activity_name:
                st.error("Please enter a booking name")
            else:
                # Create new booking
                new_booking = {
                    'type': booking_type,
                    'activity_name': activity_name,
                    'time_info': {'start_time': start_time, 'end_time': end_time},
                    'location_info': {'meeting_point': meeting_point},
                    'booking_ref': booking_ref,
                    'status': status,
                    'notes': notes,
                    'subject': activity_name
                }

                # Handle file uploads
                if uploaded_files:
                    attachments = []
                    for file in uploaded_files:
                        file_data = file.read()
                        file_b64 = base64.b64encode(file_data).decode()
                        attachments.append({
                            'filename': file.name,
                            'data': file_b64
                        })
                    new_booking['attachments'] = attachments

                # Add to day
                st.session_state.trip_data['days'][day_key]['bookings'].append(new_booking)

                # Save to itinerary.json
                save_trip_data(st.session_state.trip_data)

                st.success("✅ Booking added successfully!")
                del st.session_state.add_booking_day
                st.rerun()

        if cancel:
            del st.session_state.add_booking_day
            st.rerun()

@st.dialog("➕ Add New Day", width="medium")
def show_add_day_modal():
    """Show modal for adding a new day to the itinerary."""
    with st.form(key="add_day_form"):
        day_date = st.date_input("Date", value=datetime.now())

        st.info("💡 Enter any city name - it will be automatically geocoded and shown on the map!")

        location_name = st.text_input(
            "Location (City/Place)",
            placeholder="e.g., Paris, New York, Tokyo, Santorini",
            help="Type any city or place name - works worldwide!"
        )

        location_display = st.text_input(
            "Custom Display Name (Optional)",
            placeholder="Leave empty to use location name",
            help="Custom name to display for this location (optional)"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("➕ Add Day", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            if not location_name:
                st.error("Please enter a location name!")
            else:
                # Create new day
                day_key = day_date.strftime('%Y-%m-%d')

                # Check if day already exists
                if day_key in st.session_state.trip_data['days']:
                    st.error(f"Day {day_key} already exists!")
                else:
                    # Convert location name to normalized key
                    location_key = location_name.lower().replace(' ', '_').replace(',', '')

                    # Find the right day number
                    existing_days = list(st.session_state.trip_data['days'].keys())
                    day_num = len(existing_days) + 1

                    new_day = {
                        'day_num': day_num,
                        'display': day_date.strftime('%A, %B %d'),
                        'location': location_key,
                        'location_display': location_display if location_display else location_name,
                        'bookings': []
                    }

                    st.session_state.trip_data['days'][day_key] = new_day

                    # Save to itinerary.json
                    save_trip_data(st.session_state.trip_data)

                    st.success(f"✅ Day {day_num} added! '{location_name}' will be geocoded automatically on the map.")
                    if 'show_add_day_modal' in st.session_state:
                        del st.session_state.show_add_day_modal
                    st.rerun()

        if cancel:
            if 'show_add_day_modal' in st.session_state:
                del st.session_state.show_add_day_modal
            st.rerun()


@st.dialog("✏️ Edit Day Information", width="medium")
def show_edit_day_modal():
    """Show modal for editing day metadata."""
    if 'edit_day' not in st.session_state:
        return

    day_key = st.session_state.edit_day
    day = st.session_state.trip_data['days'][day_key]

    with st.form(key="edit_day_form"):
        st.info("💡 Enter any city name - it will be automatically geocoded and shown on the map!")

        location_name = st.text_input(
            "Location (City/Place)",
            value=day.get('location_display', '') or (LOCATION_COORDS.get(day.get('location', ''), {}).get('name', '')),
            placeholder="e.g., Paris, New York, Tokyo, Santorini",
            help="Type any city or place name - works worldwide!"
        )

        location_display = st.text_input(
            "Custom Display Name (Optional)",
            value=day.get('location_display', ''),
            placeholder="Leave empty to use location name",
            help="Custom name to display for this location (optional)"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            # Convert location name to normalized key
            location_key = location_name.lower().replace(' ', '_').replace(',', '')

            # Update day data
            day['location'] = location_key
            day['location_display'] = location_display if location_display else location_name

            # Save to itinerary.json
            save_trip_data(st.session_state.trip_data)

            st.success(f"✅ Day updated! '{location_name}' will be geocoded automatically on the map.")
            del st.session_state.edit_day
            st.rerun()

        if cancel:
            del st.session_state.edit_day
            st.rerun()

def save_trip_data(trip_data):
    """Save trip data back to itinerary.json."""
    try:
        with open('itinerary.json', 'w') as f:
            json.dump({
                'trip_name': trip_data.get('trip_name', 'My Trip'),
                'days': trip_data.get('days', {}),
                'unassigned': trip_data.get('unassigned', [])
            }, f, indent=2, default=str)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")




def create_day_map(day_data, day_key, all_days):
    """Create a map showing locations for a specific day with activity markers at their exact locations."""
    location = day_data.get('location')

    # Try smart geocoding for the day's location
    loc_coords = geocode_location(location) if location else None

    if not loc_coords:
        # Fallback to basic map
        m = folium.Map(location=[13.7563, 100.5018], zoom_start=6)
        return m

    # Get all bookings for this day
    bookings = day_data.get('bookings', [])

    # Calculate bounds to fit all markers
    all_lats = [loc_coords['lat']]
    all_lons = [loc_coords['lon']]

    # Type colors for numbered markers (matching your design)
    type_colors = {
        'hotels': '#4ECDC4',      # Teal
        'flights': '#FF6B6B',     # Coral/Red
        'tours': '#FFE66D',       # Yellow
        'activity': '#FFE66D',    # Yellow (same as tours)
        'ferries': '#95E1D3',     # Mint
        'dining': '#F38181',      # Pink/Salmon
        'spa': '#DDA0DD',         # Plum
        'transport': '#87CEEB',   # Sky blue
    }

    # Create map without initial zoom - we'll fit bounds instead
    m = folium.Map(location=[loc_coords['lat'], loc_coords['lon']])

    # Add markers for each booking at their exact locations
    for idx, booking in enumerate(bookings):
        btype = booking.get('type', 'tours').lower()  # Normalize to lowercase
        activity_name = booking.get('activity_name', booking.get('subject', 'Activity'))
        marker_color = type_colors.get(btype, '#888888')

        # ALWAYS place marker at offset from center (simpler approach)
        # Spread markers in a small grid pattern around the center
        row = idx // 3
        col = idx % 3
        marker_lat = loc_coords['lat'] + (row * 0.003) - 0.003
        marker_lon = loc_coords['lon'] + (col * 0.004) - 0.004

        all_lats.append(marker_lat)
        all_lons.append(marker_lon)

        # Create numbered square marker with activity-type color
        marker_num = idx + 1
        icon_html = f'''
        <div style="
            background: {marker_color};
            color: white;
            border-radius: 8px;
            width: 36px;
            height: 36px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: bold;
            border: 3px solid white;
            box-shadow: 0 3px 10px rgba(0,0,0,0.3);
        ">{marker_num}</div>
        '''

        # Popup content
        time_info = booking.get('time_info', {})
        time_str = time_info.get('start_time', '')
        loc_info = booking.get('location_info', {})
        address = loc_info.get('meeting_point', '') or loc_info.get('address', '') or loc_info.get('hotel', '')

        popup_html = f"""
        <div style="min-width: 200px;">
            <b>{marker_num}. {activity_name}</b><br>
            {f'🕐 {time_str}<br>' if time_str else ''}
            {f'📍 {address[:80]}{"..." if len(address) > 80 else ""}<br>' if address else ''}
            <span style="background: {marker_color}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">{btype.upper()}</span>
        </div>
        """

        folium.Marker(
            [marker_lat, marker_lon],
            popup=popup_html,
            icon=folium.DivIcon(html=icon_html, icon_size=(36, 36), icon_anchor=(18, 18))
        ).add_to(m)

    # Add main day number marker at center
    day_num = day_data.get('day_num', '1')
    center_marker_html = f'''
    <div style="
        background: linear-gradient(135deg, #4A90A4 0%, #357ABD 100%);
        color: white;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        font-size: 22px;
        border: 4px solid white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4);
    ">{day_num}</div>
    '''

    popup_html = f"""
    <b>Day {day_num}</b><br>
    {loc_coords['name']}<br>
    {day_data.get('display', '')}<br>
    {len(bookings)} activity/activities
    """

    folium.Marker(
        [loc_coords['lat'], loc_coords['lon']],
        popup=popup_html,
        icon=folium.DivIcon(html=center_marker_html, icon_size=(50, 50), icon_anchor=(25, 25))
    ).add_to(m)

    # Fit map bounds to show all markers with padding
    if len(all_lats) > 1:
        southwest = [min(all_lats) - 0.003, min(all_lons) - 0.003]
        northeast = [max(all_lats) + 0.003, max(all_lons) + 0.003]
        m.fit_bounds([southwest, northeast], padding=(30, 30))

    return m


def render_illustrative_view(trip_data):
    """Render the journey view with day selector and interactive map."""
    days = trip_data.get('days', {})

    if not days:
        st.warning("No days in itinerary")
        return

    # Initialize selected day in session state
    if 'selected_journey_day' not in st.session_state:
        st.session_state.selected_journey_day = sorted(days.keys())[0]

    st.markdown("### Journey View")

    # Two column layout: Map on LEFT, Day selector + details on RIGHT
    map_col, details_col = st.columns([1.5, 1], gap="large")

    with map_col:
        # Show map for selected day
        selected_day_key = st.session_state.selected_journey_day
        if selected_day_key in days:
            selected_day = days[selected_day_key]
            day_map = create_day_map(selected_day, selected_day_key, days)
            st_folium(day_map, width=None, height=700, key=f"day_map_{selected_day_key}")

            # Color legend for activity types
            st.markdown("""
            <div style="display: flex; flex-wrap: wrap; gap: 12px; margin-top: 10px; padding: 12px; background: #f8f9fa; border-radius: 10px;">
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #4ECDC4; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Hotels</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #FF6B6B; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Flights</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #FFE66D; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Tours/Activities</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #F38181; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Dining</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #95E1D3; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Ferries</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #DDA0DD; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Spa</span>
                </div>
                <div style="display: flex; align-items: center; gap: 6px;">
                    <div style="width: 20px; height: 20px; background: #87CEEB; border-radius: 4px;"></div>
                    <span style="font-size: 13px;">Transport</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with details_col:
        st.markdown("#### Select Day")

        # Day selector cards styled like Figma design
        for day_key in sorted(days.keys()):
            day = days[day_key]
            day_num = day.get('day_num')
            location_display = day.get('location_display', '')
            display_date = day.get('display', '')
            loc_key = day.get('location', '')
            loc_info = LOCATION_COORDS.get(loc_key, {})
            icon = loc_info.get('icon', '📍')
            num_bookings = len(day.get('bookings', []))

            # Highlight selected day
            is_selected = (day_key == st.session_state.selected_journey_day)

            # Determine button type based on selection
            button_type = "primary" if is_selected else "secondary"

            # Build the button label
            button_label = f"{day_num} {icon} {location_display} • {display_date.split(',')[1].strip() if ',' in display_date else display_date} [{num_bookings}]"

            if st.button(button_label, key=f"select_day_{day_key}", type=button_type, help=f"Click to select {display_date}"):
                st.session_state.selected_journey_day = day_key
                st.rerun()

        st.markdown("---")

        # Show details of selected day
        if st.session_state.selected_journey_day in days:
            selected_day = days[st.session_state.selected_journey_day]

            st.markdown(f"### Day {selected_day.get('day_num')} Details")
            st.markdown(f"**{selected_day.get('display')}**")
            st.markdown(f"**Location:** {selected_day.get('location_display')}")

            st.markdown("---")

            # Show all bookings for selected day
            bookings = selected_day.get('bookings', [])
            if bookings:
                for booking in bookings:
                    st.html(render_booking_card(booking))
            else:
                st.info("No bookings for this day - free to explore!")


def render_day_by_day_view(trip_data):
    """Render the day-by-day timeline view."""
    days = trip_data.get('days', {})
    unassigned = trip_data.get('unassigned', [])

    # Check if we're in jump mode (user clicked an issue card)
    jump_mode = 'jump_to_day' in st.session_state and st.session_state.jump_to_day is not None
    target_day_key = st.session_state.get('jump_to_day', None)

    # Day-by-Day header with Add Day button
    header_col1, header_col2 = st.columns([20, 1])
    with header_col1:
        st.markdown("### Day-by-Day Itinerary")
    with header_col2:
        if st.button("➕", key="add_new_day", help="Add a new day to the itinerary"):
            st.session_state.show_add_day_modal = True
            show_add_day_modal()

    if not days:
        st.warning("No bookings found for the selected date range. Check the 'Unassigned' section below.")

    # Check if we need to detect issues for warning icons
    issues_by_day = {}
    all_issues = detect_booking_issues(trip_data)
    for issue in all_issues:
        day_num = issue['day_num']
        if day_num not in issues_by_day:
            issues_by_day[day_num] = []
        issues_by_day[day_num].append(issue)

    for day_key in sorted(days.keys()):
        day = days[day_key]
        location_display = day.get('location_display', '')
        loc_key = day.get('location', '')
        loc_info = LOCATION_COORDS.get(loc_key, {})
        icon = loc_info.get('icon', '📍')
        day_num = day['day_num']

        # Add warning icon if day has issues
        warning_icon = f" ⚠️" if day_num in issues_by_day else ""

        expander_label = f"**Day {day_num}** • {icon} {location_display} • {day['display']}{warning_icon}"

        # Determine if this expander should be expanded
        # If in jump mode: only expand the target day, collapse others
        # If not in jump mode: expand all by default
        if jump_mode:
            should_expand = (day_key == target_day_key)
        else:
            should_expand = True

        # Add scroll anchor with unique ID
        anchor_id = f"day_anchor_{day_key}"

        # If this is the target day, inject JavaScript to scroll to it
        if jump_mode and day_key == target_day_key:
            # Add the anchor div first
            st.markdown(f'<div id="{anchor_id}" style="scroll-margin-top: 100px;"></div>', unsafe_allow_html=True)
            # Use components.html for more reliable JavaScript execution
            components.html(f"""
                <script>
                    // Find the anchor in the parent document
                    var anchor = window.parent.document.getElementById('{anchor_id}');
                    if (anchor) {{
                        anchor.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                    }}
                    // Delayed scroll for after Streamlit fully renders
                    setTimeout(function() {{
                        var anchor = window.parent.document.getElementById('{anchor_id}');
                        if (anchor) {{
                            anchor.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                        }}
                    }}, 500);
                    setTimeout(function() {{
                        var anchor = window.parent.document.getElementById('{anchor_id}');
                        if (anchor) {{
                            anchor.scrollIntoView({{behavior: 'smooth', block: 'start'}});
                        }}
                    }}, 1000);
                </script>
            """, height=0)
            # Clear the jump flag after processing
            del st.session_state.jump_to_day
        else:
            st.markdown(f'<div id="{anchor_id}"></div>', unsafe_allow_html=True)

        # Use standard expander with action buttons inside at top-right
        expander_label = f"**Day {day_num}** • {icon} {location_display} • {day['display']}{warning_icon}"

        with st.expander(expander_label, expanded=should_expand):
            # Action buttons row at top of expander - right aligned
            btn_spacer, btn_edit, btn_add = st.columns([0.88, 0.06, 0.06])
            with btn_edit:
                if st.button("✏️", key=f"edit_day_{day_key}", help="Edit day"):
                    st.session_state.edit_day = day_key
                    show_edit_day_modal()
            with btn_add:
                if st.button("➕", key=f"add_booking_{day_key}", help="Add booking"):
                    st.session_state.add_booking_day = day_key
                    show_add_booking_modal()

            # Bookings content
            bookings = day.get('bookings', [])
            if bookings:
                for idx, booking in enumerate(bookings):
                    booking_key = f"{day_key}_booking_{idx}"
                    col1, col2 = st.columns([0.95, 0.05])
                    with col1:
                        st.html(render_booking_card(booking))
                    with col2:
                        if st.button("✏️", key=f"edit_{booking_key}", help="Edit this booking"):
                            st.session_state.edit_booking = {'day_key': day_key, 'booking_idx': idx, 'booking': booking}
                            show_edit_booking_modal()
            else:
                st.info("No bookings for this day - free to explore!")

    # Unassigned
    if unassigned:
        st.markdown("---")
        st.markdown("### Unassigned Bookings")
        st.markdown("These bookings have dates that **don't match your selected date range**, or no date was found.")
        st.info("💡 **Tip:** Check if your date range is correct, or the booking dates may be outside your trip dates.")

        for i, booking in enumerate(unassigned):
            st.html(render_booking_card(booking, show_date=True))


@st.dialog("📅 Export to Calendar", width="medium")
def show_calendar_export_dialog(trip_data):
    """Show calendar export dialog with multiple export modes."""

    st.markdown("### Choose Calendar Export Type")
    st.markdown("Select how you want to add your trip to your calendar:")

    # Export mode selection with clear descriptions
    export_mode = st.radio(
        "Export Mode",
        options=["Block Trip Days", "Day-by-Day Breakdown", "Individual Activities"],
        format_func=lambda x: {
            "Block Trip Days": "Block Trip Days - Single event spanning your entire trip",
            "Day-by-Day Breakdown": "Day-by-Day Breakdown - One event per day with daily schedule",
            "Individual Activities": "Individual Activities - Separate timed events for each activity"
        }.get(x, x),
        help="Choose how your trip will appear in your calendar"
    )

    st.markdown("---")

    # Mode-specific preview and description
    if export_mode == "Block Trip Days":
        st.info("**Block Trip Days**\n\nCreates a single calendar event from your first day to your last day. The event description includes your complete day-by-day itinerary. Best for getting a quick overview of when you're traveling.")

        trip_name = trip_data.get('trip_name', 'My Trip')
        start_date = trip_data.get('start_date', '')
        end_date = trip_data.get('end_date', '')
        total_days = trip_data.get('total_days', 0)

        st.markdown(f"**Preview:** *{trip_name}* ({start_date} - {end_date}, {total_days} days)")

    elif export_mode == "Day-by-Day Breakdown":
        st.info("**Day-by-Day Breakdown**\n\nCreates one all-day event for each day of your trip. Each event includes that day's location and all activities. Best for seeing your trip day by day on your calendar.")

        days = trip_data.get('days', {})
        st.markdown(f"**Preview:** {len(days)} day events will be created")

        # Show first 3 days as preview
        preview_days = list(sorted(days.keys()))[:3]
        for day_key in preview_days:
            day = days[day_key]
            day_num = day.get('day_num', '')
            location = day.get('location_display') or day.get('location', 'TBD')
            bookings_count = len(day.get('bookings', []))
            st.markdown(f"- Day {day_num}: {location} ({bookings_count} activities)")

        if len(days) > 3:
            st.markdown(f"- ... and {len(days) - 3} more days")

    elif export_mode == "Individual Activities":
        st.info("**Individual Activities**\n\nCreates a separate calendar event for each activity with specific times. Events without times become all-day events. Best for detailed schedule management.")

        # Count activities with and without times
        total_activities = 0
        timed_activities = 0
        for day in trip_data.get('days', {}).values():
            for booking in day.get('bookings', []):
                total_activities += 1
                time_info = booking.get('time_info', {})
                if time_info.get('start_time'):
                    timed_activities += 1

        st.markdown(f"**Preview:** {total_activities} events will be created ({timed_activities} with specific times)")

    st.markdown("---")

    # Export buttons section
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # Generate ICS file based on mode
        mode_map = {
            "Block Trip Days": "block",
            "Day-by-Day Breakdown": "day_by_day",
            "Individual Activities": "individual"
        }
        ical_mode = mode_map.get(export_mode, "block")

        ical_data = generate_ical(trip_data, mode=ical_mode)
        if ical_data:
            filename_suffix = {
                "block": "trip_block",
                "day_by_day": "day_by_day",
                "individual": "activities"
            }.get(ical_mode, "calendar")

            trip_name_safe = trip_data.get('trip_name', 'trip').replace(' ', '_')
            filename = f"{trip_name_safe}_{filename_suffix}.ics"

            st.download_button(
                label="Download .ics File",
                data=ical_data,
                file_name=filename,
                mime="text/calendar",
                help="Download calendar file to import into any calendar app",
                type="primary",
                key="download_ics_btn"
            )
        else:
            st.error("Unable to generate calendar file")

    with col2:
        # Google Calendar link
        if export_mode == "Block Trip Days":
            gcal_link = generate_google_calendar_link(trip_data, mode='block')
            if gcal_link:
                st.markdown(f'''
                    <a href="{gcal_link}" target="_blank" style="text-decoration: none; display: inline-block; width: 100%;">
                        <button style="
                            background-color: #4285F4;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.5rem;
                            font-size: 0.875rem;
                            font-weight: 500;
                            cursor: pointer;
                            width: 100%;
                            height: 42px;
                            transition: all 0.2s;
                        " onmouseover="this.style.backgroundColor='#3367D6'"
                           onmouseout="this.style.backgroundColor='#4285F4'">
                            Add to Google Calendar
                        </button>
                    </a>
                ''', unsafe_allow_html=True)
        elif export_mode == "Day-by-Day Breakdown":
            gcal_links = generate_google_calendar_link(trip_data, mode='day_by_day')
            if gcal_links and len(gcal_links) > 0:
                # Show first day link with note
                first_link = gcal_links[0]['url']
                st.markdown(f'''
                    <a href="{first_link}" target="_blank" style="text-decoration: none; display: inline-block; width: 100%;">
                        <button style="
                            background-color: #4285F4;
                            color: white;
                            padding: 0.5rem 1rem;
                            border: none;
                            border-radius: 0.5rem;
                            font-size: 0.875rem;
                            font-weight: 500;
                            cursor: pointer;
                            width: 100%;
                            height: 42px;
                            transition: all 0.2s;
                        " onmouseover="this.style.backgroundColor='#3367D6'"
                           onmouseout="this.style.backgroundColor='#4285F4'">
                            Add Day 1 to Google
                        </button>
                    </a>
                ''', unsafe_allow_html=True)
                st.caption("*Download .ics for all days*")
        else:
            st.markdown('''
                <button disabled style="
                    background-color: #ccc;
                    color: #666;
                    padding: 0.5rem 1rem;
                    border: none;
                    border-radius: 0.5rem;
                    font-size: 0.875rem;
                    font-weight: 500;
                    cursor: not-allowed;
                    width: 100%;
                    height: 42px;
                ">
                    Use .ics for Activities
                </button>
            ''', unsafe_allow_html=True)
            st.caption("*Google Calendar only supports single events. Download .ics for multiple activities.*")

    with col3:
        if st.button("Close", key="close_calendar_dialog_btn"):
            st.rerun()

    # Show all day links for day-by-day mode in an expander
    if export_mode == "Day-by-Day Breakdown":
        gcal_links = generate_google_calendar_link(trip_data, mode='day_by_day')
        if gcal_links and len(gcal_links) > 1:
            with st.expander("Add individual days to Google Calendar"):
                for link_info in gcal_links:
                    day_num = link_info['day_num']
                    location = link_info['location'] or 'TBD'
                    url = link_info['url']
                    st.markdown(f"[Day {day_num}: {location}]({url})")


@st.dialog("📤 Export Itinerary", width="small")
def show_export_dialog(trip_data):
    """Show export dialog to choose format and type."""

    if not PDF_EXPORT_AVAILABLE:
        st.error("PDF export is not available. Please install reportlab: pip install reportlab")
        return

    st.markdown("### Choose Export Options")

    export_type = st.radio(
        "Export Type",
        options=["Full Journey", "Day-by-Day"],
        help="Full Journey = All days in one PDF. Day-by-Day = Each day on separate page."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # Buttons in a row using columns
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Generate PDF", type="primary", key="generate_pdf_btn"):
            with st.spinner("Generating PDF with map screenshots..."):
                try:
                    if export_type == "Full Journey":
                        pdf_data = generate_full_journey_pdf(trip_data, LOCATION_COORDS)
                        filename = f"{trip_data.get('trip_name', 'trip')}_full_journey.pdf"
                    else:
                        pdf_data = generate_day_by_day_pdf(trip_data, LOCATION_COORDS)
                        filename = f"{trip_data.get('trip_name', 'trip')}_day_by_day.pdf"

                    # Store PDF in session state to show download button
                    st.session_state.pdf_data = pdf_data
                    st.session_state.pdf_filename = filename
                    st.success("✅ PDF generated successfully!")

                except Exception as e:
                    st.error(f"Error generating PDF: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())

    with col2:
        if st.button("Cancel", key="cancel_export_btn"):
            st.rerun()

    with col3:
        # Show download button if PDF was generated
        if 'pdf_data' in st.session_state:
            st.download_button(
                label="Download PDF",
                data=st.session_state.pdf_data,
                file_name=st.session_state.pdf_filename,
                mime="application/pdf",
                key="download_pdf_btn"
            )


def main():
    # Check for shared trip link in URL parameters
    query_params = st.query_params
    if 'trip' in query_params:
        try:
            # Decode the shared trip data
            encoded_data = query_params['trip']
            decoded_json = base64.urlsafe_b64decode(encoded_data.encode()).decode()
            shared_trip = json.loads(decoded_json)

            # Load shared trip into session state
            if 'shared_trip_loaded' not in st.session_state:
                st.session_state.trip = shared_trip
                st.session_state.shared_trip_loaded = True
                st.success("✅ Shared trip loaded successfully!")
        except Exception as e:
            st.error(f"❌ Failed to load shared trip: {str(e)}")

    # Sidebar
    with st.sidebar:
        st.markdown("### Trip Visualizer")
        st.markdown("---")

        st.subheader("➕ Add Your Trip")

        # Search method
        search_method = st.radio(
            "How would you like to add your trip?",
            ["Demo Mode", "Paste Itinerary"],
            horizontal=True,
            help="Demo Mode uses sample data, or paste your own itinerary"
        )

        if search_method == "Demo Mode":
            st.info("📌 Demo mode uses pre-loaded sample data (Thailand trip)")
            search_input = "demo"
            search_label = None
            search_query = None
        elif search_method == "Paste Itinerary":
            # Initialize session state
            if 'formatted_itinerary' not in st.session_state:
                st.session_state.formatted_itinerary = ''
            if 'last_raw_input' not in st.session_state:
                st.session_state.last_raw_input = ''

            st.info("💡 Structure your itinerary before pasting")

            # Copy prompt button - using streamlit component for clipboard
            prompt_text = """Convert my travel itinerary into structured format.

═══════════════════════════════════════════════════════════════════
CRITICAL: SPLIT COMPLEX DAYS INTO MULTIPLE BOOKINGS
═══════════════════════════════════════════════════════════════════
When a day has multiple activities (meals, tours, transport), create SEPARATE entries for each!

BAD (everything jammed together):
10:25 AM | Tour | Paris Day | Paris | — | Confirmed
Notes: Land at CDG, lunch at restaurant, bike tour, dinner at Les Ombres...

GOOD (split properly):
10:25 AM | Flight | Arrive CDG Airport | Paris | — | Confirmed
1:30 PM | Dining | Lunch at La Pause Verte | Paris | — | Confirmed
2:30 PM | Tour | Bike Tour Right Bank | Trocadéro | — | Confirmed
7:30 PM | Dining | Birthday Dinner at Les Ombres | Eiffel Tower | — | Confirmed

═══════════════════════════════════════════════════════════════════
NOTES ARE FOR LOGISTICS ONLY:
═══════════════════════════════════════════════════════════════════
✅ PUT IN NOTES: [ ] todos, @mentions, reminders, tips, booking links
❌ DON'T PUT IN NOTES: activity descriptions, things to see, timelines (make separate bookings instead)

═══════════════════════════════════════════════════════════════════
FORMAT:
═══════════════════════════════════════════════════════════════════
TRIP: [Name]
DATES: [Start] - [End, Year]

DAY 1 - [Date] - [City]
[Time] | [Type] | [Activity] | [Location] | [Platform #Ref] | [Status]
Notes: [Brief logistics, todos, @mentions only]

...more days...

KEY_INSIGHTS:
[{"icon": "emoji", "text": "insight"}, ...]

Types: Flight, Hotel, Tour, Dining, Transport, Spa, Ferry
Status: Confirmed, Pending, Optional, Cancelled

═══════════════════════════════════════════════════════════════════
KEY_INSIGHTS (REQUIRED AT END):
═══════════════════════════════════════════════════════════════════
After all days, add KEY_INSIGHTS as a JSON array with 5-8 insights about the trip.
Each insight has "icon" (emoji) and "text" (brief insight).

Include insights about:
- 🎯 Trip theme/highlights (e.g., "Island hopping adventure")
- 📸 Best photo opportunities
- 🎂 Special occasions (birthdays, anniversaries)
- 🌤️ Weather/season tips
- 💰 Budget tips
- 🏛️ Cultural notes/local customs
- 🎒 Packing suggestions
- ⚡ Pro tips

═══════════════════════════════════════════════════════════════════
EXAMPLE - Dense itinerary properly split:
═══════════════════════════════════════════════════════════════════
INPUT: "Day 1 Paris - Arrive 10:25, RER to hotel, lunch at veg place, 2:30 bike tour, 7:30 birthday dinner at Les Ombres"

OUTPUT:
DAY 1 - Apr 18, 2026 - Paris
10:25 AM | Flight | Arrive CDG Airport | Paris CDG | — | Confirmed
Notes: Take RER B + Line 1 to hotel
12:30 PM | Hotel | Check-in Gare de Lyon | Near Gare de Lyon | — | Confirmed
1:30 PM | Dining | Lunch at La Pause Verte | Paris | — | Confirmed
Notes: Vegetarian restaurant
2:30 PM | Tour | Bike Tour Right Bank | Trocadéro, Paris | — | Confirmed
Notes: ~8 km route via Eiffel Tower
7:30 PM | Dining | Birthday Dinner at Les Ombres | Eiffel Tower terrace | — | Confirmed
Notes: ⭐ Special occasion

KEY_INSIGHTS:
[{"icon": "🎂", "text": "Birthday celebration trip - special dinner at Les Ombres with Eiffel Tower views"},
{"icon": "📸", "text": "Best Eiffel Tower photos from Trocadéro plaza at sunset"},
{"icon": "🚴", "text": "Bike tour along Seine - scenic 8km route through historic Paris"},
{"icon": "🥗", "text": "La Pause Verte great for vegetarian options in meat-heavy Paris"},
{"icon": "🎫", "text": "Book Eiffel Tower tickets 2 weeks ahead to avoid long queues"},
{"icon": "💳", "text": "Metro tickets cheaper in carnets of 10 - get at any station"}]

---
[PASTE YOUR ITINERARY HERE]"""

            # Use streamlit-extras or pyperclip for clipboard
            import streamlit.components.v1 as components

            # Create copy button with HTML/JS component - prompt is HIDDEN
            copy_button_html = f"""
                <div id="copy-container">
                    <button id="copy-btn" style="
                        background-color: #4CAF50;
                        color: white;
                        padding: 10px 20px;
                        border: none;
                        border-radius: 12px;
                        cursor: pointer;
                        font-size: 14px;
                        font-weight: 500;
                        margin-bottom: 20px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        transition: all 0.2s;
                    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.15)';"
                       onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)';">
                        📋 Copy Prompt
                    </button>
                    <textarea id="prompt-text" style="position: absolute; left: -9999px; opacity: 0;">{prompt_text}</textarea>
                </div>
                <script>
                    document.getElementById('copy-btn').addEventListener('click', function() {{
                        var textArea = document.getElementById('prompt-text');
                        textArea.select();
                        document.execCommand('copy');
                        this.textContent = '✅ Copied!';
                        this.style.backgroundColor = '#2196F3';
                        setTimeout(() => {{
                            this.textContent = '📋 Copy Prompt';
                            this.style.backgroundColor = '#4CAF50';
                        }}, 2000);
                    }});
                </script>
            """

            components.html(copy_button_html, height=60)

            # Main textarea - auto-format if messy text detected
            itinerary_input = st.text_area(
                "Paste Your Itinerary:",
                value=st.session_state.get('formatted_itinerary', ''),
                height=350,
                placeholder="TRIP: Thailand Adventure\nDATES: Dec 22 - Dec 28, 2025\n\nDAY 1 - Dec 22, 2025 - Phuket\n2:00 PM | Hotel | Grand Supicha | 48 Narisorn | Booking.com #6450 | Confirmed",
                key="itinerary_text"
            )

            # Auto-format detection: if text doesn't follow format, auto-format it silently
            if itinerary_input and not itinerary_input.startswith("TRIP:") and len(itinerary_input) > 50:
                # Only auto-format once per text input (avoid infinite loops)
                if st.session_state.get('last_raw_input') != itinerary_input:
                    st.session_state.last_raw_input = itinerary_input
                    with st.spinner("🪄 Auto-formatting your itinerary..."):
                        try:
                            api_key = "92133f6e-fe42-435f-9a86-29d2738a5582"
                            formatted = format_with_ai(itinerary_input, api_key, "Hyperspace AI")
                            st.session_state.formatted_itinerary = formatted
                            st.success("✅ Auto-formatted!")
                            st.rerun()
                        except Exception as e:
                            error_msg = str(e)
                            # Show more specific error messages
                            if "Connection" in error_msg or "timeout" in error_msg.lower():
                                st.warning(f"⚠️ Auto-format timeout. The AI service is slow. Use 'Copy Prompt' button to manually format with ChatGPT/Claude instead.")
                            elif "API" in error_msg or "401" in error_msg or "403" in error_msg:
                                st.warning(f"⚠️ API key issue. Use 'Copy Prompt' button to manually format with ChatGPT/Claude instead.")
                            else:
                                st.warning(f"⚠️ Auto-format failed: {error_msg}. Use 'Copy Prompt' button to manually format with ChatGPT/Claude.")
                            # Don't block the user - let them proceed with unformatted text
            search_input = itinerary_input
            search_label = None
            search_query = None

        # For Demo Mode and Paste Itinerary, use defaults (will be overridden by data)
        start_date = datetime(2025, 5, 10)
        end_date = datetime(2025, 5, 20)
        trip_name = "My Trip"

        st.markdown("---")

        if st.button("🚀 Generate Itinerary", type="primary", use_container_width=True):
            if search_method == "Demo Mode" or (search_method == "Paste Itinerary" and search_input):
                st.session_state.trip_data = None

                # Demo mode - load sample data
                if search_method == "Demo Mode":
                    with st.spinner("Loading demo data..."):
                        try:
                            with open('itinerary.json', 'r') as f:
                                sample_data = json.load(f)

                            # Convert sample data to app format
                            days_dict = sample_data.get('days', {})
                            unassigned_list = sample_data.get('unassigned', [])

                            # Use dates and name from JSON file, with smart fallback to calculate from days
                            demo_trip_name = sample_data.get('trip_name', 'My Trip')

                            # Calculate dates from days dictionary if not provided
                            if days_dict:
                                sorted_days = sorted(days_dict.keys())
                                first_day = datetime.strptime(sorted_days[0], '%Y-%m-%d')
                                last_day = datetime.strptime(sorted_days[-1], '%Y-%m-%d')
                                default_start = first_day.strftime('%B %d, %Y')
                                default_end = last_day.strftime('%B %d, %Y')
                            else:
                                default_start = 'May 10, 2025'
                                default_end = 'May 20, 2025'

                            demo_start_date = sample_data.get('start_date', default_start)
                            demo_end_date = sample_data.get('end_date', default_end)

                            st.session_state.trip_data = {
                                'trip_name': demo_trip_name,
                                'search_term': 'Demo Data',
                                'start_date': demo_start_date,
                                'end_date': demo_end_date,
                                'days': days_dict,
                                'unassigned': unassigned_list,
                                'total_bookings': sum(len(d.get('bookings', [])) for d in days_dict.values()) + len(unassigned_list),
                                'total_days': len(days_dict)
                            }
                            st.success("✅ Demo data loaded!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error loading demo data: {str(e)}")

                # Paste Itinerary mode
                elif search_method == "Paste Itinerary":
                    with st.spinner("Parsing itinerary..."):
                        try:
                            # Try to parse as JSON first
                            try:
                                pasted_data = json.loads(search_input)
                                days_dict = pasted_data.get('days', {})
                                unassigned_list = pasted_data.get('unassigned', [])

                                st.session_state.trip_data = {
                                    'trip_name': pasted_data.get('trip_name', trip_name),
                                    'search_term': 'Pasted Itinerary',
                                    'start_date': pasted_data.get('start_date', start_date.strftime('%b %d, %Y')),
                                    'end_date': pasted_data.get('end_date', end_date.strftime('%b %d, %Y')),
                                    'days': days_dict,
                                    'unassigned': unassigned_list,
                                    'total_bookings': sum(len(d.get('bookings', [])) for d in days_dict.values()) + len(unassigned_list),
                                    'total_days': len(days_dict)
                                }
                                st.success("✅ Itinerary loaded from JSON!")
                                st.rerun()
                            except json.JSONDecodeError:
                                # Not JSON, try parsing as structured text
                                from text_parser import parse_text_itinerary

                                parsed_data = parse_text_itinerary(search_input)
                                days_dict = parsed_data.get('days', {})

                                if not days_dict:
                                    st.error("❌ Could not parse itinerary. Please check the format.")
                                    st.info("""💡 **Tip:** Use "📋 Copy Prompt" button above to structure your itinerary correctly.

Your itinerary must follow this format:

**TRIP:** [Trip Name]
**DATES:** [Month Day] - [Month Day, Year]

**DAY 1 - [Month Day, Year] - [Location]**
[Time] | [Type] | [Activity] | [Address] | [Platform #Ref] | [Status]
Notes: [Your personal notes and insights]
                                    """)
                                    st.stop()
                                else:
                                    # Get key_insights from parsed data if available
                                    key_insights = parsed_data.get('key_insights', [])

                                    st.session_state.trip_data = {
                                        'trip_name': parsed_data.get('trip_name', trip_name),
                                        'search_term': 'Pasted Itinerary',
                                        'start_date': parsed_data.get('start_date', start_date.strftime('%b %d, %Y')),
                                        'end_date': parsed_data.get('end_date', end_date.strftime('%b %d, %Y')),
                                        'days': days_dict,
                                        'unassigned': [],
                                        'total_bookings': sum(len(d.get('bookings', [])) for d in days_dict.values()),
                                        'total_days': len(days_dict),
                                        'key_insights': key_insights
                                    }

                                    # If we have AI-generated insights, store them in session state
                                    if key_insights:
                                        st.session_state.custom_insights = key_insights

                                    st.success("✅ Itinerary parsed from text format!")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error parsing itinerary: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
            else:
                st.warning("Please enter your itinerary text")
                st.warning("Enter a label or keywords to search")

        st.markdown("---")
        st.caption("Powered by Gmail API")

    # Main content
    if st.session_state.trip_data:
        trip = st.session_state.trip_data

        # Header with editable trip name
        col1, col2 = st.columns([3, 1])
        with col1:
            # Make trip name editable inline
            if 'editing_trip_name' not in st.session_state:
                st.session_state.editing_trip_name = False

            if st.session_state.editing_trip_name:
                # Show text input
                new_name = st.text_input(
                    "Trip Name",
                    value=trip["trip_name"],
                    key="trip_name_editor",
                    label_visibility="collapsed",
                    placeholder="Enter trip name..."
                )

                # Update if changed
                if new_name and new_name != trip["trip_name"]:
                    trip["trip_name"] = new_name
                    st.session_state.trip_data = trip
                    st.session_state.editing_trip_name = False
                    st.rerun()

                # Done button below
                if st.button("✓ Done", key="done_editing_trip_name", help="Finish editing"):
                    st.session_state.editing_trip_name = False
                    st.rerun()
            else:
                # Show trip name with inline edit button using columns
                title_col, btn_col, spacer_col = st.columns([4, 0.3, 5.7])

                with title_col:
                    st.markdown(f'''
                    <h1 style="margin: 0; padding: 0; color: #4A7C9E !important; font-weight: 700; line-height: 1.2;">{trip["trip_name"]}</h1>
                    ''', unsafe_allow_html=True)

                with btn_col:
                    if st.button("✏️", key="edit_trip_name_btn", help="Click to edit trip name"):
                        st.session_state.editing_trip_name = True
                        st.rerun()

                with spacer_col:
                    st.empty()

            # Date subtitle below
            st.markdown(f'<p style="color: #8B7B68; font-size: 1.1rem; margin-top: 5px; margin-bottom: 8px;">{trip["start_date"]} → {trip["end_date"]}</p>', unsafe_allow_html=True)

            # Generate city route from days data
            days_dict = trip.get('days', {})
            if days_dict:
                # Get unique cities in order, preserving sequence
                city_route = []
                for day_key in sorted(days_dict.keys()):
                    day = days_dict[day_key]
                    city = day.get('location_display', day.get('location', ''))
                    # Clean up city name - take first part if it has arrows or commas
                    if city:
                        city = city.split('→')[0].split(',')[0].strip()
                        # Only add if different from last city (avoid duplicates)
                        if not city_route or city_route[-1] != city:
                            city_route.append(city)

                if city_route:
                    route_html = ' <span style="color: #4A90A4;">→</span> '.join(
                        [f'<span style="color: #5a5a5a;">{city}</span>' for city in city_route]
                    )
                    st.markdown(f'<p style="font-size: 0.95rem; margin-top: 0; margin-bottom: 20px; line-height: 1.5;">🗺️ {route_html}</p>', unsafe_allow_html=True)

        with col2:
            # Clean button row - 3 buttons only
            btn_col1, btn_col2, btn_col3 = st.columns(3)

            with btn_col1:
                # Calendar Export button
                if st.button("📅 Calendar", key="calendar_btn", help="Export to calendar"):
                    show_calendar_export_dialog(trip)

            with btn_col2:
                # Google Calendar button - using Streamlit's native button with JavaScript redirect
                gcal_link = generate_google_calendar_link(trip, mode='block')
                if gcal_link and st.button("📆 Google", key="google_cal_btn", help="Add to Google Calendar"):
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={gcal_link}">', unsafe_allow_html=True)
                    st.components.v1.html(f'<script>window.open("{gcal_link}", "_blank");</script>', height=0)

            with btn_col3:
                # Export PDF button
                if st.button("📤 Export", key="export_btn", help="Export PDF"):
                    st.session_state.show_export_dialog = True
                    show_export_dialog(trip)

        # Main 2-column layout: Left (Overview + Insights + Map) | Right (Action Required + Day-by-Day)
        left_col, right_col = st.columns([1.2, 1], gap="large")

        with left_col:
            # Trip Overview - with container styling via CSS
            st.markdown("#### Trip Overview")
            stat_cols = st.columns(4)
            with stat_cols[0]:
                st.metric("Days", trip['total_days'])
            with stat_cols[1]:
                st.metric("Bookings", trip['total_bookings'])
            with stat_cols[2]:
                # Count unique locations
                locations = set()
                for day in trip['days'].values():
                    if day.get('location'):
                        locations.add(day['location'])
                st.metric("Destinations", len(locations))
            with stat_cols[3]:
                st.metric("Unassigned", len(trip.get('unassigned', [])))

            st.markdown("---")

            st.markdown("### Key Insights")

            # Check if custom insights exist in session state
            if 'custom_insights' not in st.session_state:
                st.session_state.custom_insights = None

            # Show button to get web-based insights (left aligned)
            if st.button("🌐 Get Real-Time Insights", key="get_web_insights_btn", help="Get current weather, prices, and tips"):
                st.session_state.show_insights_prompt = True

            if st.session_state.custom_insights:
                if st.button("↩️ Use Default Insights", key="reset_insights_btn"):
                    st.session_state.custom_insights = None
                    st.rerun()

            # Show prompt in expander if requested
            if 'show_insights_prompt' in st.session_state and st.session_state.show_insights_prompt:
                with st.expander("Copy Prompt for AI", expanded=True):
                    prompt = generate_web_insights_prompt(trip)
                    st.markdown("**Instructions:**")
                    st.markdown("1. Click 'Copy Prompt' button below")
                    st.markdown("2. Paste into ChatGPT or Claude")
                    st.markdown("3. Copy the JSON response")
                    st.markdown("4. Paste below and click Load")

                    # Copy button using HTML component - Fixed with proper JS-based value setting
                    # Escape the prompt properly for JavaScript string
                    escaped_prompt = prompt.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

                    copy_button_html = f"""
                        <div id="copy-insights-container">
                            <button id="copy-insights-btn" style="
                                background-color: #4CAF50;
                                color: white;
                                padding: 10px 20px;
                                border: none;
                                border-radius: 12px;
                                cursor: pointer;
                                font-size: 14px;
                                font-weight: 500;
                                margin: 10px 0 20px 0;
                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                transition: all 0.2s;
                            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 8px rgba(0,0,0,0.15)';"
                               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 2px 4px rgba(0,0,0,0.1)';">
                                Copy Prompt
                            </button>
                            <textarea id="insights-prompt-text" style="position: absolute; left: -9999px; opacity: 0;"></textarea>
                        </div>
                        <script>
                            (function() {{
                                var promptText = '{escaped_prompt}';
                                var textArea = document.getElementById('insights-prompt-text');
                                textArea.value = promptText;

                                document.getElementById('copy-insights-btn').addEventListener('click', function() {{
                                    // Try modern clipboard API first
                                    if (navigator.clipboard && navigator.clipboard.writeText) {{
                                        navigator.clipboard.writeText(promptText).then(function() {{
                                            updateButtonState();
                                        }}).catch(function() {{
                                            fallbackCopy();
                                        }});
                                    }} else {{
                                        fallbackCopy();
                                    }}

                                    function fallbackCopy() {{
                                        textArea.select();
                                        textArea.setSelectionRange(0, 99999);
                                        document.execCommand('copy');
                                        updateButtonState();
                                    }}

                                    function updateButtonState() {{
                                        var btn = document.getElementById('copy-insights-btn');
                                        btn.textContent = 'Copied!';
                                        btn.style.backgroundColor = '#2196F3';
                                        setTimeout(function() {{
                                            btn.textContent = 'Copy Prompt';
                                            btn.style.backgroundColor = '#4CAF50';
                                        }}, 2000);
                                    }}
                                }});
                            }})();
                        </script>
                    """

                    components.html(copy_button_html, height=70)

                    # Text area to paste custom insights JSON
                    custom_json = st.text_area(
                        "Paste AI Response (JSON):",
                        height=150,
                        placeholder='[{"icon": "🌤️", "text": "..."}, ...]'
                    )

                    if st.button("✅ Load Custom Insights"):
                        try:
                            custom_insights = json.loads(custom_json)
                            if isinstance(custom_insights, list):
                                st.session_state.custom_insights = custom_insights
                                st.session_state.show_insights_prompt = False
                                st.success("✅ Custom insights loaded!")
                                st.rerun()
                            else:
                                st.error("Invalid format. Expected JSON array.")
                        except json.JSONDecodeError:
                            st.error("Invalid JSON. Please check the format.")

            # Use custom insights if available, otherwise generate default
            if st.session_state.custom_insights:
                all_insights = st.session_state.custom_insights
            else:
                all_insights = generate_insights(trip)

            top_insights = get_top_insights(all_insights, count=5)
            remaining_insights = get_remaining_insights(all_insights, skip=5)

            # Display top insights
            for insight in top_insights:
                col1, col2 = st.columns([0.08, 0.92])
                with col1:
                    st.markdown(insight['icon'])
                with col2:
                    st.markdown(insight['text'])

            # Show more insights in expander
            if remaining_insights:
                with st.expander(f"➕ Show {len(remaining_insights)} more insight{'s' if len(remaining_insights) > 1 else ''}"):
                    for insight in remaining_insights:
                        col1, col2 = st.columns([0.08, 0.92])
                        with col1:
                            st.markdown(insight['icon'])
                        with col2:
                            st.markdown(insight['text'])

            st.markdown("---")

        with right_col:
            # Action Required section at the top (only show if there are issues)
            issues = detect_booking_issues(trip)

            if issues:
                st.markdown("### Action Required")

                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ffe8e8 0%, #ffeded 100%);
                     border: none;
                     border-radius: 12px;
                     padding: 12px;
                     margin-bottom: 12px;">
                    <div style="color: #868e96; font-size: 13px;">{len(issues)} booking issue{"s" if len(issues) > 1 else ""} found. Click cards to jump to day.</div>
                </div>
                """, unsafe_allow_html=True)

                # Show issue details as clickable cards with full text, left-aligned
                issues_to_show = issues[:3] if len(issues) > 3 else issues

                # Add CSS to style buttons as cards with text truncation
                st.markdown("""
                <style>
                .issue-card-button button {
                    width: 100% !important;
                    text-align: left !important;
                    padding: 10px 14px !important;
                    background: rgba(255, 255, 255, 0.9) !important;
                    border: 1px solid rgba(0, 0, 0, 0.08) !important;
                    border-radius: 18px !important;
                    backdrop-filter: blur(10px) !important;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
                    font-family: 'SF Pro Display', -apple-system, sans-serif !important;
                    margin-bottom: 2px !important;
                    cursor: pointer !important;
                    transition: all 0.2s ease !important;
                    color: #1d1d1f !important;
                    white-space: nowrap !important;
                    line-height: 1.4 !important;
                    height: 50px !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    font-size: 13px !important;
                }
                .issue-card-button button:hover {
                    transform: translateY(-2px) !important;
                    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12) !important;
                }
                .issue-card-button button p {
                    margin: 0 !important;
                    padding: 0 !important;
                    overflow: hidden !important;
                    text-overflow: ellipsis !important;
                    white-space: nowrap !important;
                }
                .issue-card-button {
                    margin: 0 !important;
                    padding: 0 !important;
                }
                /* Remove default Streamlit button container spacing */
                .issue-card-button .stButton {
                    margin: 0 !important;
                    padding: 0 !important;
                    gap: 0 !important;
                }
                .issue-card-button [data-testid="stVerticalBlock"] {
                    gap: 0 !important;
                }
                .issue-card-button div[data-testid="column"] {
                    padding: 0 !important;
                }
                /* Fix Streamlit emotion cache container gap ONLY within action required cards */
                .issue-card-button .st-emotion-cache-wfksaw {
                    gap: 0.5rem !important;
                }
                .issue-card-button [class*="st-emotion-cache"] {
                    gap: 0.5rem !important;
                }
                </style>
                """, unsafe_allow_html=True)

                for idx, issue in enumerate(issues_to_show):
                    day_num = issue.get('day_num', 'N/A')
                    booking_name = issue.get('booking_name', 'Unknown')
                    issue_text = issue.get('issue', '')
                    day_key = issue.get('day_key', None)

                    # Truncate booking name if too long
                    if len(booking_name) > 20:
                        booking_name_short = booking_name[:20] + "..."
                    else:
                        booking_name_short = booking_name

                    # Calculate remaining space for issue text
                    # Header is roughly: "⚠️ Day X • BookingName • "
                    header_length = len(f"⚠️ Day {day_num} • {booking_name_short} • ")
                    # Total chars that fit in the width: ~60 chars at 13px font
                    max_total_chars = 60
                    remaining_chars = max_total_chars - header_length

                    # Truncate issue text to fit remaining space
                    if remaining_chars > 10:  # Only show if we have at least 10 chars
                        if len(issue_text) > remaining_chars:
                            issue_text_short = issue_text[:remaining_chars].strip() + "..."
                        else:
                            issue_text_short = issue_text
                    else:
                        issue_text_short = ""  # No space left for issue text

                    # Create button content with truncated text on same line
                    if issue_text_short:
                        button_content = f"⚠️ Day {day_num} • {booking_name_short} • {issue_text_short}"
                    else:
                        button_content = f"⚠️ Day {day_num} • {booking_name_short}"

                    # Wrap button in div with class for styling
                    st.markdown('<div class="issue-card-button">', unsafe_allow_html=True)

                    if st.button(
                        button_content,
                        key=f"action_card_{idx}_{day_key}",
                        use_container_width=True
                    ):
                        st.session_state.jump_to_day = day_key
                        st.session_state.view_mode = 'map'
                        st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

                if len(issues) > 3:
                    with st.expander(f"➕ Show {len(issues) - 3} more issue{'s' if len(issues) - 3 > 1 else ''}"):
                        for idx_more, issue in enumerate(issues[3:], start=3):
                            day_num = issue.get('day_num', 'N/A')
                            booking_name = issue.get('booking_name', 'Unknown')
                            issue_text = issue.get('issue', '')
                            day_key = issue.get('day_key', None)

                            full_text = f"⚠️ Day {day_num} • {booking_name}\n{issue_text}"

                            if st.button(
                                full_text,
                                key=f"action_req_issue_card_more_{idx_more}",
                                help=f"Click to jump to Day {day_num}",
                                use_container_width=True
                            ):
                                st.session_state.jump_to_day = day_key
                                st.session_state.view_mode = 'map'
                                st.rerun()

                st.markdown("---")

            # Empty placeholder to align with left column
            st.markdown("")

        # View toggle buttons (outside columns, full width)
        # Use very small columns with minimal gap to keep buttons close together
        view_col1, view_col2, view_col3 = st.columns([0.8, 0.8, 4.4])
        with view_col1:
            if st.button("🗺️ Map View", use_container_width=True, type="primary" if st.session_state.view_mode == 'map' else "secondary"):
                st.session_state.view_mode = 'map'
                st.rerun()
        with view_col2:
            if st.button("🎨 Journey View", use_container_width=True, type="primary" if st.session_state.view_mode == 'journey' else "secondary"):
                st.session_state.view_mode = 'journey'
                st.rerun()
        with view_col3:
            st.markdown("")  # Empty space

        st.markdown("")

        # Render based on view mode
        if st.session_state.view_mode == 'map':
            # Second row: Map and (Action Required + Day-by-Day) side by side
            map_col, daylist_col = st.columns([1.2, 1], gap="large")

            with map_col:
                # Map heading
                st.markdown("### Zoomed Out Places View")

                # Map
                location_sequence = []
                for day_key in sorted(trip['days'].keys()):
                    loc = trip['days'][day_key].get('location')
                    if loc and (not location_sequence or location_sequence[-1] != loc):
                        location_sequence.append(loc)

                m = create_map(location_sequence)
                st_folium(m, width=None, height=500)

            with daylist_col:
                # Day-by-Day Itinerary in right column
                render_day_by_day_view(trip)

        else:  # journey view
            render_illustrative_view(trip)

        # Warning if all bookings are unassigned (moved outside columns, full width)
        assigned_count = sum(len(day.get('bookings', [])) for day in trip['days'].values())
        unassigned_count = len(trip.get('unassigned', []))

        if assigned_count == 0 and unassigned_count > 0:
            st.error(f"""
            **All {unassigned_count} bookings are unassigned!**

            This usually means:
            - Your **date range** doesn't match the booking dates
            - Check the "Unassigned Bookings" section below to see the detected dates

            **Your selected range:** {trip['start_date']} to {trip['end_date']}
            """)

    else:
        # Welcome screen
        st.markdown("## Welcome to Trip Visualizer")
        st.markdown("Transform your travel itinerary into a beautiful visual journey with maps, timelines, and insights.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            ### 🎯 Demo Mode
            Explore a sample Thailand trip
            - Pre-loaded itinerary
            - Interactive maps and timeline
            - See all features in action
            """)
        with col2:
            st.markdown("""
            ### ✍️ Paste Itinerary
            Add your own trip
            - Copy/paste your itinerary text
            - AI-powered formatting available
            - Works with any destination
            """)

        st.info("👈 Use the sidebar to get started: Choose Demo Mode or Paste your own itinerary")

        # Demo map
        st.markdown("### Preview")
        demo_map = create_map(['rome', 'florence', 'venice', 'milan'])
        st_folium(demo_map, width=None, height=400)


if __name__ == "__main__":
    main()
