# Version 2.1 - Calendar & Share Features

## 🎉 New Features

### 📅 Enhanced Calendar Export (3 Options)
1. **Download .ics file** - Import into any calendar app (Apple Calendar, Outlook, etc.)
2. **Add to Google Calendar** - One-click button opens Google Calendar with all trip events
3. **Complete trip view** - Shows all days, activities, and locations

### 🔗 Share Your Trip
- **Generate shareable links** - Create a URL that contains your entire itinerary
- **One-click copy** - Copy button for easy sharing
- **Direct loading** - Recipients can open the link and see your trip immediately
- **Secure encoding** - Trip data encoded in URL using base64

### 🎨 UI Improvements
- **Compact export dialog** - Reduced width from "medium" to "small"
- **Better button layout** - 3-column layout for Calendar/Google/Export buttons
- **Professional styling** - Google Calendar button uses official Google blue (#4285F4)

## 🔧 Technical Changes

### New Functions
- `generate_google_calendar_link(trip_data)` - Creates Google Calendar add event URL
- `generate_share_link(trip_data)` - Encodes trip data as base64 for URL sharing
- URL parameter handling in `main()` - Loads shared trips from `?trip=` parameter

### New Imports
- `import html` - For HTML escaping shared URLs
- `import urllib.parse` - For URL encoding parameters

### Modified Functions
- `show_export_dialog()` - Changed width from "medium" to "small"
- Button layout section - Replaced 2-column with 3-column + share link section

## 📋 Files Modified
- `app.py` - Main application file (all changes)

## 🚀 Deployment Notes
- No new dependencies required (urllib and html are built-in)
- Share links use the format: `https://trip-visualizer.streamlit.app/?trip=<encoded_data>`
- Google Calendar link creates a single all-day event for the entire trip with booking details

## 🐛 Bug Fixes
- HTML escaping for share URLs to prevent injection issues
- Proper error handling for malformed shared trip URLs

## 📸 What Users Will See
1. **Three buttons in header**: "📅 Download .ics" | "📆 Add to Google" | "📤 Export PDF"
2. **Share link field below**: Text input with shareable URL + "📋 Copy" button
3. **Smaller export dialog**: More compact PDF export options
