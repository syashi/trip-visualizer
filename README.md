# 🗺️ Trip Visualizer

**Transform messy travel plans into beautiful, interactive visual timelines with smart maps and AI-powered insights.**

Built for modern travelers who want to see their entire trip at a glance with rich visualizations and actionable intelligence.

![Trip Visualizer](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## 🎯 What is Trip Visualizer?

Trip Visualizer is a **smart travel itinerary management tool** that automatically converts any travel text (emails, bookings, notes) into:
- 🗺️ **Interactive maps** with exact location markers
- 📅 **Visual timelines** showing your day-by-day journey
- ⚠️ **Action alerts** for booking conflicts and missing details
- 💡 **AI insights** with travel tips and recommendations

**No manual work. No subscriptions. No data harvesting. Just paste and visualize.**

---

## ✨ Key Features

### 🤖 Smart AI Processing
- **AI Auto-Formatting** - Converts messy notes into structured itineraries
- **Text Parsing** - Extracts dates, locations, and booking details automatically
- **Preserves Everything** - Keeps todos, reminders, @mentions, and personal notes intact

### 🌍 Intelligent Location Detection
- **Worldwide Coverage** - Automatically geocodes ANY city/location globally
- **Exact Markers** - Shows precise locations for hotels, restaurants, tours, attractions
- **Smart Routing** - Visualizes your journey path across multiple destinations

### 🗺️ Dual Map Views
- **Map View** - Overview of all destinations with route visualization
- **Journey View** - Day-by-day interactive map with activity-level markers

### ⚠️ Smart Issue Detection
- Identifies missing bookings (e.g., no hotel on Day 3)
- Flags overlapping times (e.g., two activities at same time)
- Alerts for location issues (e.g., missing addresses)
- **Click cards to jump directly to problem bookings**

### ✏️ Fully Editable
- Inline editing of bookings with drag-and-drop reordering
- Add new days, activities, or bookings
- Modify times, locations, and notes
- Real-time updates to map visualizations

### 📄 Export & Share
- **PDF Export** - Two formats (detailed & condensed) with embedded map screenshots
- Share itineraries with travel companions
- Print-ready for offline reference

### 🎨 Beautiful Modern Design
- **SF Pro Typography** - Clean, thin, modern fonts
- **Glassy UI** - Backdrop filters and smooth animations
- **Color-Coded Markers** - Visual distinction for hotels 🏨, flights ✈️, tours 🎫, dining 🍽️, etc.
- **Compact & Responsive** - Optimized spacing and mobile-friendly

---

## 👥 Who is it for?

- **✈️ Organized Travelers** - Visual oversight of pre-booked trips
- **👨‍👩‍👧‍👦 Group Planners** - Coordinate complex multi-day family/friend trips
- **🌎 Digital Nomads** - Plan extended travels with multiple destinations
- **🎒 Travel Enthusiasts** - Optimize itineraries with visual insights
- **💼 Travel Agents** - Create professional itineraries for clients

---

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/trip-visualizer.git
   cd trip-visualizer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app**
   ```bash
   streamlit run app.py
   ```

4. **Open in browser** - Go to `http://localhost:8501`

---

## 🎯 How It Works

1. **📋 Paste Your Itinerary**
   - Copy travel emails, booking confirmations, or structured notes
   - Use "Copy Prompt" button to format with ChatGPT/Claude if needed

2. **🤖 AI Processing**
   - Automatically extracts bookings, dates, and locations
   - Preserves todos, reminders, @mentions, and personal notes
   - Geocodes all locations worldwide (not limited to pre-defined cities)

3. **🗺️ Interactive Visualization**
   - View on interactive maps with exact location markers
   - Switch between Map View (overview) and Journey View (day-by-day)
   - See day-by-day timeline with color-coded booking cards

4. **✏️ Edit & Refine**
   - Modify bookings inline with drag-and-drop
   - Add missing activities or update details
   - Action Required alerts show what needs attention

5. **📄 Export & Share**
   - Generate PDF with embedded map screenshots
   - Share with travel companions or print for offline use

---

## 📝 Itinerary Format

Use this format (or click "Copy Prompt" in the app for AI formatting):

```
TRIP: [Trip Name]
DATES: [Month Day] - [Month Day, Year]

DAY 1 - [Date] - [City]
[Time] | [Type] | [Activity] | [Address] | [Platform #Ref] | [Status]
Notes: [Your insights, todos, reminders, @mentions, meal plans, drive times, links]
[Each insight on new line - with or without [ ] checkboxes]

Types: Hotel, Flight, Tour, Ferry, Dining, Spa
Status: Confirmed, Pending, Optional, Cancelled
```

**Example:**
```
TRIP: California Coast Adventure
DATES: June 19 - June 21, 2025

DAY 1 - June 19, 2025 - Mendocino
1:45 PM | Tour | Skunk Train Pudding Creek Ride | Fort Bragg | Skunk Train | Confirmed
Notes: Park at Fort Bragg station. Arrive 15 mins early.
[ ] Bring camera for scenic views @John

5:00 PM | Tour | Russian Gulch Hike | Russian Gulch State Park | | Optional
Notes: Trail link: https://www.alltrails.com/trail/russian-gulch
Carry snacks: cucumber sandwiches + protein bars

7:30 PM | Hotel | Redwood Retreat Check-in | Albion, CA | | Confirmed
Notes: Confirmation #ABC123. Late check-in OK.

DAY 2 - June 20, 2025 - Little River
11:30 AM | Tour | Kayaking | Van Damme State Park Beach, Little River | | Confirmed
Notes: Meet at white bus with logo. Wear quick-dry clothes.
[ ] SUSU before leaving! @Sarah
```

**What Gets Preserved:**
- ✅ ALL todos and reminders (with or without [ ] checkboxes)
- ✅ @mentions (e.g., @John, @Sarah)
- ✅ Dates in todos
- ✅ Meal plans and drive times
- ✅ Links and URLs (clickable in the app)
- ✅ Personal notes, tips, and ANY unstructured text

---

## 🏗️ Technical Architecture

### Core Components

```
trip-visualizer/
├── app.py                      # Main Streamlit app with UI/UX
├── text_parser.py              # Structured text parsing engine
├── export_pdf_functions.py     # PDF generation with embedded maps
├── insights_generator.py       # AI-powered travel insights
├── web_insights_generator.py   # Web-based insights prompts
├── travel_extractor.py         # Gmail booking extraction (optional)
├── requirements.txt            # Python dependencies
├── packages.txt                # System dependencies (chromium)
└── README.md                   # This file
```

### Key Technologies

- **Streamlit** - Modern web framework for Python
- **Folium** - Interactive Leaflet.js maps
- **OpenStreetMap Nominatim** - Worldwide geocoding (no API key needed)
- **ReportLab** - PDF generation with map screenshots
- **OpenAI SDK** - AI formatting (optional, with Hyperspace AI)

### Smart Geocoding

The app uses intelligent location detection:
1. Checks pre-defined location cache (instant results)
2. Falls back to OpenStreetMap Nominatim API for unknown locations
3. Caches results to avoid repeated API calls
4. Handles complex location strings (e.g., "Mendocino / Albion / Fort Bragg")

This means **it works for ANY location worldwide** - not just major cities.

---

## 🌐 Deploy to Streamlit Cloud

1. Fork this repository to your GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your forked repository
5. Set main file: `app.py`
6. Click "Deploy"

Your app will be live at: `https://your-app-name.streamlit.app`

---

## 💎 Why Trip Visualizer is Great

### For Travelers
- **Saves Time** - No manual map plotting or timeline creation
- **Visual Clarity** - See entire trip layout instantly
- **Error Prevention** - Catches booking conflicts before departure
- **Preserves Context** - Keeps all personal notes and reminders

### For Developers
- **Open Source** - MIT licensed, free to use and modify
- **Extensible** - Easy to add new booking types or features
- **Modern Stack** - Built with latest Python/Streamlit best practices
- **Well Documented** - Clear code structure and comments

### Unique Advantages
1. **Works Everywhere** - Not limited to pre-defined cities
2. **Flexible Input** - Accepts any format (structured text, emails, notes)
3. **Privacy First** - Runs locally, no data sent to external servers (except geocoding)
4. **No Subscriptions** - Completely free, no paywalls
5. **Beautiful UI** - Modern SF Pro design with glassy effects

---

## 📋 Requirements

- Python 3.9+
- Streamlit 1.30+
- Chrome/Chromium (for PDF map screenshots)
- Internet connection (for geocoding and AI formatting)

See `requirements.txt` for complete dependency list.

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- [ ] Add more booking platforms (Expedia, Hotels.com, etc.)
- [ ] Implement calendar sync (Google Calendar, iCal)
- [ ] Add budget tracking and cost visualization
- [ ] Support for multi-traveler itineraries
- [ ] Offline mode with cached maps
- [ ] Mobile app version

Please submit Pull Requests or open Issues for discussion.

---

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Maps powered by [Folium](https://python-visualization.github.io/folium/) & [OpenStreetMap](https://www.openstreetmap.org/)
- Geocoding via [Nominatim](https://nominatim.org/)
- PDF generation with [ReportLab](https://www.reportlab.com/)
- Inspired by modern travelers who deserve better tools

---

## 📞 Support & Contact

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/trip-visualizer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/trip-visualizer/discussions)

---

Made with ❤️ for travelers worldwide
