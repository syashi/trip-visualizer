# PDF Export Functions

import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
import tempfile
import os
import folium
import base64
from PIL import Image as PILImage

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    import time
    SELENIUM_AVAILABLE = True
    SELENIUM_ERROR = None
except ImportError as e:
    SELENIUM_AVAILABLE = False
    SELENIUM_ERROR = str(e)
except Exception as e:
    SELENIUM_AVAILABLE = False
    SELENIUM_ERROR = str(e)

def create_overview_map(trip_data, location_coords):
    """Create a zoomed-out overview map showing all locations in the trip."""
    if not location_coords:
        return None

    days = trip_data.get('days', {})
    if not days:
        return None

    # Collect all unique locations
    locations = []
    seen = set()

    for day_key in sorted(days.keys()):
        day = days[day_key]
        loc_key = day.get('location')

        if loc_key and loc_key in location_coords and loc_key not in seen:
            loc_data = location_coords[loc_key]
            locations.append({
                'lat': loc_data['lat'],
                'lon': loc_data['lon'],
                'name': loc_data.get('name', loc_key),
                'icon': loc_data.get('icon', '📍'),
                'day_num': day.get('day_num')
            })
            seen.add(loc_key)

    if not locations:
        return None

    # Calculate center and bounds
    lats = [loc['lat'] for loc in locations]
    lons = [loc['lon'] for loc in locations]

    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    # Create map with proper dimensions
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=6,
        width='800px',
        height='600px',
        prefer_canvas=True,
        tiles='OpenStreetMap'
    )

    # Add markers for each location with numbers and names
    for i, loc in enumerate(locations, start=1):
        # Create a custom numbered icon using DivIcon
        folium.Marker(
            [loc['lat'], loc['lon']],
            popup=f"Day {loc['day_num']}: {loc['name']}",
            tooltip=f"{i}. {loc['name']}",
            icon=folium.DivIcon(
                html=f'''
                <div style="
                    background-color: #4A7C9E;
                    color: white;
                    border-radius: 50%;
                    width: 32px;
                    height: 32px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 16px;
                    border: 3px solid white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                ">{i}</div>
                <div style="
                    margin-top: 2px;
                    background-color: white;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: 11px;
                    font-weight: 600;
                    color: #1d1d1f;
                    white-space: nowrap;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.2);
                    text-align: center;
                ">{loc['name']}</div>
            ''',
                icon_size=(100, 60),
                icon_anchor=(50, 30)
            )
        ).add_to(m)

    # Fit bounds to show all markers with extra padding for labels
    if len(locations) > 1:
        m.fit_bounds(
            [[min(lats), min(lons)], [max(lats), max(lons)]],
            padding=[50, 50]  # Extra padding to ensure labels don't get cut off
        )

    return m


