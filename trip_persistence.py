"""
Trip Persistence Module
Handles saving and restoring trip data through OAuth redirects using browser localStorage.

This solves the problem of Streamlit session state being cleared on OAuth redirects.
The trip data is stored in browser localStorage before redirect and restored after.

Architecture:
1. Before OAuth: JavaScript saves trip to localStorage, then redirects
2. After OAuth: JavaScript reads localStorage and triggers a Streamlit rerun with data in URL
3. Streamlit reads the data from URL query param and restores to session state

For large trips (>16KB compressed), we use a hash-based approach:
- Store full data in localStorage with a unique hash key
- Pass only the hash in the URL
- JavaScript reads the full data from localStorage using the hash

The key insight is that we use the URL as a bridge between JavaScript and Python.
"""

import streamlit as st
import streamlit.components.v1 as components
import json
import base64
import zlib
import hashlib
from datetime import datetime

# Storage key for localStorage
LOCALSTORAGE_KEY = "trip_visualizer_pending_trip"
RESTORE_FLAG_KEY = "restore_pending"
RESTORE_HASH_KEY = "restore_hash"

# Max size for URL-embedded data (be conservative)
MAX_URL_DATA_SIZE = 16000  # 16KB - safe for most browsers/servers


def compress_trip_data(trip_data):
    """Compress trip data for more efficient storage."""
    json_str = json.dumps(trip_data, separators=(',', ':'))  # Compact JSON
    compressed = zlib.compress(json_str.encode('utf-8'), level=9)
    b64 = base64.urlsafe_b64encode(compressed).decode('ascii')
    return b64


def decompress_trip_data(compressed_str):
    """Decompress trip data."""
    try:
        compressed = base64.urlsafe_b64decode(compressed_str.encode('ascii'))
        json_str = zlib.decompress(compressed).decode('utf-8')
        return json.loads(json_str)
    except Exception as e:
        print(f"Decompression error: {e}")
        return None


