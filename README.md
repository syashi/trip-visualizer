# 🗺️ Trip Visualizer

Transform your travel itinerary text into a beautiful, interactive visual timeline with maps and smart insights.

![Trip Visualizer](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

## ✨ Features

- 📝 **Text-based Input** - Just paste your travel emails or booking confirmations
- 🤖 **AI Parsing** - Automatically extracts dates, locations, and booking details
- 🗺️ **Interactive Maps** - Multiple view modes with color-coded booking markers
- 📅 **Timeline View** - Chronological day-by-day itinerary
- ✏️ **Editable Cards** - Modify bookings inline with drag-and-drop
- ⚠️ **Issue Detection** - Alerts for missing or overlapping bookings
- 💡 **Smart Insights** - Get tips, weather, and cost info for your destinations
- 📄 **PDF Export** - Two formats with map screenshots
- 🏨 **Multi-booking Types** - Hotels, flights, tours, ferries, dining, spa

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

## 🎯 How It Works

1. **Paste Text** - Copy your travel itinerary (emails, bookings, etc.)
2. **Automatic Parsing** - AI extracts bookings, dates, locations
3. **Visualize** - View on interactive maps and timeline
4. **Edit & Export** - Modify details and export to PDF

## 📋 Requirements

- Python 3.9+
- Streamlit 1.30+
- Chrome/Chromium (for PDF map screenshots)
- See `requirements.txt` for full list

## 🗂️ Project Structure

```
trip-visualizer/
├── app.py                      # Main Streamlit app
├── text_parser.py              # Text parsing logic
├── export_pdf_functions.py     # PDF generation with maps
├── insights_generator.py       # Travel insights generator
├── requirements.txt            # Python dependencies
├── packages.txt                # System dependencies (chromium)
└── README.md                   # Documentation
```

## 🌐 Deploy to Streamlit Cloud

1. Fork this repository to your GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your forked repository
5. Set main file: `app.py`
6. Click "Deploy"

Your app will be live at: `https://your-app-name.streamlit.app`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📝 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Maps powered by [Folium](https://python-visualization.github.io/folium/)
- PDF generation with [ReportLab](https://www.reportlab.com/)

---

Made with ❤️ for travelers
