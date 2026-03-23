# Trip Visualizer

Turn your unstructured travel plans into a beautiful, interactive visual itinerary in minutes.

## Features

- 📋 **Easy Text-Based Input** - Paste structured text itineraries (no JSON required!)
- 🗺️ **Interactive Maps** - See your journey visualized on an interactive map
- 📅 **Day-by-Day View** - Organized timeline with all bookings
- 📤 **PDF Export** - Export full journey or day-by-day PDFs with maps
- 📧 **Gmail Integration** - Automatically extract bookings from emails
- ✏️ **Editable** - Edit bookings, add new activities, modify dates

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

### 2. Create Your Itinerary

**Option A: Use AI to Format (Recommended)**

1. Open `AI_TEXT_CONVERSION_PROMPT.txt`
2. Copy the entire prompt
3. Paste into ChatGPT or Claude
4. Add your messy trip notes at the bottom
5. Copy the AI's structured output
6. Paste into Trip Visualizer

**Option B: Gmail Integration**

1. Set up Gmail API credentials (see `credentials.json`)
2. Label your booking emails in Gmail
3. Use the "Label" search method in the app

**Option C: Try Demo Mode**

1. Select "Demo Mode" in the sidebar
2. Click "Generate Itinerary"
3. Explore the sample Thailand trip

### 3. Text Format

The app accepts this simple text format:

```
TRIP: Thailand Adventure
DATES: Dec 22 - Dec 28, 2025

DAY 1 - Dec 22, 2025 - Phuket
2:00 PM | Hotel | Grand Hotel | 48 Narisorn Road | Booking.com #6450050149 | Confirmed
Notes: Check-in at 2 PM

DAY 2 - Dec 23, 2025 - Phuket
9:30 AM - 4:00 PM | Tour | Phi Phi Snorkeling | Royal Marina | Tripadvisor #TRP12345 | Confirmed
Notes: Bring sunscreen
```

**Format:** `Time | Type | Activity | Location | Platform #Reference | Status`

See `sample_text_itinerary.txt` for a complete example.

## Project Structure

```
├── app.py                          # Main Streamlit application
├── text_parser.py                  # Converts text format to internal JSON
├── travel_extractor.py             # Gmail API integration
├── export_pdf_functions.py         # PDF generation with maps
├── api.py                          # API endpoints
├── itinerary.json                  # Demo data
├── AI_TEXT_CONVERSION_PROMPT.txt   # AI prompt for users
├── QUICK_START.txt                 # Quick reference guide
├── README.txt                      # Detailed user guide
└── sample_text_itinerary.txt       # Example formatted itinerary
```

## Supported Booking Types

- 🏨 Hotels - Hotels, resorts, accommodations
- ✈️ Flights - Air travel
- 🎫 Tours - Tours, activities, excursions, sightseeing
- ⛴️ Ferries - Boats, ferries, water transport
- 🍽️ Dining - Restaurants, food reservations
- 💆 Spa - Spa, massage, wellness

## Supported Locations

Currently optimized for Thailand:
- Phuket
- Krabi
- Koh Samui
- Bangkok
- Phi Phi Islands
- Koh Phangan
- Chiang Mai

## User Documentation

- **`README.txt`** - Complete user guide with step-by-step instructions
- **`QUICK_START.txt`** - Quick reference card
- **`AI_TEXT_CONVERSION_PROMPT.txt`** - AI prompt to structure messy notes

## Requirements

- Python 3.8+
- Streamlit
- Folium (for maps)
- ReportLab (for PDFs)
- Gmail API (optional, for email integration)
- Selenium + ChromeDriver (optional, for PDF map screenshots)

See `requirements.txt` for complete list.

## Gmail API Setup (Optional)

1. Go to Google Cloud Console
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials
5. Download and save as `credentials.json`
6. Run the app and authenticate when prompted

## PDF Export with Maps (Optional)

For map screenshots in PDFs:

```bash
# Install Selenium
pip install selenium

# Install ChromeDriver (macOS)
brew install chromedriver
```

## License

Private project - not for public distribution.

## Support

For questions or issues, check:
- `README.txt` for detailed user instructions
- `QUICK_START.txt` for quick reference
- The in-app help tooltips