def get_trip_hash(trip_data):
    """Generate a short hash of trip data for identification."""
    json_str = json.dumps(trip_data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()[:12]


def create_oauth_button_with_persistence(trip_data, auth_url):
    """
    Create a GitHub OAuth button that saves trip data to localStorage before redirecting.

    This is the key function - it creates a JavaScript button that:
    1. Saves the trip data to localStorage
    2. Redirects to GitHub OAuth

    Args:
        trip_data: The trip data dict to persist
        auth_url: The GitHub OAuth authorization URL

    Returns:
        None (renders the component directly)
    """
    if not trip_data or not auth_url:
        st.error("Missing trip data or auth URL")
        return

    # Compress trip data for storage
    compressed_data = compress_trip_data(trip_data)

    # Create storage object with metadata
    storage_obj = {
        "data": compressed_data,
        "trip_name": trip_data.get('trip_name', 'My Trip'),
        "timestamp": datetime.now().isoformat(),
        "hash": get_trip_hash(trip_data)
    }

    # Escape for JavaScript
    storage_json = json.dumps(storage_obj)
    escaped_storage = storage_json.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')

    # Escape auth URL
    escaped_url = auth_url.replace("'", "\\'").replace('"', '\\"')

    # Create the button HTML with save-then-redirect logic
    button_html = f"""
    <style>
        .github-oauth-btn {{
            background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
            color: white;
            padding: 14px 28px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            width: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            transition: all 0.2s ease;
            box-shadow: 0 2px 8px rgba(35, 134, 54, 0.3);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        .github-oauth-btn:hover {{
            background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
        }}
        .github-oauth-btn:active {{
            transform: translateY(0);
        }}
        .github-oauth-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        .github-oauth-btn svg {{
            width: 22px;
            height: 22px;
            fill: currentColor;
        }}
        .oauth-status-msg {{
            text-align: center;
            margin-top: 12px;
            font-size: 14px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            min-height: 20px;
        }}
        .status-saving {{ color: #f0ad4e; }}
        .status-success {{ color: #238636; }}
        .status-error {{ color: #da3633; }}
        .spinner {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff40;
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
            margin-right: 8px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>

    <button class="github-oauth-btn" id="github-oauth-btn" onclick="saveAndRedirect()">
        <svg viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
        </svg>
        Sign in with GitHub
    </button>
    <div class="oauth-status-msg" id="oauth-status"></div>

    <script>
        function saveAndRedirect() {{
            var btn = document.getElementById('github-oauth-btn');
            var status = document.getElementById('oauth-status');

            // Disable button and show saving state
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner"></span> Saving trip...';
            status.className = 'oauth-status-msg status-saving';
            status.textContent = 'Saving your trip data before sign-in...';

            try {{
                // Save trip data to localStorage
                var tripData = '{escaped_storage}';
                localStorage.setItem('{LOCALSTORAGE_KEY}', tripData);

                // Verify save
                var verify = localStorage.getItem('{LOCALSTORAGE_KEY}');
                if (!verify) {{
                    throw new Error('Failed to save - localStorage may be disabled');
                }}

                // Success - redirect to OAuth
                status.className = 'oauth-status-msg status-success';
                status.textContent = 'Trip saved! Redirecting to GitHub...';
                btn.innerHTML = '<span class="spinner"></span> Redirecting...';

                // Short delay to show success, then redirect
                setTimeout(function() {{
                    window.location.href = '{escaped_url}';
                }}, 400);

            }} catch (e) {{
                console.error('Save error:', e);
                status.className = 'oauth-status-msg status-error';
                status.textContent = 'Error: ' + e.message;
                btn.disabled = false;
                btn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg> Sign in with GitHub';
            }}
        }}
    </script>
    """

    components.html(button_html, height=100)


def create_trip_restoration_component():
    """
    Create a component that checks localStorage for pending trip data
    and restores it to the app via URL parameter.

    This should be called early in the app, before any trip-dependent UI.

    The component:
    1. Checks if there's pending trip data in localStorage
    2. If found, triggers a page reload with the data in a URL parameter
    3. The main app reads the URL parameter and restores the trip

    Returns:
        str or None: The restored trip data (compressed) if available in URL
    """
    # Check if we have restored data in URL params
    query_params = st.query_params

    if RESTORE_FLAG_KEY in query_params:
        # We have data to restore!
        compressed_data = query_params.get(RESTORE_FLAG_KEY)

        # Clear the restore flag from URL
        st.query_params.clear()

        if compressed_data and compressed_data != 'true':
            # Decompress and return
            trip_data = decompress_trip_data(compressed_data)
            if trip_data:
                return trip_data

    # Inject JavaScript to check localStorage and restore if needed
    # This only runs if we just came back from OAuth (have github_token but no trip)
    should_check = (
        st.session_state.get('github_token') is not None and
        (st.session_state.get('trip_data') is None or
         st.session_state.get('_needs_trip_restore', False))
    )

    if should_check:
        restore_js = f"""
        <script>
            (function() {{
                try {{
                    var stored = localStorage.getItem('{LOCALSTORAGE_KEY}');
                    if (stored) {{
                        var storageObj = JSON.parse(stored);
                        if (storageObj && storageObj.data) {{
                            // Clear localStorage to prevent double-restore
                            localStorage.removeItem('{LOCALSTORAGE_KEY}');

                            // Reload page with restore flag
                            var currentUrl = window.location.href.split('?')[0];
                            var newUrl = currentUrl + '?{RESTORE_FLAG_KEY}=' + encodeURIComponent(storageObj.data);

                            console.log('Restoring trip, redirecting...');
                            window.location.href = newUrl;
                        }}
                    }}
                }} catch (e) {{
                    console.error('Trip restore error:', e);
                }}
            }})();
        </script>
        """
        components.html(restore_js, height=0)

    return None


def check_for_pending_trip_restore():
    """
    Check URL parameters for pending trip restoration.
    Call this at the very start of the app.

    Handles two restoration methods:
    1. Direct data in URL (small trips) - restore_pending=<compressed_data>
    2. Hash-based (large trips) - restore_hash=<hash> (data is in localStorage)

    Returns:
        dict or None: The trip data if restoration is needed, None otherwise
    """
    query_params = st.query_params

    # Method 1: Check for direct data in URL (small trips)
    if RESTORE_FLAG_KEY in query_params:
        compressed_data = query_params.get(RESTORE_FLAG_KEY)

        # Clear the restore param immediately
        new_params = {k: v for k, v in dict(query_params).items() if k != RESTORE_FLAG_KEY}
        st.query_params.clear()
        for k, v in new_params.items():
            st.query_params[k] = v

        if compressed_data:
            trip_data = decompress_trip_data(compressed_data)
            if trip_data:
                return trip_data

    # Method 2: Check for hash-based restoration (large trips)
    if RESTORE_HASH_KEY in query_params:
        trip_hash = query_params.get(RESTORE_HASH_KEY)

        # Clear the hash param
        new_params = {k: v for k, v in dict(query_params).items() if k != RESTORE_HASH_KEY}
        st.query_params.clear()
        for k, v in new_params.items():
            st.query_params[k] = v

        if trip_hash:
            # Mark that we need to read from localStorage
            st.session_state._pending_hash_restore = trip_hash
            # Inject JS to read localStorage and redirect with full data
            # We do a second redirect to get the actual data
            restore_js = f"""
            <script>
                (function() {{
                    var hash = '{trip_hash}';
                    var storageKey = 'trip_restore_' + hash;
                    var compressedData = localStorage.getItem(storageKey);

                    if (compressedData) {{
                        // Clear from localStorage
                        localStorage.removeItem(storageKey);

                        // Now redirect with the full data
                        var baseUrl = window.location.origin + window.location.pathname;
                        var restoreUrl = baseUrl + '?{RESTORE_FLAG_KEY}=' + encodeURIComponent(compressedData);
                        console.log('Hash restore: redirecting with full data');
                        window.location.replace(restoreUrl);
                    }} else {{
                        console.error('No data found for hash:', hash);
                    }}
                }})();
            </script>
            """
            components.html(restore_js, height=0)
            # Return None - the redirect will bring us back with actual data
            return None

    return None


def inject_trip_restore_listener():
    """
    Inject a JavaScript listener that checks localStorage after OAuth
    and triggers restoration.

    This should be called once per page load, before the OAuth callback handler.
    """
    js_code = f"""
    <script>
        (function() {{
            // Only run restoration logic if we're returning from OAuth
            // (URL has 'code' parameter or we just cleared it)
            var urlParams = new URLSearchParams(window.location.search);
            var hasOAuthCode = urlParams.has('code');
            var hasRestoreFlag = urlParams.has('{RESTORE_FLAG_KEY}');

            // Don't run if we already have a restore flag
            if (hasRestoreFlag) return;

            // Check for stored trip data
            var stored = localStorage.getItem('{LOCALSTORAGE_KEY}');
            if (stored && hasOAuthCode) {{
                console.log('Found stored trip data, will restore after OAuth completes');
                // Set a flag for post-OAuth restoration
                sessionStorage.setItem('trip_restore_pending', 'true');
            }}
        }})();
    </script>
    """
    components.html(js_code, height=0)


def handle_post_oauth_restore():
    """
    Handle trip restoration after OAuth callback is processed.
    Call this AFTER the OAuth callback handler.

    For small trips: embeds compressed data directly in URL
    For large trips: keeps data in localStorage, passes only a hash in URL,
                    then uses a two-step process to restore

    Returns:
        dict or None: The restored trip data, or None if no restoration needed
    """
    # If we just completed OAuth and don't have trip data, trigger restoration
    if (st.session_state.get('github_token') and
            not st.session_state.get('trip_data') and
            not st.session_state.get('_restoration_attempted')):

        st.session_state._restoration_attempted = True

        # Inject JS to restore from localStorage
        # This version handles both small (URL) and large (hash) trips
        restore_js = f"""
        <script>
            (function() {{
                var stored = localStorage.getItem('{LOCALSTORAGE_KEY}');
                if (stored) {{
                    try {{
                        var storageObj = JSON.parse(stored);
                        if (storageObj && storageObj.data) {{
                            var compressedData = storageObj.data;
                            var baseUrl = window.location.origin + window.location.pathname;

                            // Check if data is small enough for URL
                            if (compressedData.length < {MAX_URL_DATA_SIZE}) {{
                                // Small trip - embed data in URL
                                localStorage.removeItem('{LOCALSTORAGE_KEY}');
                                var restoreUrl = baseUrl + '?{RESTORE_FLAG_KEY}=' + encodeURIComponent(compressedData);
                                console.log('Restoring small trip via URL (' + compressedData.length + ' bytes)');
                                window.location.replace(restoreUrl);
                            }} else {{
                                // Large trip - use hash approach
                                // Keep data in localStorage with hash key
                                var hash = storageObj.hash || 'trip_' + Date.now();
                                localStorage.setItem('trip_restore_' + hash, compressedData);
                                localStorage.removeItem('{LOCALSTORAGE_KEY}');

                                var restoreUrl = baseUrl + '?{RESTORE_HASH_KEY}=' + encodeURIComponent(hash);
                                console.log('Restoring large trip via hash (' + compressedData.length + ' bytes)');
                                window.location.replace(restoreUrl);
                            }}
                        }}
                    }} catch (e) {{
                        console.error('Restore error:', e);
                    }}
                }}
            }})();
        </script>
        """
        components.html(restore_js, height=0)

    return None


def clear_pending_trip():
    """Clear any pending trip data from localStorage."""
    js_code = f"""
    <script>
        localStorage.removeItem('{LOCALSTORAGE_KEY}');
    </script>
    """
    components.html(js_code, height=0)
