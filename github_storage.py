"""
GitHub Storage Module
Handles saving itineraries to user's GitHub repository.
"""

import json
import requests
import re
from datetime import datetime


def sanitize_filename(trip_name):
    """Convert trip name to valid filename."""
    # Remove special characters, keep alphanumeric and spaces
    filename = re.sub(r'[^\w\s-]', '', trip_name.lower())
    # Replace spaces with hyphens
    filename = re.sub(r'[-\s]+', '-', filename)
    # Remove leading/trailing hyphens
    filename = filename.strip('-')
    # Add timestamp to ensure uniqueness
    timestamp = datetime.now().strftime('%Y%m%d')
    return f"{filename}-{timestamp}"


def create_repo_if_not_exists(username, access_token):
    """Create trip-visualizer-itineraries repo if it doesn't exist."""
    repo_name = 'trip-visualizer-itineraries'

    # Check if repo exists
    response = requests.get(
        f'https://api.github.com/repos/{username}/{repo_name}',
        headers={
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    )

    if response.status_code == 200:
        return True  # Repo already exists

    if response.status_code == 404:
        # Create the repo
        response = requests.post(
            'https://api.github.com/user/repos',
            headers={
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            },
            json={
                'name': repo_name,
                'description': 'Travel itineraries shared via Trip Visualizer',
                'private': False,
                'auto_init': True  # Create with README
            }
        )

        if response.status_code == 201:
            return True
        else:
            return False

    return False


def save_itinerary_to_github(trip_data, username, access_token):
    """
    Save itinerary JSON to user's GitHub repository.
    Returns: (success: bool, trip_id: str, error_message: str)
    """
    repo_name = 'trip-visualizer-itineraries'

    # Ensure repo exists
    if not create_repo_if_not_exists(username, access_token):
        return False, None, "Failed to create or access repository"

    # Generate filename from trip name
    trip_name = trip_data.get('trip_name', 'my-trip')
    trip_id = sanitize_filename(trip_name)
    filename = f"{trip_id}.json"

    # Prepare content
    content = json.dumps(trip_data, indent=2)

    # Check if file already exists (to get SHA for update)
    check_response = requests.get(
        f'https://api.github.com/repos/{username}/{repo_name}/contents/{filename}',
        headers={
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
    )

    # Prepare commit data
    import base64
    commit_data = {
        'message': f'Add itinerary: {trip_data.get("trip_name", "Trip")}',
        'content': base64.b64encode(content.encode()).decode(),
        'branch': 'main'
    }

    # If file exists, include SHA for update
    if check_response.status_code == 200:
        commit_data['sha'] = check_response.json()['sha']
        commit_data['message'] = f'Update itinerary: {trip_data.get("trip_name", "Trip")}'

    # Create or update file
    response = requests.put(
        f'https://api.github.com/repos/{username}/{repo_name}/contents/{filename}',
        headers={
            'Authorization': f'token {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        },
        json=commit_data
    )

    if response.status_code in [200, 201]:
        return True, trip_id, None
    else:
        error_msg = response.json().get('message', 'Unknown error')
        return False, None, f"Failed to save: {error_msg}"


def generate_shareable_link(username, trip_id):
    """Generate shareable link for the itinerary."""
    base_url = "https://trip-visualizer.streamlit.app"
    return f"{base_url}/?user={username}&trip={trip_id}"


def load_shared_itinerary(username, trip_id):
    """
    Load itinerary from a shared link.
    Returns: (success: bool, trip_data: dict, error_message: str)
    """
    repo_name = 'trip-visualizer-itineraries'
    filename = f"{trip_id}.json"

    try:
        # Fetch from GitHub raw content
        url = f"https://raw.githubusercontent.com/{username}/{repo_name}/main/{filename}"
        response = requests.get(url)

        if response.status_code == 200:
            trip_data = response.json()
            return True, trip_data, None
        else:
            return False, None, f"Could not load trip: {response.status_code}"
    except Exception as e:
        return False, None, f"Error loading trip: {str(e)}"
