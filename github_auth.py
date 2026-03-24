"""
GitHub OAuth Authentication Module
Handles user authentication via GitHub OAuth for sharing itineraries.
"""

import streamlit as st
import requests
from urllib.parse import urlencode


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


def get_authorization_url():
    """Generate GitHub OAuth authorization URL."""
    config = get_oauth_config()
    if not config:
        return None

    params = {
        'client_id': config['client_id'],
        'redirect_uri': config['redirect_uri'],
        'scope': 'repo',
        'state': 'share_itinerary'  # CSRF protection
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
    """Handle OAuth callback from GitHub."""
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
                # Store in session state
                st.session_state.github_token = access_token
                st.session_state.github_user = user_info.get('login')
                st.session_state.github_user_info = user_info

                # Clear URL parameters
                st.query_params.clear()
                st.rerun()


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
