#!/usr/bin/env python3
"""
Travel Extractor v2 - Extract travel bookings from Gmail and create detailed itineraries.
Outputs both Markdown and JSON for AI enhancement.
"""

import os
import re
import json
import base64
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, List, Dict, Tuple
from dateutil import parser as date_parser
import tempfile

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Location detection keywords
LOCATIONS = {
    # Thailand
    'phuket': ['phuket', 'patong', 'karon', 'kata', 'rassada pier', 'supicha'],
    'krabi': ['krabi', 'ao nang', 'railay', 'nopparat thara', 'verandah'],
    'koh_samui': ['koh samui', 'samui', 'chaweng', 'lamai', 'bophut', 'bo put', 'nathon', 'blue turtle', 'maenam', 'mae nam'],
    'koh_phangan': ['koh phangan', 'phangan', 'haad rin'],
    'bangkok': ['bangkok', 'suvarnabhumi', 'don mueang', 'davis', 'pratunam', 'sukhumvit'],
    'phi_phi': ['phi phi', 'koh phi', 'phi-phi'],
    'hong_islands': ['hong island', 'hong islands'],
    # Italy
    'rome': ['rome', 'roma', 'fiumicino', 'ciampino', 'vatican', 'colosseum', 'trastevere', 'termini'],
    'florence': ['florence', 'firenze', 'tuscany', 'toscana', 'uffizi', 'duomo'],
    'venice': ['venice', 'venezia', 'murano', 'burano', 'san marco', 'rialto'],
    'milan': ['milan', 'milano', 'malpensa', 'linate'],
    'naples': ['naples', 'napoli', 'pompeii', 'amalfi', 'positano', 'sorrento', 'capri'],
    'cinque_terre': ['cinque terre', 'monterosso', 'vernazza', 'corniglia', 'manarola', 'riomaggiore'],
    'sicily': ['sicily', 'sicilia', 'palermo', 'catania', 'taormina'],
    'bologna': ['bologna', 'emilia-romagna'],
    'pisa': ['pisa', 'leaning tower'],
    'lake_como': ['lake como', 'como', 'bellagio', 'varenna'],
    # Generic/Other
    'paris': ['paris', 'cdg', 'orly', 'eiffel'],
    'london': ['london', 'heathrow', 'gatwick', 'stansted'],
    'barcelona': ['barcelona', 'el prat'],
    'madrid': ['madrid', 'barajas'],
    'amsterdam': ['amsterdam', 'schiphol'],
    'lisbon': ['lisbon', 'lisboa'],
    'berlin': ['berlin', 'tegel', 'brandenburg'],
    'munich': ['munich', 'münchen'],
    'vienna': ['vienna', 'wien'],
    'prague': ['prague', 'praha'],
    'new_york': ['new york', 'nyc', 'jfk', 'laguardia', 'newark', 'manhattan'],
    'los_angeles': ['los angeles', 'lax', 'hollywood'],
    'tokyo': ['tokyo', 'narita', 'haneda', 'shinjuku', 'shibuya'],
    'singapore': ['singapore', 'changi'],
    'dubai': ['dubai', 'dxb', 'abu dhabi'],
    'bali': ['bali', 'ubud', 'seminyak', 'kuta', 'denpasar'],
}

# Booking sources
BOOKING_SOURCES = {
    'flights': ['singaporeair', 'emirates', 'qatarairways', 'thaiairways', 'airasia',
                'vietjet', 'bangkokair', 'capital one', 'chase travel', 'united', 'delta'],
    'hotels': ['booking.com', 'agoda', 'airbnb', 'marriott', 'hilton', 'expedia', 'hotels.com'],
    'tours': ['getyourguide', 'viator', 'klook', 'tripadvisor', 'civitatis'],
    'ferries': ['12go', 'lomprayah', 'songserm', 'seatran', 'raja ferry'],
    'dining': ['restaurant', 'lounge', 'rooftop', 'reservation', 'opentable'],
    'spa': ['spa', 'massage', 'wellness', 'radarom']
}

# False positive confirmation codes to filter
FALSE_CONFIRMATIONS = [
    'details', 'number', 'code', 'from', 'your', 'confirmation', 'booking',
    'request', 'radius', 'policy', 'center', 'hong', 'trip', 'reserved'
]


