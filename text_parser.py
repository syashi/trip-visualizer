# Text Itinerary Parser
# Converts structured text format to JSON for Trip Visualizer

import re
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional

def parse_text_itinerary(text: str) -> Dict:
    """
    Parse structured text itinerary into JSON format.

    Expected format:
    TRIP: Trip Name
    DATES: Dec 22 - Dec 28, 2025

    DAY 1 - Dec 22, 2025 - Phuket
    2:00 PM | Hotel | Grand Supicha Hotel | 48 Narisorn Road | Booking.com #6450050149 | Confirmed
    Notes: Check-in at 2 PM

    DAY 2 - Dec 23, 2025 - Phuket
    9:30 AM - 4:00 PM | Tour | Phi Phi Snorkeling | Royal Marina | Tripadvisor TRP12345 | Confirmed
    Notes: Bring sunscreen

    KEY_INSIGHTS:
    [{"icon": "emoji", "text": "insight"}, ...]
    """

    lines = text.strip().split('\n')

    # Initialize result structure
    result = {
        'trip_name': 'My Trip',
        'start_date': '',
        'end_date': '',
        'days': {},
        'key_insights': []
    }

    current_day = None
    current_booking = None
    parsing_insights = False
    insights_json_buffer = ""

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Parse trip name
        if line.upper().startswith('TRIP:'):
            result['trip_name'] = line.split(':', 1)[1].strip()
            continue

        # Parse dates
        if line.upper().startswith('DATES:'):
            dates_str = line.split(':', 1)[1].strip()
            result['start_date'], result['end_date'] = parse_date_range(dates_str)
            continue

        # Parse day header (DAY 1 - Dec 22, 2025 - Phuket)
        day_match = re.match(r'^DAY\s+(\d+)\s*[-–]\s*(.+?)\s*[-–]\s*(.+)$', line, re.IGNORECASE)
        if day_match:
            day_num = int(day_match.group(1))
            date_str = day_match.group(2).strip()
            location_display = day_match.group(3).strip()

            # Parse the date
            date_key, display_date = parse_date(date_str)
            location_key = normalize_location(location_display)

            current_day = {
                'day_num': day_num,
                'display': display_date,
                'location': location_key,
                'location_display': location_display,
                'bookings': []
            }
            result['days'][date_key] = current_day
            current_booking = None
            continue

        # Parse booking line (time | type | name | location | ref | status)
        if '|' in line and current_day is not None:
            parts = [p.strip() for p in line.split('|')]

            if len(parts) >= 2:
                time_part = parts[0]
                booking_type = parts[1] if len(parts) > 1 else 'tours'
                activity_name = parts[2] if len(parts) > 2 else 'Activity'
                meeting_point = parts[3] if len(parts) > 3 else ''
                booking_ref = parts[4] if len(parts) > 4 else ''
                status = parts[5] if len(parts) > 5 else 'confirmed'

                # Parse time
                date_key = list(result['days'].keys())[-1] if result['days'] else datetime.now().strftime('%Y-%m-%d')
                start_time, end_time, trip_datetime = parse_time(time_part, date_key)

                # Normalize booking type
                booking_type_normalized = normalize_booking_type(booking_type)

                # Extract booking reference if it contains #
                platform_name = ''
                if '#' in booking_ref:
                    parts = booking_ref.split('#')
                    platform_name = parts[0].strip()
                    booking_ref = parts[1].strip() if len(parts) > 1 else booking_ref
                else:
                    platform_name = booking_ref.strip()
                    booking_ref = ''

                # Get sender from platform name
                sender = extract_sender(platform_name) if platform_name else 'Booking'

                # Build booking object
                booking = {
                    'type': booking_type_normalized,
                    'activity_name': activity_name,
                    'subject': activity_name,
                    'sender': sender,
                    'trip_date': trip_datetime,
                    'booking_ref': booking_ref,
                    'time_info': {
                        'start_time': start_time,
                        'end_time': end_time
                    },
                    'location_info': {
                        'meeting_point': meeting_point
                    },
                    'location': current_day['location'],
                    'links': [],
                    'places': [activity_name] if activity_name else [],
                    'has_pdf': False,
                    'pdf_filenames': [],
                    'status': normalize_status(status),
                    'notes': ''
                }

                # Add hotel-specific fields
                if booking_type_normalized == 'hotels':
                    booking['location_info']['hotel'] = activity_name
                    booking['location_info']['address'] = meeting_point

                current_day['bookings'].append(booking)
                current_booking = booking
            continue

        # Parse notes line (can be multi-line with checkboxes and insights)
        if line.upper().startswith('NOTES:') and current_booking is not None and not parsing_insights:
            notes_content = line.split(':', 1)[1].strip()
            current_booking['notes'] = notes_content
            continue

        # Parse KEY_INSIGHTS section - accept both KEY_INSIGHTS: and KEY_INSIGHTS (with or without colon)
        key_insights_match = re.match(r'^KEY_INSIGHTS\s*:?\s*(.*)$', line, re.IGNORECASE)
        if key_insights_match:
            parsing_insights = True
            # Check if JSON is on the same line (after optional colon)
            rest = key_insights_match.group(1).strip()
            if rest:
                insights_json_buffer = rest
            continue

        # If we're parsing insights, accumulate the JSON
        if parsing_insights:
            # Stop parsing insights if we hit another section marker
            if line.upper().startswith('DAY ') or line.upper().startswith('TRIP:') or line.upper().startswith('DATES:'):
                # Try to parse accumulated buffer
                if insights_json_buffer:
                    try:
                        result['key_insights'] = json.loads(insights_json_buffer)
                    except json.JSONDecodeError:
                        pass
                parsing_insights = False
                # Don't continue - let the line be processed by other handlers
            else:
                # Accumulate JSON content
                insights_json_buffer += line
                continue

        # Parse any unstructured lines as insights/todos and append to current booking notes
        # This includes: checkboxes [ ], reminders, todos, @mentions, or any other text
        if current_booking is not None and line and not line.upper().startswith('DAY') and '|' not in line and not parsing_insights:
            # Skip if it's a new TRIP or DATES line or KEY_INSIGHTS (handled above)
            if line.upper().startswith('TRIP:') or line.upper().startswith('DATES:') or re.match(r'^KEY_INSIGHTS\s*:?\s*', line, re.IGNORECASE):
                continue

            # This is likely a todo, reminder, or insight - add it to notes
            if current_booking['notes']:
                current_booking['notes'] += '\n' + line
            else:
                current_booking['notes'] = line
            continue

    # After loop ends, try to parse any remaining insights buffer
    if parsing_insights and insights_json_buffer:
        try:
            result['key_insights'] = json.loads(insights_json_buffer)
        except json.JSONDecodeError:
            # Try to extract JSON array from buffer (in case there's extra text)
            json_match = re.search(r'\[.*\]', insights_json_buffer, re.DOTALL)
            if json_match:
                try:
                    result['key_insights'] = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass

    return result