def capture_map_screenshot_from_html(html_file_path, width=800, height=600):
    """Capture a screenshot of a folium map HTML file using selenium."""
    if not SELENIUM_AVAILABLE:
        print(f"Selenium not available: {SELENIUM_ERROR}")
        return None

    driver = None
    screenshot_path = None

    try:
        # Create temp file path for screenshot (don't keep file handle open)
        fd, screenshot_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)  # Close immediately so Selenium can write to it

        # Setup Chrome in headless mode
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument(f'--window-size={width},{height}')

        # Create driver (will use system Chrome)
        print(f"Starting Chrome webdriver...")
        driver = webdriver.Chrome(options=chrome_options)
        print(f"Chrome webdriver started successfully")

        # Load the map HTML file using execute_script to avoid timeout
        abs_path = os.path.abspath(html_file_path)
        print(f"Loading map HTML from: {abs_path}")

        # Use data URI to load the HTML content directly
        with open(abs_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # Navigate to blank page first
        driver.get('data:text/html,<html><body>Loading...</body></html>')

        # Then inject the actual HTML
        driver.execute_script(f"document.open(); document.write({repr(html_content)}); document.close();")

        # Wait for map to fully render - tiles need time to load
        print("Waiting for map tiles to load...")
        time.sleep(8)  # Increased to 8 seconds to ensure all tiles load

        # Check if tiles have loaded by looking for tile images
        try:
            tiles_loaded = driver.execute_script("""
                var tiles = document.querySelectorAll('.leaflet-tile');
                var loaded = 0;
                for (var i = 0; i < tiles.length; i++) {
                    if (tiles[i].complete) loaded++;
                }
                return loaded > 0 ? loaded : -1;
            """)
            print(f"Tiles loaded: {tiles_loaded if tiles_loaded > 0 else 'checking...'}")
        except:
            pass

        # Take screenshot
        print(f"Saving screenshot to: {screenshot_path}")
        success = driver.save_screenshot(screenshot_path)

        if not success:
            print(f"driver.save_screenshot returned False")
            if screenshot_path and os.path.exists(screenshot_path):
                os.unlink(screenshot_path)
            return None

        # Verify the screenshot file exists and has content
        if not os.path.exists(screenshot_path):
            print(f"Screenshot file was not created at: {screenshot_path}")
            return None

        file_size = os.path.getsize(screenshot_path)
        if file_size == 0:
            print(f"Screenshot file is empty (0 bytes)")
            os.unlink(screenshot_path)
            return None

        print(f"Screenshot saved successfully ({file_size} bytes)")
        return screenshot_path

    except Exception as e:
        print(f"Error capturing map screenshot: {e}")
        import traceback
        traceback.print_exc()
        # Clean up screenshot file on error
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.unlink(screenshot_path)
            except:
                pass
        return None
    finally:
        # Always quit driver if it was created
        if driver:
            try:
                driver.quit()
            except:
                pass


def create_day_map_for_pdf(day_data, location_coords):
    """Create a Folium map for a specific day with all activity markers."""
    location = day_data.get('location')
    if not location or location not in location_coords:
        return None

    loc_coords = location_coords[location]
    bookings = day_data.get('bookings', [])

    # Calculate bounds
    all_lats = [loc_coords['lat']]
    all_lons = [loc_coords['lon']]

    for idx, booking in enumerate(bookings):
        offset_lat = loc_coords['lat'] + (idx * 0.002)
        offset_lon = loc_coords['lon'] + (idx * 0.002)
        all_lats.append(offset_lat)
        all_lons.append(offset_lon)

    # Create map with specific size for PDF
    m = folium.Map(
        location=[loc_coords['lat'], loc_coords['lon']],
        tiles='OpenStreetMap',
        width='800px',
        height='600px',
        prefer_canvas=True
    )

    # Type colors for numbered markers (no emojis - they render as black squares in PDF)
    type_colors = {
        'hotels': '#4ECDC4',
        'flights': '#FF6B6B',
        'tours': '#FFE66D',
        'activity': '#FFE66D',
        'ferries': '#95E1D3',
        'dining': '#F38181',
        'spa': '#DDA0DD',
        'transport': '#87CEEB',
    }

    # Add markers for each booking
    for idx, booking in enumerate(bookings):
        btype = booking.get('type', 'tours').lower()
        activity_name = booking.get('activity_name', booking.get('subject', 'Activity'))
        marker_color = type_colors.get(btype, '#888888')

        offset_lat = loc_coords['lat'] + (idx * 0.002)
        offset_lon = loc_coords['lon'] + (idx * 0.002)

        # Use numbered markers instead of emojis
        marker_num = idx + 1
        icon_html = f'''
        <div style="background: {marker_color}; color: white; border-radius: 8px;
             width: 36px; height: 36px; display: flex; align-items: center;
             justify-content: center; font-size: 18px; font-weight: bold; border: 3px solid white;
             box-shadow: 0 3px 10px rgba(0,0,0,0.3);">{marker_num}</div>
        '''

        folium.Marker(
            [offset_lat, offset_lon],
            popup=activity_name,
            icon=folium.DivIcon(html=icon_html, icon_size=(38, 38), icon_anchor=(19, 19))
        ).add_to(m)

    # Add center marker with day number
    day_num = day_data.get('day_num', '1')
    center_marker_html = f'''
    <div style="background: linear-gradient(135deg, #4A90A4 0%, #357ABD 100%);
         color: white; border-radius: 50%; width: 50px; height: 50px;
         display: flex; align-items: center; justify-content: center;
         font-weight: bold; font-size: 22px; border: 4px solid white;
         box-shadow: 0 4px 15px rgba(0,0,0,0.4);">{day_num}</div>
    '''

    folium.Marker(
        [loc_coords['lat'], loc_coords['lon']],
        popup=f"Day {day_num}",
        icon=folium.DivIcon(html=center_marker_html, icon_size=(50, 50), icon_anchor=(25, 25))
    ).add_to(m)

    # Fit bounds to show all markers
    if len(all_lats) > 1:
        southwest = [min(all_lats) - 0.003, min(all_lons) - 0.003]
        northeast = [max(all_lats) + 0.003, max(all_lons) + 0.003]
        m.fit_bounds([southwest, northeast], padding=(30, 30))

    # Save map to temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        m.save(f.name)
        return f.name

    return None

def generate_full_journey_pdf(trip_data, location_coords=None):
    """Generate a single PDF with full journey overview."""

    # Debug logging
    print(f"\n=== PDF GENERATION DEBUG ===")
    print(f"SELENIUM_AVAILABLE: {SELENIUM_AVAILABLE}")
    print(f"location_coords provided: {location_coords is not None}")
    if location_coords:
        print(f"location_coords keys: {list(location_coords.keys())}")
    print(f"===========================\n")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1d1d1f'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    story.append(Paragraph(trip_data.get('trip_name', 'My Trip'), title_style))
    story.append(Paragraph(f"{trip_data.get('start_date', '')} → {trip_data.get('end_date', '')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # Track temp files to clean up AFTER doc.build()
    temp_files_to_cleanup = []

    # Add overview map screenshot at the top
    if SELENIUM_AVAILABLE and location_coords:
        try:
            print("Creating overview map for Full Journey PDF...")
            overview_map = create_overview_map(trip_data, location_coords)

            if overview_map:
                # Save map to temp HTML file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    overview_map.save(f.name)
                    map_html_path = f.name
                temp_files_to_cleanup.append(map_html_path)

                print(f"Saved overview map to: {map_html_path}")

                # Capture screenshot
                screenshot_path = capture_map_screenshot_from_html(map_html_path, width=800, height=600)

                if screenshot_path and os.path.exists(screenshot_path):
                    print(f"Overview map screenshot captured successfully")
                    temp_files_to_cleanup.append(screenshot_path)
                    # Add image to PDF
                    img = Image(screenshot_path, width=6*inch, height=4*inch)
                    story.append(Paragraph("<b>Trip Overview Map</b>", styles['Heading2']))
                    story.append(Spacer(1, 0.1*inch))
                    story.append(img)
                    story.append(Spacer(1, 0.3*inch))
                    print("Successfully added overview map to PDF")
                else:
                    print(f"Screenshot not available, skipping map")
                    story.append(Paragraph("<b>Trip Overview</b> (map not available - Selenium/Chrome required)", styles['Heading2']))
                    story.append(Spacer(1, 0.2*inch))

        except Exception as e:
            print(f"Error adding overview map: {e}")
            import traceback
            traceback.print_exc()

    # Add each day
    days = trip_data.get('days', {})
    for day_key in sorted(days.keys()):
        day = days[day_key]

        # Day header
        day_header = f"Day {day['day_num']} • {day.get('location_display', '')} • {day.get('display', '')}"
        story.append(Paragraph(day_header, styles['Heading2']))

        # Map location note
        location = day.get('location_display', 'Location')
        story.append(Paragraph(f"<b>Location:</b> {location}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        # No individual day maps in Full Journey PDF - only overview map at top

        # Bookings
        bookings = day.get('bookings', [])
        for booking in bookings:
            btype = booking.get('type', 'tours').upper()
            name = booking.get('activity_name', booking.get('subject', 'Booking'))
            story.append(Paragraph(f"<b>{btype}:</b> {name}", styles['Normal']))

            # Location
            loc_info = booking.get('location_info', {})
            meeting = loc_info.get('meeting_point', '')
            if meeting:
                story.append(Paragraph(f"<b>Location:</b> {meeting}", styles['Normal']))

            # Time
            time_info = booking.get('time_info', {})
            time_str = time_info.get('start_time', '')
            if time_str:
                story.append(Paragraph(f"<b>Time:</b> {time_str}", styles['Normal']))

            # Notes
            notes = booking.get('notes', '')
            if notes:
                story.append(Paragraph(f"<i>{notes}</i>", styles['Normal']))

            story.append(Spacer(1, 0.1*inch))

        story.append(Spacer(1, 0.3*inch))

    doc.build(story)

    # Clean up all temp files AFTER doc.build() has read them
    for temp_file in temp_files_to_cleanup:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception as e:
            print(f"Warning: Could not clean up temp file {temp_file}: {e}")

    buffer.seek(0)
    return buffer.getvalue()


def generate_day_by_day_pdf(trip_data, location_coords=None):
    """Generate PDF with each day on a separate page."""

    # Debug logging
    print(f"\n=== PDF GENERATION DEBUG (Day-by-Day) ===")
    print(f"SELENIUM_AVAILABLE: {SELENIUM_AVAILABLE}")
    print(f"location_coords provided: {location_coords is not None}")
    if location_coords:
        print(f"location_coords keys: {list(location_coords.keys())}")
    print(f"===========================\n")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Add trip title and overview map at the very top
    title_style = ParagraphStyle(
        'TripTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1d1d1f'),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    story.append(Paragraph(trip_data.get('trip_name', 'My Trip'), title_style))
    story.append(Paragraph(f"{trip_data.get('start_date', '')} → {trip_data.get('end_date', '')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))

    # Track temp files to clean up AFTER doc.build()
    temp_files_to_cleanup = []

    # Add overview map screenshot at the top
    if SELENIUM_AVAILABLE and location_coords:
        try:
            print("Creating overview map for Day-by-Day PDF...")
            overview_map = create_overview_map(trip_data, location_coords)

            if overview_map:
                # Save map to temp HTML file
                with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                    overview_map.save(f.name)
                    map_html_path = f.name
                temp_files_to_cleanup.append(map_html_path)

                print(f"Saved overview map to: {map_html_path}")

                # Capture screenshot
                screenshot_path = capture_map_screenshot_from_html(map_html_path, width=800, height=600)

                if screenshot_path and os.path.exists(screenshot_path):
                    print(f"Overview map screenshot captured successfully")
                    temp_files_to_cleanup.append(screenshot_path)
                    # Add image to PDF
                    img = Image(screenshot_path, width=6*inch, height=4*inch)
                    story.append(Paragraph("<b>Trip Overview Map</b>", styles['Heading2']))
                    story.append(Spacer(1, 0.1*inch))
                    story.append(img)
                    story.append(Spacer(1, 0.4*inch))
                else:
                    print("Overview map screenshot not available, skipping")
                    story.append(Paragraph("<b>Trip Overview</b> (map not available - Chrome/Selenium required)", styles['Heading2']))
                    story.append(Spacer(1, 0.2*inch))

        except Exception as e:
            print(f"Error adding overview map: {e}")
            import traceback
            traceback.print_exc()

    # Add page break before daily details
    story.append(PageBreak())

    days = trip_data.get('days', {})

    for idx, day_key in enumerate(sorted(days.keys())):
        day = days[day_key]

        # Day title
        title_style = ParagraphStyle(
            'DayTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1d1d1f'),
            spaceAfter=20
        )

        day_title = f"Day {day['day_num']} • {day.get('location_display', '')}"
        story.append(Paragraph(day_title, title_style))
        story.append(Paragraph(day.get('display', ''), styles['Normal']))

        # Map location note
        location = day.get('location_display', 'Location')
        story.append(Paragraph(f"<b>Location:</b> {location}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))

        # Add individual day map screenshot with all booking markers
        if SELENIUM_AVAILABLE and location_coords:
            try:
                day_num = day.get('day_num', 1)
                print(f"Creating map for Day {day_num} with all booking markers...")

                # Use create_day_map_for_pdf() to create a map with all booking markers
                # (hotels, tours, ferries, dining, spa, etc.)
                map_html_path = create_day_map_for_pdf(day, location_coords)

                if map_html_path:
                    temp_files_to_cleanup.append(map_html_path)
                    print(f"Capturing Day {day_num} map screenshot...")

                    # Capture screenshot
                    screenshot_path = capture_map_screenshot_from_html(map_html_path, width=800, height=600)

                    if screenshot_path and os.path.exists(screenshot_path):
                        temp_files_to_cleanup.append(screenshot_path)
                        # Add image to PDF
                        img = Image(screenshot_path, width=5*inch, height=3.3*inch)
                        story.append(img)
                        story.append(Spacer(1, 0.2*inch))
                        print(f"Day {day_num} map added to PDF with {len(day.get('bookings', []))} booking markers")
                    else:
                        print(f"Day {day_num} map screenshot not available, skipping")
                else:
                    print(f"Could not create map for Day {day_num} - location not found in coords")

            except Exception as e:
                print(f"Error adding map for Day {day.get('day_num')}: {e}")
                import traceback
                traceback.print_exc()

        story.append(Spacer(1, 0.1*inch))

        # Bookings for this day
        bookings = day.get('bookings', [])
        if bookings:
            for booking in bookings:
                btype = booking.get('type', 'tours').upper()
                name = booking.get('activity_name', booking.get('subject', 'Booking'))

                story.append(Paragraph(f"<b>{btype}</b>", styles['Heading3']))
                story.append(Paragraph(name, styles['Normal']))

                # Location
                loc_info = booking.get('location_info', {})
                meeting = loc_info.get('meeting_point', '')
                if meeting:
                    story.append(Paragraph(f"<b>Location:</b> {meeting}", styles['Normal']))

                # Time
                time_info = booking.get('time_info', {})
                time_str = time_info.get('start_time', '')
                if time_str:
                    story.append(Paragraph(f"<b>Time:</b> {time_str}", styles['Normal']))

                # Booking reference
                ref = booking.get('booking_ref', '')
                if ref and ref != 'ffffff':
                    story.append(Paragraph(f"<b>Ref:</b> {ref}", styles['Normal']))

                # Notes
                notes = booking.get('notes', '')
                if notes:
                    story.append(Paragraph(f"<i>{notes}</i>", styles['Normal']))

                story.append(Spacer(1, 0.2*inch))
        else:
            story.append(Paragraph("No bookings - free day to explore!", styles['Normal']))

        # Add page break except for last page
        if idx < len(days) - 1:
            story.append(PageBreak())

    doc.build(story)

    # Clean up all temp files AFTER doc.build() has read them
    for temp_file in temp_files_to_cleanup:
        try:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        except Exception as e:
            print(f"Warning: Could not clean up temp file {temp_file}: {e}")

    buffer.seek(0)
    return buffer.getvalue()
