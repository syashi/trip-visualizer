#!/bin/bash

# Initialize git
git init

# Add all files
git add .

# Commit
git commit -m "Major update v2.0: Smart worldwide geocoding and streamlined interface

✨ Features:
- Smart geocoding for ANY location worldwide using OpenStreetMap
- Journey View shows exact location markers for each booking
- AI auto-formatting with copy prompt buttons
- Simplified interface: Demo Mode + Paste Itinerary only

🎨 UI Improvements:
- Changed 'Search Your Trip' to 'Add Your Trip'
- Removed Label and Keywords options
- SF Pro typography with modern glassy design
- Fixed card spacing (0.5rem for action cards only)

📍 Locations:
- Added California locations (Mendocino, Albion, Fort Bragg, Sonoma)
- Two-tier lookup: cache + OpenStreetMap API
- Works for any city worldwide

📚 Documentation:
- New PROJECT_OVERVIEW.md with project gist
- Enhanced README.md with architecture details
- Deployment instructions

🐛 Bug Fixes:
- Fixed icon font rendering
- Fixed text visibility in textareas
- Fixed column spacing (scoped CSS properly)
- Better API error messages"

# Add remote
git remote add origin https://github.com/syashi/trip-visualize.git

# Rename branch to main
git branch -M main

# Push to GitHub
git push -u origin main

echo ""
echo "✅ Pushed to GitHub: https://github.com/syashi/trip-visualize"
echo ""