def parse_date_range(date_str: str) -> Tuple[str, str]:
    """Parse date range like 'Dec 22 - Dec 28, 2025' into start and end dates."""
    try:
        # Handle various formats with different separators (arrows, dashes, etc.)
        separator = None
        # Try these in order of specificity (most specific first)
        for sep in [' -> ', ' − ', ' - ', ' – ', ' — ', '->', '−', '-', '–', '—']:
            if sep in date_str:
                separator = sep
                break

        if separator:
            parts = date_str.split(separator, 1)  # Split only on first occurrence
            start = parts[0].strip()
            end = parts[1].strip()

            # If start doesn't have year, extract from end
            if ',' not in start and ',' in end:
                year = end.split(',')[1].strip()
                start = f"{start}, {year}"

            return start, end
        else:
            return date_str, date_str
    except:
        return date_str, date_str


def parse_date(date_str: str) -> Tuple[str, str]:
    """
    Parse date string into YYYY-MM-DD key and display format.
    Examples: 'Dec 22, 2025' -> ('2025-12-22', 'Monday, December 22')
    """
    try:
        # Try to parse various date formats
        for fmt in ['%b %d, %Y', '%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                date_key = dt.strftime('%Y-%m-%d')
                display = dt.strftime('%A, %B %d')
                return date_key, display
            except ValueError:
                continue

        # If no format works, return as-is
        return date_str, date_str
    except:
        return date_str, date_str


def parse_time(time_str: str, date_key: str) -> Tuple[str, str, str]:
    """
    Parse time string and return start_time, end_time, and ISO datetime.
    Examples:
    - '9:30 AM' -> ('9:30 AM', '', '2025-12-22T09:30:00')
    - '9:30 AM - 4:00 PM' -> ('9:30 AM', '4:00 PM', '2025-12-22T09:30:00')
    """

    time_str = time_str.strip()

    # Check for time range
    if ' - ' in time_str or ' to ' in time_str.lower():
        separator = ' - ' if ' - ' in time_str else ' to '
        parts = time_str.split(separator)
        start_time = parts[0].strip()
        end_time = parts[1].strip() if len(parts) > 1 else ''

        # Convert to 12-hour format if needed
        start_time = normalize_time_format(start_time)
        end_time = normalize_time_format(end_time)

        # Create ISO datetime
        iso_time = convert_to_iso_datetime(start_time, date_key)

        return start_time, end_time, iso_time
    else:
        # Single time
        start_time = normalize_time_format(time_str)
        iso_time = convert_to_iso_datetime(start_time, date_key)
        return start_time, '', iso_time


def normalize_time_format(time_str: str) -> str:
    """Convert time to 12-hour format with AM/PM."""
    if not time_str:
        return ''

    try:
        # Try parsing 24-hour format
        if ':' in time_str and ('AM' not in time_str.upper() and 'PM' not in time_str.upper()):
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = parts[1] if len(parts) > 1 else '00'

            if hour >= 12:
                return f"{hour if hour == 12 else hour - 12}:{minute} PM"
            else:
                return f"{hour if hour != 0 else 12}:{minute} AM"

        return time_str
    except:
        return time_str


def convert_to_iso_datetime(time_str: str, date_key: str) -> str:
    """Convert time and date to ISO datetime format."""
    if not time_str:
        return f"{date_key}T00:00:00"

    try:
        # Parse time
        time_upper = time_str.upper().strip()

        # Extract hour and minute
        time_part = time_upper.replace('AM', '').replace('PM', '').strip()
        parts = time_part.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        # Convert to 24-hour
        if 'PM' in time_upper and hour != 12:
            hour += 12
        elif 'AM' in time_upper and hour == 12:
            hour = 0

        return f"{date_key}T{hour:02d}:{minute:02d}:00"
    except:
        return f"{date_key}T00:00:00"


def normalize_location(location: str) -> str:
    """Normalize location name to location key.

    Handles complex strings like "Kauai (Arrival - Sunday)" by extracting
    just the location name and removing parenthetical content.
    """
    # First, clean the location string - remove parenthetical content
    # This handles cases like "Kauai (Arrival - Sunday)" -> "Kauai"
    location_clean = re.sub(r'\s*\([^)]*\)\s*', ' ', location)

    # Also remove common suffixes like "- Day 1", "- Arrival", etc.
    location_clean = re.sub(r'\s*[-–]\s*(Day\s*\d+|Arrival|Departure|Morning|Evening|Night|Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday).*$', '', location_clean, flags=re.IGNORECASE)

    location_lower = location_clean.lower().strip()

    # Map common variations (expanded list)
    location_map = {
        # Hawaii
        'kauai': 'kauai',
        'lihue': 'kauai',
        'poipu': 'kauai',
        'princeville': 'kauai',
        'hanalei': 'kauai',
        'oahu': 'oahu',
        'honolulu': 'honolulu',
        'waikiki': 'honolulu',
        'maui': 'maui',
        'lahaina': 'maui',
        'kaanapali': 'maui',
        'wailea': 'maui',
        'big island': 'big_island',
        'hawaii island': 'big_island',
        'kona': 'big_island',
        'hilo': 'big_island',
        # Thailand
        'phuket': 'phuket',
        'krabi': 'krabi',
        'koh samui': 'koh_samui',
        'samui': 'koh_samui',
        'bangkok': 'bangkok',
        'phi phi': 'phi_phi',
        'phi phi islands': 'phi_phi',
        'koh phangan': 'koh_phangan',
        'phangan': 'koh_phangan',
        'chiang mai': 'chiang_mai',
        # France
        'paris': 'paris',
        'versailles': 'versailles',
        'lyon': 'lyon',
        'nice': 'nice',
        'marseille': 'marseille',
        # Austria
        'vienna': 'vienna',
        'salzburg': 'salzburg',
        'innsbruck': 'innsbruck',
        'hallstatt': 'hallstatt',
        # Italy
        'rome': 'rome',
        'florence': 'florence',
        'venice': 'venice',
        'milan': 'milan',
        'naples': 'naples',
        'amalfi': 'amalfi',
        'positano': 'amalfi',
        'sicily': 'sicily',
        # Other Europe
        'london': 'london',
        'barcelona': 'barcelona',
        'amsterdam': 'amsterdam',
        'berlin': 'berlin',
        'munich': 'munich',
        'prague': 'prague',
        'lisbon': 'lisbon',
        'dublin': 'dublin',
        # California
        'mendocino': 'mendocino',
        'albion': 'albion',
        'fort bragg': 'fort_bragg',
        'little river': 'little_river',
        'sonoma': 'sonoma',
        'san francisco': 'san_francisco',
        'los angeles': 'los_angeles',
        'san diego': 'san_diego',
        'napa': 'napa',
        # Alaska
        'anchorage': 'anchorage',
        'seward': 'seward',
        'talkeetna': 'talkeetna',
        'wasilla': 'wasilla',
        'fairbanks': 'fairbanks',
        'juneau': 'juneau',
        # Other US
        'new york': 'new_york',
        'nyc': 'new_york',
        'miami': 'miami',
        'las vegas': 'las_vegas',
        'seattle': 'seattle',
        'boston': 'boston',
        'chicago': 'chicago',
        'denver': 'denver',
        'austin': 'austin',
        'portland': 'portland',
        # Asia
        'tokyo': 'tokyo',
        'kyoto': 'kyoto',
        'osaka': 'osaka',
        'singapore': 'singapore',
        'bali': 'bali',
        'hong kong': 'hong_kong',
        'seoul': 'seoul',
        'taipei': 'taipei',
        # Australia/NZ
        'sydney': 'sydney',
        'melbourne': 'melbourne',
        'auckland': 'auckland',
        'queenstown': 'queenstown',
        # Caribbean/Mexico
        'cancun': 'cancun',
        'cabo': 'cabo',
        'puerto rico': 'puerto_rico',
        'san juan': 'san_juan',
        'jamaica': 'jamaica',
        'bahamas': 'bahamas',
    }

    for key, value in location_map.items():
        if key in location_lower:
            return value

    # Default to cleaned lowercase with underscores
    # Only use the first part before any remaining dashes or special chars
    clean_key = location_lower.replace(' ', '_').replace(',', '').replace('.', '')
    return clean_key


def normalize_booking_type(booking_type: str) -> str:
    """Normalize booking type to standard values."""
    type_lower = booking_type.lower().strip()

    type_map = {
        'hotel': 'hotels',
        'hotels': 'hotels',
        'accommodation': 'hotels',
        'resort': 'hotels',
        'flight': 'flights',
        'flights': 'flights',
        'plane': 'flights',
        'tour': 'tours',
        'tours': 'tours',
        'activity': 'tours',
        'excursion': 'tours',
        'snorkeling': 'tours',
        'sightseeing': 'tours',
        'ferry': 'ferries',
        'ferries': 'ferries',
        'boat': 'ferries',
        'speedboat': 'ferries',
        'restaurant': 'dining',
        'dining': 'dining',
        'food': 'dining',
        'spa': 'spa',
        'massage': 'spa',
        'wellness': 'spa',
    }

    return type_map.get(type_lower, 'tours')


def normalize_status(status: str) -> str:
    """Normalize status to standard values."""
    status_lower = status.lower().strip()

    status_map = {
        'confirmed': 'confirmed',
        'paid': 'confirmed',
        'booked': 'confirmed',
        'pending': 'pending',
        'waiting': 'pending',
        'optional': 'optional',
        'maybe': 'optional',
        'cancelled': 'cancelled',
        'canceled': 'cancelled',
    }

    return status_map.get(status_lower, 'confirmed')


def extract_sender(booking_ref: str) -> str:
    """Extract sender/company name from booking reference."""
    # Common booking platforms
    platforms = {
        'booking': 'Booking.com',
        'tripadvisor': 'Tripadvisor',
        '12go': '12Go',
        'agoda': 'Agoda',
        'expedia': 'Expedia',
        'hotels': 'Hotels.com',
        'airbnb': 'Airbnb',
    }

    ref_lower = booking_ref.lower()
    for key, value in platforms.items():
        if key in ref_lower:
            return value

    return 'Booking'
