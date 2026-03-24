"""
GitHub OAuth Authentication Module
Handles user authentication via GitHub OAuth for sharing itineraries.

Updated to integrate with trip_persistence module for preserving trip data
through the OAuth redirect flow.
"""

import streamlit as st
import requests
from urllib.parse import urlencode

# Import trip persistence module
try:
    import trip_persistence
    PERSISTENCE_AVAILABLE = True
except ImportError:
    PERSISTENCE_AVAILABLE = False


def get_oauth_config():
    """Get GitHub OAuth configuration from Streamlit secrets."""
    try:
        return {
            'client_id': st.secrets['github']['client_id'],
            'client_secret': st.secrets['github']['client_secret'],
            'redirect_uri': st.secrets['github'].get('redirect_uri', 'https://trip-visualizer.streamlit.app')
        }
    except Exception as e:
        st.error(f"⚠️ GitHub OAuth not configured: {e}")
        return None


def get_authorization_url(trip_data=None):
    """Generate GitHub OAuth authorization URL."""
    config = get_oauth_config()
    if not config:
        return None

    # Use simple state token - don't try to persist trip data (session clears on redirect)
    params = {
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'scope': 'repo',
        'state': 'trip_visualizer_oauth'  # Simple identifier
    }

    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


def exchange_code_for_token(code):
    """Exchange OAuth code for access token."""
    config = get_oauth_config()
    if not config:
        return None

    try:
        response = requests.post(
            'https://github.com/login/oauth/access_token',
            headers={'Accept': 'application/json'},
            data={
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'code': code,
                'redirect_uri': config['redirect_uri']
            }
        )

        if response.status_code == 200:
            data = response.json()
            return data.get('access_token')
        else:
            st.error(f"Failed to get access token: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error exchanging code: {e}")
        return None


def get_github_user(access_token):
    """Get GitHub user information."""
    try:
        response = requests.get(
            'https://api.github.com/user',
            headers={
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
        )

        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get user info: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error getting user info: {e}")
        return None


def handle_oauth_callback():
    """
    Handle OAuth callback from GitHub.

    This function:
    1. Exchanges the OAuth code for an access token
    2. Gets user info
    3. Stores auth in session state
    4. Sets flags for trip restoration (actual restoration happens in main app)

    The trip restoration happens via JavaScript redirect with the compressed
    trip data in the URL, which is then picked up by check_for_pending_trip_restore().
    """
    # Check for OAuth code in URL parameters
    query_params = st.query_params

    if 'code' in query_params:
        code = query_params['code']

        # Exchange code for token
        access_token = exchange_code_for_token(code)

        if access_token:
            # Get user info
            user_info = get_github_user(access_token)

            if user_info:
                # Store auth in session state
                st.session_state.github_token = access_token
                st.session_state.github_user = user_info.get('login')
                st.session_state.github_user_info = user_info

                # Flag that we need to restore trip data
                # The actual restoration happens in app.py main() after this
                st.session_state._needs_trip_restore = True
                st.session_state.show_share_after_oauth = True

                # Clear OAuth code from URL
                st.query_params.clear()

                # DON'T rerun yet - let the main app handle trip restoration first
                # The restoration JavaScript will trigger its own reload
                # st.rerun()  # Removed - causes race condition with JS


def is_authenticated():
    """Check if user is authenticated."""
    return 'github_token' in st.session_state and 'github_user' in st.session_state


def logout():
    """Log out the current user."""
    if 'github_token' in st.session_state:
        del st.session_state.github_token
    if 'github_user' in st.session_state:
        del st.session_state.github_user
    if 'github_user_info' in st.session_state:
        del st.session_state.github_user_info


def get_current_user():
    """Get current authenticated user's username."""
    return st.session_state.get('github_user', None)


def get_access_token():
    """Get current user's access token."""
    return st.session_state.get('github_token', None)