class TravelExtractor:
    def __init__(self, credentials_file: str = 'credentials.json', token_file: str = 'token.json'):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None

    def authenticate(self) -> bool:
        """Authenticate with Gmail API."""
        creds = None
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    print(f"ERROR: {self.credentials_file} not found.")
                    return False
                flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())

        self.service = build('gmail', 'v1', credentials=creds)
        return True

    def get_labels(self) -> list:
        """Get all Gmail labels."""
        results = self.service.users().labels().list(userId='me').execute()
        return [(l['name'], l['id']) for l in results.get('labels', [])]

    def search_emails(self, label: str = None, query: str = None, max_results: int = 200) -> list:
        """Search Gmail using label and/or query."""
        search_query_parts = []
        if label:
            clean_label = label.replace(' ', '-').lower()
            search_query_parts.append(f'label:{clean_label}')
        if query:
            search_query_parts.append(query)

        final_query = ' '.join(search_query_parts) if search_query_parts else None
        print(f"Gmail search query: {final_query}")

        results = self.service.users().messages().list(
            userId='me', q=final_query, maxResults=max_results
        ).execute()

        messages = results.get('messages', [])
        emails = []

        print(f"Fetching {len(messages)} emails...")
        for i, msg in enumerate(messages):
            if (i + 1) % 10 == 0:
                print(f"  Processing {i + 1}/{len(messages)}...")
            full_msg = self.service.users().messages().get(
                userId='me', id=msg['id'], format='full'
            ).execute()
            emails.append(self._parse_email(full_msg))

        return emails

    def _parse_email(self, message: dict) -> dict:
        """Parse email with attachments."""
        headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
        body = self._get_email_body(message['payload'])
        attachments = self._get_attachments(message)

        return {
            'id': message['id'],
            'subject': headers.get('Subject', ''),
            'from': headers.get('From', ''),
            'date': headers.get('Date', ''),
            'body': body,
            'snippet': message.get('snippet', ''),
            'attachments': attachments
        }

    def _get_email_body(self, payload: dict) -> str:
        """Extract email body text."""
        body = ''
        if 'body' in payload and payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and part['body'].get('data'):
                    body += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html' and part['body'].get('data') and not body:
                    html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                    body += self._strip_html(html)
                elif 'parts' in part:
                    body += self._get_email_body(part)
        return body

    def _strip_html(self, html: str) -> str:
        """Convert HTML to text."""
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&#39;', "'", text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _get_attachments(self, message: dict) -> list:
        """Get PDF attachment info."""
        attachments = []

        def find_attachments(payload):
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('filename') and part['filename'].lower().endswith('.pdf'):
                        attachments.append({
                            'filename': part['filename'],
                            'attachment_id': part['body'].get('attachmentId'),
                            'size': part['body'].get('size', 0)
                        })
                    if 'parts' in part:
                        find_attachments(part)

        find_attachments(message['payload'])
        return attachments

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download an attachment."""
        attachment = self.service.users().messages().attachments().get(
            userId='me', messageId=message_id, id=attachment_id
        ).execute()
        return base64.urlsafe_b64decode(attachment['data'])

    def extract_pdf_text(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        try:
            import fitz  # PyMuPDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
                f.write(pdf_bytes)
                f.flush()
                doc = fitz.open(f.name)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                os.unlink(f.name)
                return text
        except ImportError:
            return ""
        except Exception:
            return ""

    def detect_location(self, text: str) -> Optional[str]:
        """Detect location from text."""
        text_lower = text.lower()
        for location, keywords in LOCATIONS.items():
            if any(kw in text_lower for kw in keywords):
                return location
        return None

    def identify_booking_type(self, email: dict) -> str:
        """Identify booking type."""
        text = f"{email['from']} {email['subject']} {email['snippet']}".lower()

        for btype, keywords in BOOKING_SOURCES.items():
            if any(kw in text for kw in keywords):
                return btype

        # Keyword fallback
        if any(kw in text for kw in ['flight', 'airline', 'boarding', 'airport']):
            return 'flights'
        if any(kw in text for kw in ['hotel', 'resort', 'check-in', 'room', 'stay']):
            return 'hotels'
        if any(kw in text for kw in ['tour', 'activity', 'island', 'snorkel', 'kayak', 'speedboat']):
            return 'tours'
        if any(kw in text for kw in ['ferry', 'boat', 'pier', 'transfer']):
            return 'ferries'

        return 'other'

    def extract_trip_date(self, text: str) -> Optional[datetime]:
        """Extract the actual trip/activity date from text. Works with any date."""

        now = datetime.now()
        min_year = now.year - 2  # Accept dates from 2 years ago
        max_year = now.year + 2  # Accept dates up to 2 years ahead

        def is_valid_date(dt):
            """Check if date is within reasonable range."""
            return dt and min_year <= dt.year <= max_year

        # HIGH PRIORITY: Activity-specific date patterns
        activity_patterns = [
            # "Tour on September 25, 2024" or "on 24th September 2024"
            r'(?:tour|activity|trip|experience|visit|check-in|check in|departure|arrives?|booking|reservation)\s+(?:on|for|date:?)?\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            r'(?:tour|activity|trip|experience|visit|check-in|check in|departure|arrives?)\s+(?:on|for|date:?)?\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})',
            # "on Thursday, September 25, 2024"
            r'on\s+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            # "Thursday, September 25, 2024 at 9:00 AM"
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})\s+at\s+\d',
            # "Departure date: 24 Sep 2024"
            r'(?:departure|arrival|travel|trip)\s*date:?\s*(?:\d{1,2}:\d{2}\s*(?:AM|PM)?,?\s*)?(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})',
            # "Check-in: September 22, 2024"
            r'(?:check-in|check in|checkin|check-out|checkout)[:\s]+(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?,?\s*((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})',
            # "Date: 25 September 2024" or "Date: September 25, 2024"
            r'date[:\s]+(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})',
            r'date[:\s]+((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})',
        ]

        for pattern in activity_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
                    parsed = date_parser.parse(date_str, fuzzy=True)
                    if is_valid_date(parsed):
                        return parsed
                except:
                    continue

        # MEDIUM PRIORITY: Day of week with date
        day_patterns = [
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4})',
            r'(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})',
        ]

        for pattern in day_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    date_str = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
                    parsed = date_parser.parse(date_str, fuzzy=True)
                    if is_valid_date(parsed):
                        return parsed
                except:
                    continue

        # Standard date formats: "Month DD, YYYY" or "DD Month YYYY"
        general_patterns = [
            r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})',
        ]

        for pattern in general_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    date_str = match.group(1)
                    parsed = date_parser.parse(date_str, fuzzy=True)
                    if is_valid_date(parsed):
                        return parsed
                except:
                    continue

        # European format: DD/MM/YYYY or DD.MM.YYYY or DD-MM-YYYY
        eu_date_match = re.search(r'(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})', text)
        if eu_date_match:
            try:
                day, month, year = eu_date_match.groups()
                day, month, year = int(day), int(month), int(year)
                if 1 <= month <= 12 and 1 <= day <= 31 and min_year <= year <= max_year:
                    return datetime(year, month, day)
            except:
                pass

        # ISO format: YYYY-MM-DD
        iso_date_match = re.search(r'(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})', text)
        if iso_date_match:
            try:
                year, month, day = iso_date_match.groups()
                year, month, day = int(year), int(month), int(day)
                if 1 <= month <= 12 and 1 <= day <= 31 and min_year <= year <= max_year:
                    return datetime(year, month, day)
            except:
                pass

        # US format: MM/DD/YYYY (try if EU format didn't work)
        us_date_match = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', text)
        if us_date_match:
            try:
                month, day, year = us_date_match.groups()
                month, day, year = int(month), int(day), int(year)
                if 1 <= month <= 12 and 1 <= day <= 31 and min_year <= year <= max_year:
                    return datetime(year, month, day)
            except:
                pass

        return None

    def extract_time_info(self, text: str) -> dict:
        """Extract time-related information."""
        info = {}

        # Start time patterns
        start_patterns = [
            r'(?:starts?|departure|departs?|pickup|pick-up|pick up|meeting)[:\s]+at?\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',
            r'(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))\s*[-–]\s*\d{1,2}:\d{2}',  # Time range
            r'at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))',
            r'(\d{1,2}:\d{2}\s*(?:AM|PM))\s+(?:departure|start)',
        ]
        for pattern in start_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['start_time'] = match.group(1).strip()
                break

        # End time / arrival
        end_patterns = [
            r'(?:ends?|arrival|arrives?|drop-off|return|until)[:\s]+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',
            r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?\s*[-–]\s*(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)?)',
        ]
        for pattern in end_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                info['end_time'] = match.group(1).strip()
                break

        # Duration
        duration_patterns = [
            r'(?:duration|length)[:\s]*(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)',
            r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s*(?:tour|trip|experience)',
            r'(\d+)\s*(?:hours?|hrs?)\s+(\d+)\s*(?:minutes?|mins?)',
        ]
        for pattern in duration_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    info['duration'] = f"{match.group(1)}h {match.group(2)}m"
                else:
                    info['duration'] = f"{match.group(1)} hours"
                break

        return info

    def extract_location_info(self, text: str) -> dict:
        """Extract location/address information."""
        info = {}

        # Meeting point / pickup location - clean patterns
        meeting_patterns = [
            r'(?:meeting\s+point|pickup\s+(?:point|location|at|from)|pick-up\s+(?:point|location|at|from))[:\s]*([A-Z][^.\n]{15,120})',
            r'(?:meet\s+at|pickup\s+at|pick\s+up\s+at)[:\s]*([A-Z][^.\n]{15,100})',
        ]
        for pattern in meeting_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Filter out URLs and encoded strings
                if not location.startswith('http') and '%' not in location[:20]:
                    location = re.sub(r'\s+', ' ', location)
                    info['meeting_point'] = location[:150]
                    break

        # Departure/Arrival piers
        pier_patterns = [
            r'(?:departure\s+from|depart\s+from|from)[:\s]*([A-Z][A-Za-z\s]+Pier)',
            r'([A-Z][A-Za-z\s]+Pier)[,\s]+(?:Phuket|Krabi|Samui)',
        ]
        for pattern in pier_patterns:
            match = re.search(pattern, text)
            if match and 'departure_pier' not in info:
                info['departure_pier'] = match.group(1).strip()

        arrival_patterns = [
            r'(?:arrival\s+to|arrive\s+at|to)[:\s]*([A-Z][A-Za-z\s]+Pier)',
        ]
        for pattern in arrival_patterns:
            match = re.search(pattern, text)
            if match:
                info['arrival_pier'] = match.group(1).strip()

        # Hotel/Stay name
        hotel_patterns = [
            r'(?:stay|staying|hotel|accommodation)[:\s]+(?:at\s+)?([A-Z][A-Za-z\s&\'-]+(?:Hotel|Resort|Inn|Suites|Villa|House|Hostel))',
            r'((?:Grand|Royal|The|Blue|Golden|Green|Davis)[A-Za-z\s\']+(?:Hotel|Resort|Villa|House))',
            r'confirmed\s+at\s+([A-Z][A-Za-z\s]+)',
        ]
        for pattern in hotel_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                hotel = match.group(1).strip()
                if len(hotel) > 5 and len(hotel) < 60:
                    info['hotel'] = hotel
                    break

        # Full address with Thai formatting
        address_match = re.search(r'(\d+[/\d]*\s+[A-Za-z\s,]+(?:Road|Rd|Street|St|Soi)[^,\n]*,\s*[^,\n]+,\s*(?:Thailand|\d{5}))', text)
        if address_match:
            info['address'] = address_match.group(1).strip()

        return info

    def extract_booking_reference(self, text: str) -> Optional[str]:
        """Extract booking/confirmation reference."""
        patterns = [
            r'#([A-Z]{2,4}[0-9A-Z]{4,12})\b',  # #GYGMX4XH4XFR
            r'(?:booking|confirmation|reference|order)\s*(?:number|code|id)?[:\s#]+([A-Z0-9]{6,15})\b',
            r'(?:trip\s+id|booking\s+id|order\s+id)[:\s#]+(\d{8,15})',
            r'(?:pnr|record\s+locator)[:\s]+([A-Z0-9]{6})\b',
            r'confirmation[:\s]+#?(\d{8,12})\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ref = match.group(1).strip()
                # Filter false positives
                if ref.lower() not in FALSE_CONFIRMATIONS and len(ref) >= 6:
                    return ref
        return None

    def extract_all_links(self, text: str) -> list:
        """Extract all relevant URLs."""
        urls = re.findall(r'https?://[^\s<>"\')\]]+', text)

        # Filter and categorize
        links = []
        dominated_domains = ['getyourguide', 'booking.com', 'agoda', 'tripadvisor', 'klook',
                           '12go', 'viator', 'airbnb', 'expedia', 'google.com/travel',
                           'google.com/maps', 'maps.app.goo.gl', 'goo.gl', 'erandaspa',
                           'marriott', 'hilton', 'hotels.com']

        for url in urls:
            # Skip privacy policies, unsubscribe, tracking
            if any(skip in url.lower() for skip in ['privacy', 'unsubscribe', 'track', 'click', 'email']):
                continue
            if any(domain in url.lower() for domain in dominated_domains):
                links.append(url[:200])

        return list(set(links))[:5]  # Dedupe and limit

    def extract_place_names(self, text: str) -> list:
        """Extract notable place names for AI enhancement."""
        places = []

        # Thai place patterns - specific and clean
        patterns = [
            r'(Phi Phi Islands?)',
            r'(Koh Phi Phi)',
            r'(Hong Islands?)',
            r'(Khai Islands?)',
            r'(Railay Beach)',
            r'(Maya Bay)',
            r'(Ang Thong (?:National |Marine )?Park)',
            r'(Chaweng Beach)',
            r'(Lamai Beach)',
            r'(Patong Beach)',
            r'(Grand Supicha[A-Za-z\s]*Hotel)',
            r'(The Verandah[A-Za-z\s]*Hotel)',
            r'(Blue Turtle[A-Za-z\s]*Hotel)',
            r'(Davis Bangkok[A-Za-z\s]*Hotel)',
            r'(Octave Rooftop[A-Za-z\s]*)',
            r'(Chaweng Night Market)',
            r'(Pratunam Market)',
            r'(Rassada Pier)',
            r'(Nopparat Thara Pier)',
            r'(Nathon Pier)',
            r'(Radarom Spa)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                clean = m.strip()
                # Filter out garbage (URLs, encoded text, too long)
                if len(clean) > 5 and len(clean) < 50 and '%' not in clean and 'http' not in clean.lower():
                    places.append(clean)

        return list(set(places))[:8]

    def extract_activity_name(self, text: str) -> Optional[str]:
        """Extract the main activity/tour name."""
        # Look in subject first
        patterns = [
            r'(?:Reserved|Booked|Confirmation)[:\s]+([A-Z][^|!\n]{10,60})',
            r'([A-Z][A-Za-z\s]+(?:Tour|Trip|Experience|Snorkeling|Kayaking|Island[s]?))',
            r'(\d+\s+Island[s]?\s+[A-Za-z\s]+(?:Tour|Trip))',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                name = match.group(1).strip()
                if len(name) > 10:
                    return name[:80]
        return None

    def extract_booking_details(self, email: dict) -> dict:
        """Extract comprehensive booking details."""
        full_text = f"{email['subject']} {email['body']}"

        # Get PDF content if available
        pdf_text = ""
        pdf_filenames = []
        if email['attachments']:
            for att in email['attachments']:
                pdf_filenames.append(att['filename'])
                if att['attachment_id']:
                    try:
                        pdf_bytes = self.download_attachment(email['id'], att['attachment_id'])
                        pdf_text += self.extract_pdf_text(pdf_bytes)
                    except:
                        pass

        combined_text = full_text + " " + pdf_text

        # Extract all details
        trip_date = self.extract_trip_date(combined_text)
        time_info = self.extract_time_info(combined_text)
        location_info = self.extract_location_info(combined_text)
        booking_ref = self.extract_booking_reference(combined_text)
        links = self.extract_all_links(combined_text)
        places = self.extract_place_names(combined_text)
        activity_name = self.extract_activity_name(email['subject'])
        location = self.detect_location(combined_text)

        # Get sender name
        sender = email['from']
        sender_name = sender.split('<')[0].strip().strip('"')

        return {
            'type': self.identify_booking_type(email),
            'activity_name': activity_name,
            'subject': email['subject'],
            'sender': sender_name,
            'trip_date': trip_date,
            'email_date': self._parse_date(email['date']),
            'booking_ref': booking_ref,
            'time_info': time_info,
            'location_info': location_info,
            'location': location,
            'links': links,
            'places': places,
            'snippet': email['snippet'][:300],
            'has_pdf': len(email['attachments']) > 0,
            'pdf_filenames': pdf_filenames,
            'email_id': email['id']
        }

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse email date."""
        try:
            return date_parser.parse(date_str, fuzzy=True)
        except:
            return None

    def process_emails(self, emails: list) -> List[dict]:
        """Process all emails and extract bookings."""
        bookings = []

        for email in emails:
            text = f"{email['subject']} {email['snippet']}".lower()

            # Skip obvious promos
            promo_keywords = ['save up to', 'limited time', 'flash sale', 'deals for you', 'exclusive offer', 'off on']
            if sum(1 for kw in promo_keywords if kw in text) >= 2:
                continue

            # Look for confirmation indicators
            conf_keywords = ['confirm', 'booking', 'reservation', 'itinerary', 'ticket', 'voucher', 'receipt', 'reserved']
            if any(kw in text for kw in conf_keywords):
                details = self.extract_booking_details(email)
                bookings.append(details)

        return bookings

    def organize_by_day(self, bookings: list, start_date: str, end_date: str) -> Tuple[Dict, List]:
        """Organize bookings by trip day with location context."""
        start = date_parser.parse(start_date)
        end = date_parser.parse(end_date)

        # Create day buckets
        days = {}
        current = start
        while current <= end:
            day_key = current.strftime('%Y-%m-%d')
            days[day_key] = {
                'date': current,
                'day_num': (current - start).days + 1,
                'display': current.strftime('%A, %B %d'),
                'location': None,
                'bookings': [],
                'notes': []
            }
            current += timedelta(days=1)

        # Assign bookings to days
        unassigned = []
        for booking in bookings:
            assigned = False
            if booking['trip_date']:
                day_key = booking['trip_date'].strftime('%Y-%m-%d')
                if day_key in days:
                    days[day_key]['bookings'].append(booking)
                    # Update location from booking
                    if booking['location'] and not days[day_key]['location']:
                        days[day_key]['location'] = booking['location']
                    assigned = True

            if not assigned:
                unassigned.append(booking)

        # Sort bookings within each day by time
        for day_key in days:
            days[day_key]['bookings'].sort(
                key=lambda x: x['time_info'].get('start_time', '99:99')
            )

        # Infer locations for days without explicit location
        self._infer_day_locations(days)

        return days, unassigned

    def _infer_day_locations(self, days: dict):
        """Infer locations for days based on hotels and activities."""
        location_map = {
            'phuket': 'Phuket',
            'krabi': 'Krabi / Ao Nang',
            'koh_samui': 'Koh Samui',
            'koh_phangan': 'Koh Phangan',
            'bangkok': 'Bangkok',
            'phi_phi': 'Phi Phi Islands',
            'hong_islands': 'Hong Islands'
        }

        for day_key in sorted(days.keys()):
            day = days[day_key]
            if day['location']:
                day['location_display'] = location_map.get(day['location'], day['location'].title())
            else:
                # Try to infer from bookings
                for booking in day['bookings']:
                    loc = booking.get('location')
                    if loc:
                        day['location'] = loc
                        day['location_display'] = location_map.get(loc, loc.title())
                        break
                    # Check hotel name
                    hotel = booking.get('location_info', {}).get('hotel', '')
                    detected = self.detect_location(hotel)
                    if detected:
                        day['location'] = detected
                        day['location_display'] = location_map.get(detected, detected.title())
                        break

    def generate_detailed_itinerary(self, trip_name: str, days: dict, unassigned: list) -> str:
        """Generate detailed day-by-day markdown itinerary."""
        lines = [
            f"# {trip_name}",
            "",
            f"*Generated: {datetime.now().strftime('%B %d, %Y')}*",
            "",
            "---",
            ""
        ]

        type_icons = {
            'flights': '✈️ FLIGHT',
            'hotels': '🏨 STAY',
            'tours': '🎫 ACTIVITY',
            'ferries': '⛴️ FERRY/TRANSPORT',
            'transport': '🚐 TRANSFER',
            'dining': '🍽️ DINING',
            'spa': '💆 SPA/WELLNESS',
            'other': '📋 BOOKING'
        }

        for day_key in sorted(days.keys()):
            day_data = days[day_key]
            if not day_data['bookings']:
                continue

            # Day header with location
            location_str = f" - {day_data.get('location_display', '')}" if day_data.get('location_display') else ""
            lines.append(f"## Day {day_data['day_num']} ({day_data['display']}){location_str}")
            lines.append("")

            for booking in day_data['bookings']:
                icon_label = type_icons.get(booking['type'], '📋 BOOKING')

                # Title - use activity name if available, else subject
                title = booking.get('activity_name') or booking['subject']
                if len(title) > 70:
                    title = title[:67] + "..."

                lines.append(f"### {icon_label}")
                lines.append(f"**{title}**")
                lines.append("")

                # Booking source
                lines.append(f"- **Booked via:** {booking['sender']}")

                # Booking reference
                if booking['booking_ref']:
                    lines.append(f"- **Confirmation:** `{booking['booking_ref']}`")

                # Time information
                time_info = booking['time_info']
                if time_info:
                    time_parts = []
                    if 'start_time' in time_info:
                        time_parts.append(f"Starts {time_info['start_time']}")
                    if 'end_time' in time_info:
                        time_parts.append(f"Ends {time_info['end_time']}")
                    if 'duration' in time_info:
                        time_parts.append(f"({time_info['duration']})")
                    if time_parts:
                        lines.append(f"- **Time:** {' | '.join(time_parts)}")

                # Location information
                loc_info = booking['location_info']
                if loc_info:
                    if 'hotel' in loc_info:
                        lines.append(f"- **Stay:** {loc_info['hotel']}")
                    if 'departure_pier' in loc_info:
                        lines.append(f"- **Departure:** {loc_info['departure_pier']}")
                    if 'arrival_pier' in loc_info:
                        lines.append(f"- **Arrival:** {loc_info['arrival_pier']}")
                    if 'meeting_point' in loc_info:
                        lines.append(f"- **Meeting Point:** {loc_info['meeting_point']}")
                    if 'address' in loc_info:
                        lines.append(f"- **Address:** {loc_info['address']}")

                # Links
                if booking['links']:
                    lines.append(f"- **Link:** {booking['links'][0]}")

                # Places for AI enhancement
                if booking['places']:
                    lines.append(f"- **Places mentioned:** {', '.join(booking['places'][:5])}")

                # PDF indicator
                if booking['has_pdf']:
                    filenames = ', '.join(booking['pdf_filenames'][:2])
                    lines.append(f"- **📎 Attachments:** {filenames}")

                lines.append("")

            # Notes section for manual additions
            lines.append("**Notes:**")
            lines.append("- _Add your notes here (e.g., explore local area, party, chill)_")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Unassigned bookings
        if unassigned:
            lines.append("## 📌 Other Bookings (Date to be confirmed)")
            lines.append("")
            for booking in unassigned:
                title = booking.get('activity_name') or booking['subject'][:50]
                lines.append(f"- **{title}** via {booking['sender']}")
                if booking['booking_ref']:
                    lines.append(f"  - Confirmation: `{booking['booking_ref']}`")
                if booking['links']:
                    lines.append(f"  - Link: {booking['links'][0]}")
                if booking['places']:
                    lines.append(f"  - Places: {', '.join(booking['places'][:3])}")
            lines.append("")

        # AI Enhancement section
        lines.append("---")
        lines.append("## 🔍 For AI Enhancement")
        lines.append("")
        lines.append("Use web search to find:")
        lines.append("- Weather forecast for each location/date")
        lines.append("- Top-rated cafes and restaurants near hotels")
        lines.append("- Local transit tips (airport to hotel, between islands)")
        lines.append("- Night markets and evening activities")
        lines.append("- Spa recommendations")
        lines.append("")

        # Collect all places and links for AI
        all_places = set()
        all_links = []
        for day_key in days:
            for booking in days[day_key]['bookings']:
                all_places.update(booking.get('places', []))
                all_links.extend(booking.get('links', []))
        for booking in unassigned:
            all_places.update(booking.get('places', []))
            all_links.extend(booking.get('links', []))

        if all_places:
            lines.append("**All Places Mentioned:**")
            lines.append(', '.join(sorted(all_places)))
            lines.append("")

        if all_links:
            lines.append("**All Booking Links:**")
            for link in list(set(all_links))[:10]:
                lines.append(f"- {link}")
            lines.append("")

        return "\n".join(lines)

    def generate_json_output(self, trip_name: str, days: dict, unassigned: list) -> dict:
        """Generate JSON output for AI processing."""
        def serialize_booking(b):
            return {
                'type': b['type'],
                'activity_name': b.get('activity_name'),
                'subject': b['subject'],
                'sender': b['sender'],
                'trip_date': b['trip_date'].isoformat() if b['trip_date'] else None,
                'booking_ref': b['booking_ref'],
                'time_info': b['time_info'],
                'location_info': b['location_info'],
                'location': b['location'],
                'links': b['links'],
                'places': b['places'],
                'has_pdf': b['has_pdf'],
                'pdf_filenames': b.get('pdf_filenames', [])
            }

        output = {
            'trip_name': trip_name,
            'generated_at': datetime.now().isoformat(),
            'days': {},
            'unassigned': [serialize_booking(b) for b in unassigned]
        }

        for day_key in sorted(days.keys()):
            day = days[day_key]
            if day['bookings']:
                output['days'][day_key] = {
                    'day_num': day['day_num'],
                    'display': day['display'],
                    'location': day.get('location'),
                    'location_display': day.get('location_display'),
                    'bookings': [serialize_booking(b) for b in day['bookings']]
                }

        return output


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Extract travel bookings from Gmail')
    parser.add_argument('--label', help='Gmail label to search')
    parser.add_argument('--query', help='Additional Gmail search query')
    parser.add_argument('--start', help='Trip start date (YYYY-MM-DD)')
    parser.add_argument('--end', help='Trip end date (YYYY-MM-DD)')
    parser.add_argument('--output', default='itinerary.md', help='Output markdown file')
    parser.add_argument('--json', help='Output JSON file for AI processing')
    parser.add_argument('--debug', action='store_true', help='Show debug info')
    parser.add_argument('--list-labels', action='store_true', help='List Gmail labels')

    args = parser.parse_args()

    extractor = TravelExtractor()

    print("Authenticating with Gmail...")
    if not extractor.authenticate():
        return

    if args.list_labels:
        print("\n--- Gmail Labels ---")
        for name, _ in sorted(extractor.get_labels()):
            print(f"  {name}")
        return

    if not args.label and not args.query:
        print("ERROR: Provide --label or --query")
        return

    print(f"\nSearching emails...")
    emails = extractor.search_emails(label=args.label, query=args.query)
    print(f"Found {len(emails)} emails")

    print("\nExtracting booking details...")
    bookings = extractor.process_emails(emails)
    print(f"Found {len(bookings)} booking confirmations")

    if args.debug:
        print("\n--- Bookings Found ---")
        for i, b in enumerate(bookings):
            print(f"{i+1}. [{b['type']}] {b.get('activity_name') or b['subject'][:40]}")
            print(f"   Date: {b['trip_date']}")
            print(f"   Location: {b['location']}")
            print(f"   Places: {b['places']}")
            print()

    # Generate itinerary
    if args.start and args.end:
        print(f"\nOrganizing by day ({args.start} to {args.end})...")
        days, unassigned = extractor.organize_by_day(bookings, args.start, args.end)
    else:
        # Default date range from bookings
        dates = [b['trip_date'] for b in bookings if b['trip_date']]
        if dates:
            start = min(dates)
            end = max(dates)
            print(f"\nInferred date range: {start.date()} to {end.date()}")
            days, unassigned = extractor.organize_by_day(
                bookings, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')
            )
        else:
            days = {'all': {'date': datetime.now(), 'day_num': 1, 'display': 'All Bookings', 'bookings': bookings}}
            unassigned = []

    trip_name = args.label or args.query or "My Trip"
    trip_name = trip_name.replace('-', ' ').replace('/', ' → ').title()

    # Generate markdown
    markdown = extractor.generate_detailed_itinerary(trip_name, days, unassigned)
    with open(args.output, 'w') as f:
        f.write(markdown)
    print(f"\nMarkdown itinerary saved to {args.output}")

    # Generate JSON if requested
    if args.json:
        json_data = extractor.generate_json_output(trip_name, days, unassigned)
        with open(args.json, 'w') as f:
            json.dump(json_data, f, indent=2, default=str)
        print(f"JSON data saved to {args.json}")


if __name__ == '__main__':
    main()
