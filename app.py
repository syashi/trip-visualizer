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

# Page config
st.set_page_config(
    page_title="Trip Visualizer",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* SF Pro Font Family - Apply to text only, not icons */
    body, p, span, div, input, textarea, select, button, h1, h2, h3, h4, h5, h6 {
        font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
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

    /* Accent elements - Use yellow from palette */
    [data-testid="stMain"] .highlight,
    [data-testid="stMain"] mark {
        background-color: #E8C547 !important;
        color: #2d2d2d !important;
    }

    /* Ensure metric labels and values use palette colors */
    [data-testid="stMain"] [data-testid="stMetricLabel"] {
        color: #6B9654 !important;  /* Green for labels */
        font-weight: 600 !important;
    }

    [data-testid="stMain"] [data-testid="stMetricValue"] {
        color: #4A7C9E !important;  /* Blue for values */
        font-weight: 700 !important;
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
        padding: 8px !important;
        margin-bottom: 12px !important;
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
}

# Initialize session state
if 'trip_data' not in st.session_state:
    st.session_state.trip_data = None
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'map'


def create_map(locations_sequence):
    """Create an interactive map with route markers."""
    if not locations_sequence:
        m = folium.Map(location=[41.9, 12.5], zoom_start=5)
        return m

    coords = []
    for loc in locations_sequence:
        if loc in LOCATION_COORDS:
            coords.append(LOCATION_COORDS[loc])

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


def generate_ical(trip_data):
    """Generate iCal file from trip data."""
    cal = Calendar()
    cal.add('prodid', '-//Trip Visualizer//EN')
    cal.add('version', '2.0')

    # Add all bookings
    all_bookings = []
    for day_info in trip_data.get('days', {}).values():
        all_bookings.extend(day_info.get('bookings', []))
    all_bookings.extend(trip_data.get('unassigned', []))

    for booking in all_bookings:
        event = Event()
        event.add('summary', booking.get('activity_name') or booking.get('subject', 'Booking'))

        trip_date = booking.get('trip_date')
        if trip_date:
            if isinstance(trip_date, str):
                try:
                    trip_date = datetime.fromisoformat(trip_date.replace('Z', '+00:00'))
                except:
                    continue
            event.add('dtstart', trip_date.date())
            event.add('dtend', trip_date.date())

        details = []
        if booking.get('sender'):
            details.append(f"Booked via: {booking['sender']}")
        if booking.get('booking_ref'):
            details.append(f"Confirmation: {booking['booking_ref']}")
        event.add('description', '\n'.join(details))
        cal.add_component(event)

    return cal.to_ical()


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
    <div style="background: white; border-radius: 12px; padding: 16px 50px 16px 16px; margin: 10px 0; border-left: 4px solid {config['color']}; position: relative; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
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

    # Show notes without warning icon - just display the information
    if notes:
        html += f'<div style="background: #e7f3ff; border-left: 3px solid #4A90A4; padding: 8px; margin-top: 8px; border-radius: 4px; font-size: 0.8rem; color: #004085;">{notes}</div>'

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

@st.dialog("➕ Add New Booking", width="medium")
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

        meeting_point = st.text_area("Address/Location", placeholder="Enter full address or location")

        booking_ref = st.text_input("Booking Reference", placeholder="e.g., ABC123456")

        status = st.selectbox("Status", options=['confirmed', 'pending', 'optional', 'cancelled'])

        notes = st.text_area("Notes", placeholder="Any special instructions or reminders")

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

        location_key = st.selectbox(
            "Location",
            options=list(LOCATION_COORDS.keys()),
            format_func=lambda x: LOCATION_COORDS[x]['name']
        )

        location_display = st.text_input(
            "Location Display Name",
            value=LOCATION_COORDS[location_key]['name'],
            help="Custom name to display for this location"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("➕ Add Day", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            # Create new day
            day_key = day_date.strftime('%Y-%m-%d')

            # Check if day already exists
            if day_key in st.session_state.trip_data['days']:
                st.error(f"Day {day_key} already exists!")
            else:
                # Find the right day number
                existing_days = list(st.session_state.trip_data['days'].keys())
                day_num = len(existing_days) + 1

                new_day = {
                    'day_num': day_num,
                    'display': day_date.strftime('%A, %B %d'),
                    'location': location_key,
                    'location_display': location_display,
                    'bookings': []
                }

                st.session_state.trip_data['days'][day_key] = new_day

                # Save to itinerary.json
                save_trip_data(st.session_state.trip_data)

                st.success(f"✅ Day {day_num} added successfully!")
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
        location_key = st.selectbox(
            "Location",
            options=list(LOCATION_COORDS.keys()),
            index=list(LOCATION_COORDS.keys()).index(day.get('location', 'phuket')) if day.get('location', 'phuket') in LOCATION_COORDS else 0,
            format_func=lambda x: LOCATION_COORDS[x]['name']
        )

        location_display = st.text_input(
            "Location Display Name",
            value=day.get('location_display', ''),
            help="Custom name to display for this location"
        )

        col1, col2 = st.columns(2)
        with col1:
            submit = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")
        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            # Update day data
            day['location'] = location_key
            day['location_display'] = location_display

            # Save to itinerary.json
            save_trip_data(st.session_state.trip_data)

            st.success("✅ Day updated successfully!")
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
    """Create a map showing locations for a specific day with activity markers."""
    location = day_data.get('location')

    if not location or location not in LOCATION_COORDS:
        # Fallback to basic map
        m = folium.Map(location=[13.7563, 100.5018], zoom_start=6)
        return m

    loc_coords = LOCATION_COORDS[location]

    # Get all bookings for this day
    bookings = day_data.get('bookings', [])

    # Calculate bounds to fit all markers
    all_lats = [loc_coords['lat']]
    all_lons = [loc_coords['lon']]

    # Add booking marker positions to bounds
    for idx, booking in enumerate(bookings):
        offset_lat = loc_coords['lat'] + (idx * 0.002)
        offset_lon = loc_coords['lon'] + (idx * 0.002)
        all_lats.append(offset_lat)
        all_lons.append(offset_lon)

    # Create map without initial zoom - we'll fit bounds instead
    m = folium.Map(location=[loc_coords['lat'], loc_coords['lon']])

    # Type icons and colors
    type_icons = {
        'hotels': {'emoji': '🏨', 'color': '#4ECDC4'},
        'flights': {'emoji': '✈️', 'color': '#FF6B6B'},
        'tours': {'emoji': '🎫', 'color': '#FFE66D'},
        'ferries': {'emoji': '⛴️', 'color': '#95E1D3'},
        'dining': {'emoji': '🍽️', 'color': '#F38181'},
        'spa': {'emoji': '💆', 'color': '#DDA0DD'},
    }

    # Add markers for each booking
    for idx, booking in enumerate(bookings):
        btype = booking.get('type', 'tours')
        activity_name = booking.get('activity_name', booking.get('subject', 'Activity'))
        config = type_icons.get(btype, {'emoji': '📋', 'color': '#888'})

        # For now, cluster all activities at the main location
        # In future, you could geocode addresses or add specific lat/lon to bookings
        # Add small random offset to show multiple markers
        offset_lat = loc_coords['lat'] + (idx * 0.002)
        offset_lon = loc_coords['lon'] + (idx * 0.002)

        # Create custom icon HTML with emoji
        icon_html = f'''
        <div style="
            background: {config['color']};
            color: white;
            border-radius: 50%;
            width: 38px;
            height: 38px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            border: 3px solid white;
            box-shadow: 0 3px 10px rgba(0,0,0,0.3);
        ">{config['emoji']}</div>
        '''

        # Popup content
        time_info = booking.get('time_info', {})
        time_str = time_info.get('start_time', '')
        loc_info = booking.get('location_info', {})
        address = loc_info.get('meeting_point', '')

        popup_html = f"""
        <div style="min-width: 200px;">
            <b>{activity_name}</b><br>
            {f'🕐 {time_str}<br>' if time_str else ''}
            {f'📍 {address[:50]}...<br>' if address else ''}
            <span style="background: {config['color']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 11px;">{btype.upper()}</span>
        </div>
        """

        folium.Marker(
            [offset_lat, offset_lon],
            popup=popup_html,
            icon=folium.DivIcon(html=icon_html, icon_size=(38, 38), icon_anchor=(19, 19))
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

        with st.expander(expander_label, expanded=should_expand):
            # Edit and Add buttons for this day with 10px gap
            col1, col2, spacer, col3 = st.columns([0.85, 0.05, 0.02, 0.05])
            with col1:
                st.markdown("")  # Spacer
            with col2:
                if st.button("✏️", key=f"edit_day_{day_key}", help="Edit day information"):
                    st.session_state.edit_day = day_key
                    show_edit_day_modal()
            with spacer:
                st.markdown("")  # 10px gap between buttons
            with col3:
                if st.button("➕", key=f"add_booking_{day_key}", help="Add a new booking to this day"):
                    st.session_state.add_booking_day = day_key
                    show_add_booking_modal()

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

            bookings = day.get('bookings', [])
            if bookings:
                for idx, booking in enumerate(bookings):
                    # Create unique key for this booking
                    booking_key = f"{day_key}_booking_{idx}"

                    # Render card and button side by side
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


@st.dialog("📤 Export Itinerary", width="medium")
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
    # Sidebar
    with st.sidebar:
        st.markdown("### Trip Visualizer")
        st.markdown("---")

        st.subheader("🔍 Search Your Trip")

        # Search method
        search_method = st.radio(
            "Search Method",
            ["Demo Mode", "Paste Itinerary", "Label", "Keywords"],
            horizontal=True,
            help="Demo Mode uses sample data, or paste your own itinerary, or search Gmail"
        )

        if search_method == "Demo Mode":
            st.info("📌 Demo mode uses pre-loaded sample data (Thailand trip)")
            search_input = "demo"
            search_label = None
            search_query = None
        elif search_method == "Paste Itinerary":
            st.markdown("### 📋 Paste Your Itinerary")
            st.info("💡 **Need to format your messy trip notes?** Use our AI conversion prompt below to structure your itinerary first, then paste the formatted result here.")

            # Expander with AI conversion prompt
            with st.expander("🤖 Get AI Conversion Prompt", expanded=False):
                st.markdown("""
                **How to use:**
                1. Click "Copy Prompt" below
                2. Paste into ChatGPT, Claude, or any AI assistant
                3. Add your messy trip notes at the bottom
                4. Copy the AI's formatted output
                5. Paste it into the text area below
                """)

                ai_prompt = """You are a trip planning assistant. Convert my messy travel information into a structured text format for Trip Visualizer.

**OUTPUT ONLY THE STRUCTURED TEXT - NO EXPLANATIONS**

**REQUIRED FORMAT:**

TRIP: [Trip Name]
DATES: [Month Day] - [Month Day, Year]

DAY [#] - [Month Day, Year] - [Location]
[Time] | [Type] | [Activity Name] | [Address/Meeting Point] | [Booking Platform #Reference] | [Status]
Notes: [Any special notes or instructions]

**BOOKING TYPES** (use exactly one): Hotel, Flight, Tour, Ferry, Dining, Spa

**SUPPORTED LOCATIONS**: Phuket, Krabi, Koh Samui, Bangkok, Phi Phi Islands, Koh Phangan, Chiang Mai, Paris, Versailles, Lyon, Vienna, Salzburg, Innsbruck, Hallstatt, Rome, Florence, Venice, Milan, London, Barcelona, Amsterdam

**STATUS** (use exactly one): Confirmed, Pending, Optional, Cancelled

**TIME FORMAT**: Use 12-hour format (e.g., "2:00 PM" or "9:30 AM - 4:00 PM")

**EXAMPLE:**
TRIP: Thailand Adventure
DATES: Dec 22 - Dec 28, 2025

DAY 1 - Dec 22, 2025 - Phuket
2:00 PM | Hotel | Grand Supicha Hotel | 48 Narisorn Road, Phuket Town | Booking.com #6450050149 | Confirmed
Notes: Check-in at 2 PM

DAY 2 - Dec 23, 2025 - Phuket
9:30 AM - 4:00 PM | Tour | Phi Phi Islands Snorkeling | Royal Phuket Marina | Tripadvisor #TRP12345 | Confirmed
Notes: Bring sunscreen and swimwear

---

NOW CONVERT MY TRIP INFORMATION BELOW:

[PASTE YOUR MESSY TRIP NOTES HERE]
"""

                if st.button("📋 Copy Prompt", key="copy_ai_prompt"):
                    st.code(ai_prompt, language="text")
                    st.success("✅ Prompt displayed above - copy it and paste into your AI assistant!")

            st.markdown("---")

            itinerary_input = st.text_area(
                "Paste Structured Itinerary",
                height=300,
                placeholder="""TRIP: Thailand Adventure
DATES: Dec 22 - Dec 28, 2025

DAY 1 - Dec 22, 2025 - Phuket
2:00 PM | Hotel | Grand Supicha Hotel | 48 Narisorn Road | Booking.com #6450050149 | Confirmed
Notes: Check-in at 2 PM

DAY 2 - Dec 23, 2025 - Phuket
9:30 AM - 4:00 PM | Tour | Phi Phi Snorkeling | Royal Marina | Tripadvisor TRP12345 | Confirmed
Notes: Bring sunscreen

DAY 3 - Dec 24, 2025 - Krabi
9:00 AM | Ferry | Speedboat to Krabi | Phuket Pier | 12Go ABA22847 | Confirmed
3:00 PM | Hotel | Aonang Villa Resort | Ao Nang | Booking.com | Confirmed
""",
                help="Paste your structured itinerary here. Use the AI prompt above if you need help formatting."
            )
            search_input = itinerary_input
            search_label = None
            search_query = None
        elif search_method == "Label":
            search_input = st.text_input(
                "Gmail Label",
                placeholder="e.g., Italy 2025",
                help="The Gmail label containing your bookings"
            )
            search_label = search_input
            search_query = None
        else:
            search_input = st.text_input(
                "Search Keywords",
                placeholder="e.g., Italy booking confirmation",
                help="Keywords to search in your emails"
            )
            search_label = None
            search_query = search_input

        # Only show date range and trip name for Gmail/Label/Keywords methods
        if search_method in ["Label", "Keywords"]:
            # Date range
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Start", value=datetime(2025, 5, 10))
            with col2:
                end_date = st.date_input("End", value=datetime(2025, 5, 20))

            # Trip name
            trip_name = st.text_input("Trip Name", value="My Trip", help="Display name")
        else:
            # For Demo Mode and Paste Itinerary, use defaults (will be overridden by data)
            start_date = datetime(2025, 5, 10)
            end_date = datetime(2025, 5, 20)
            trip_name = "My Trip"

        st.markdown("---")

        if st.button("🚀 Generate Itinerary", type="primary", use_container_width=True):
            if search_method == "Demo Mode" or (search_method == "Paste Itinerary" and search_input) or search_input:
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

                            # Use dates and name from JSON file
                            demo_trip_name = sample_data.get('trip_name', 'My Trip')
                            demo_start_date = sample_data.get('start_date', 'May 10, 2025')
                            demo_end_date = sample_data.get('end_date', 'May 20, 2025')

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
                                    st.info("💡 Tip: Use the AI prompt from README to structure your itinerary correctly")
                                else:
                                    st.session_state.trip_data = {
                                        'trip_name': parsed_data.get('trip_name', trip_name),
                                        'search_term': 'Pasted Itinerary',
                                        'start_date': parsed_data.get('start_date', start_date.strftime('%b %d, %Y')),
                                        'end_date': parsed_data.get('end_date', end_date.strftime('%b %d, %Y')),
                                        'days': days_dict,
                                        'unassigned': [],
                                        'total_bookings': sum(len(d.get('bookings', [])) for d in days_dict.values()),
                                        'total_days': len(days_dict)
                                    }
                                    st.success("✅ Itinerary parsed from text format!")
                                    st.rerun()
                        except Exception as e:
                            st.error(f"Error parsing itinerary: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())

                # Gmail mode
                else:
                    with st.spinner("Connecting to Gmail..."):
                        try:
                            extractor = TravelExtractor()
                            if extractor.authenticate():
                                with st.spinner("Searching emails..."):
                                    emails = extractor.search_emails(label=search_label, query=search_query)

                                if not emails:
                                    st.error(f"No emails found for '{search_input}'")
                                    st.stop()

                                st.success(f"Found {len(emails)} emails")

                                with st.spinner("Extracting bookings..."):
                                    bookings = extractor.process_emails(emails)

                                if not bookings:
                                    st.warning("No travel bookings detected in these emails")
                                    st.stop()

                                st.success(f"Extracted {len(bookings)} bookings")

                                days, unassigned = extractor.organize_by_day(
                                    bookings,
                                    start_date.strftime('%Y-%m-%d'),
                                    end_date.strftime('%Y-%m-%d')
                                )

                                st.session_state.trip_data = {
                                    'trip_name': trip_name,
                                    'search_term': search_input,
                                    'start_date': start_date.strftime('%b %d, %Y'),
                                    'end_date': end_date.strftime('%b %d, %Y'),
                                    'days': days,
                                    'unassigned': unassigned,
                                    'total_bookings': len(bookings),
                                    'total_days': (end_date - start_date).days + 1
                                }
                                st.rerun()
                            else:
                                st.error("Gmail authentication failed")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
            else:
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
            st.markdown(f'<p style="color: #8B7B68; font-size: 1.1rem; margin-top: 5px; margin-bottom: 20px;">{trip["start_date"]} → {trip["end_date"]}</p>', unsafe_allow_html=True)

        with col2:
            col_a, col_b = st.columns(2)
            with col_a:
                ical = generate_ical(trip)
                st.download_button("📅 Calendar", data=ical, file_name=f"{trip['trip_name']}.ics", mime="text/calendar")
            with col_b:
                # Export button that opens a dialog
                if st.button("📤 Export", key="export_btn", help="Export itinerary as PDF"):
                    st.session_state.show_export_dialog = True
                    show_export_dialog(trip)

        # Key Insights & Action Required Section - Side by Side
        insights_col, action_col = st.columns([1.2, 1], gap="large")

        with insights_col:
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

            # Show button to get web-based insights
            col_btn1, col_btn2 = st.columns([1, 1])
            with col_btn1:
                if st.button("🌐 Get Real-Time Insights", key="get_web_insights_btn", help="Get current weather, prices, and tips"):
                    st.session_state.show_insights_prompt = True

            with col_btn2:
                if st.session_state.custom_insights:
                    if st.button("↩️ Use Default Insights", key="reset_insights_btn"):
                        st.session_state.custom_insights = None
                        st.rerun()

            # Show prompt in expander if requested
            if 'show_insights_prompt' in st.session_state and st.session_state.show_insights_prompt:
                with st.expander("📋 Copy Prompt for AI", expanded=True):
                    prompt = generate_web_insights_prompt(trip)
                    st.markdown("**Instructions:**")
                    st.markdown("1. Copy the prompt below")
                    st.markdown("2. Paste into ChatGPT or Claude")
                    st.markdown("3. Copy the JSON response")
                    st.markdown("4. Paste below and click Load")

                    st.code(prompt, language="text")

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

        with action_col:
            st.markdown("### Action Required")

            # Detect issues in bookings
            issues = detect_booking_issues(trip)

            if issues:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #ffe8e8 0%, #ffeded 100%);
                     border: none;
                     border-radius: 12px;
                     padding: 12px;
                     margin-bottom: 12px;">
                    <div style="color: #868e96; font-size: 13px;">{len(issues)} booking issue{"s" if len(issues) > 1 else ""} found. Click cards to jump to day.</div>
                </div>
                """, unsafe_allow_html=True)

                # Show issue details as clickable cards
                issues_to_show = issues[:3] if len(issues) > 3 else issues

                for idx, issue in enumerate(issues_to_show):
                    day_num = issue.get('day_num', 'N/A')
                    booking_name = issue.get('booking_name', 'Unknown')
                    issue_text = issue.get('issue', '')
                    day_key = issue.get('day_key', None)

                    # Compact single-line format with issue text inline
                    compact_text = f"⚠️ Day {day_num} • {booking_name[:25]}{'...' if len(booking_name) > 25 else ''} • {issue_text[:35]}{'...' if len(issue_text) > 35 else ''}"

                    # Make entire card clickable using st.button - full width but left aligned content
                    if st.button(
                        compact_text,
                        key=f"issue_card_{idx}",
                        help=f"Click to jump to Day {day_num}",
                        use_container_width=True
                    ):
                        # Store the target day and switch to map view to see the accordion
                        st.session_state.jump_to_day = day_key
                        st.session_state.view_mode = 'map'
                        st.rerun()

                if len(issues) > 3:
                    with st.expander(f"➕ Show {len(issues) - 3} more issue{'s' if len(issues) - 3 > 1 else ''}"):
                        for idx_more, issue in enumerate(issues[3:], start=3):
                            day_num = issue.get('day_num', 'N/A')
                            booking_name = issue.get('booking_name', 'Unknown')
                            issue_text = issue.get('issue', '')
                            day_key = issue.get('day_key', None)

                            # Use same button format as above
                            compact_text = f"⚠️ Day {day_num} • {booking_name[:25]}{'...' if len(booking_name) > 25 else ''} • {issue_text[:35]}{'...' if len(issue_text) > 35 else ''}"

                            if st.button(
                                compact_text,
                                key=f"issue_card_{idx_more}",
                                help=f"Click to jump to Day {day_num}",
                                use_container_width=True
                            ):
                                # Store the target day and switch to map view
                                st.session_state.jump_to_day = day_key
                                st.session_state.view_mode = 'map'
                                st.rerun()

        st.markdown("---")

        # Warning if all bookings are unassigned
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

        # View toggle - minimal spacing between buttons
        view_col1, view_col2, view_col3 = st.columns([1, 1, 3.9])
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
            col1, col2 = st.columns([3, 2], gap="large")

            with col1:
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

            with col2:
                render_day_by_day_view(trip)

        else:  # journey view
            render_illustrative_view(trip)

    else:
        # Welcome screen
        st.markdown("## ✈️ Welcome to Trip Visualizer")
        st.markdown("Transform your Gmail booking confirmations into a beautiful visual itinerary.")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            ### 📧 Step 1
            Enter a Gmail label or search keywords
            """)
        with col2:
            st.markdown("""
            ### 📅 Step 2
            Set your trip dates
            """)
        with col3:
            st.markdown("""
            ### 🗺️ Step 3
            View your visual itinerary
            """)

        st.info("👈 Use the sidebar to search for your trip")

        # Demo map
        st.markdown("### Preview")
        demo_map = create_map(['rome', 'florence', 'venice', 'milan'])
        st_folium(demo_map, width=None, height=400)


if __name__ == "__main__":
    main()
