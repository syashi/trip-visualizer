#!/bin/bash

# Trip Visualizer - Git Commit and Push Script
# Run this to commit all changes and push to GitHub

cd "/Users/I751761/Documents/WORK/Trip visualizer/Code base_tripvisualizer"

# Initialize git if not already done
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
fi

# Add all files
echo "Adding files to git..."
git add .

# Create comprehensive commit
echo "Creating commit..."
git commit -m "Major update v2.0: Smart worldwide geocoding, modern UI, and streamlined interface

✨ New Features:
- Smart worldwide geocoding using OpenStreetMap Nominatim API
- Auto-geocodes ANY city/location globally (not limited to pre-defined list)
- Journey View now shows exact location markers for each booking
- AI auto-formatting integration (optional, Hyperspace AI)
- Copy Prompt buttons for easy manual AI formatting
- Session-based location caching for performance

🎨 UI/UX Improvements:
- Changed 'Search Your Trip' to 'Add Your Trip'
- Removed Label and Keywords search options (simplified interface)
- SF Pro typography with modern glassy design
- Fixed card spacing with 0.5rem gap for action cards only
- Text areas now have visible black/grey text
- Compact action required cards with smart text truncation
- Better error messages for API failures

📍 Location Enhancements:
- Added California locations (Mendocino, Albion, Fort Bragg, Little River, Sonoma)
- Added Alaska locations to text parser
- Two-tier location lookup: cache → API
- Handles complex location strings (e.g., 'Mendocino / Albion / Fort Bragg')

📚 Documentation:
- New PROJECT_OVERVIEW.md with comprehensive project gist
- Enhanced README.md with technical architecture and competitive analysis
- Updated Streamlit app config with better descriptions
- Added use cases and target audience analysis

🐛 Bug Fixes:
- Fixed icon font rendering issues (SF Pro not affecting Material Icons)
- Fixed text visibility in paste itinerary textarea
- Fixed action card spacing (scoped CSS to not affect global columns)
- Fixed Journey View to geocode exact activity locations
- Improved API timeout handling (60 seconds for geocoding)
- Fixed column gap issue affecting entire app

🔧 Technical Improvements:
- Smart geocoding with OpenStreetMap Nominatim
- Automatic icon assignment based on location type
- Better error handling with specific messages
- Enhanced text parser for multi-location days
- Removed Gmail search functionality (simplified to paste-only)

Version: 2.0
License: MIT
Built for travelers worldwide 🌍"

# Check if remote exists
if ! git remote | grep -q "origin"; then
    echo ""
    echo "⚠️  No remote repository found!"
    echo ""
    echo "Please run ONE of these commands to add your GitHub repository:"
    echo ""
    echo "Option 1 - If you already created a repo on GitHub:"
    echo "git remote add origin https://github.com/YOUR_USERNAME/trip-visualizer.git"
    echo ""
    echo "Option 2 - Using GitHub CLI (if installed):"
    echo "gh repo create trip-visualizer --public --source=. --remote=origin"
    echo ""
    echo "Then run: git push -u origin main"
    echo ""
else
    # Push to GitHub
    echo "Pushing to GitHub..."

    # Get current branch name
    BRANCH=$(git branch --show-current)

    # If no branch (first commit), use main
    if [ -z "$BRANCH" ]; then
        git branch -M main
        BRANCH="main"
    fi

    # Push to remote
    git push -u origin $BRANCH

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ Successfully pushed to GitHub!"
        echo ""
        echo "Next steps:"
        echo "1. Go to https://share.streamlit.io"
        echo "2. Click 'New app'"
        echo "3. Select your GitHub repository"
        echo "4. Set main file: app.py"
        echo "5. Click 'Deploy'"
        echo ""
    else
        echo ""
        echo "❌ Push failed. Please check the error above."
        echo ""
        echo "Common issues:"
        echo "- Repository doesn't exist on GitHub"
        echo "- Authentication required (run: gh auth login)"
        echo "- Wrong remote URL"
        echo ""
    fi
fi
