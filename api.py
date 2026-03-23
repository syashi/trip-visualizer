"""
Flask API Backend for Trip Visualizer
Serves trip data from Gmail extraction to React frontend
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__, static_folder='frontend/dist')
CORS(app)

# Load trip data
def load_trip_data():
    """Load itinerary from JSON file"""
    try:
        with open('itinerary.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

@app.route('/api/trip-data', methods=['GET'])
def get_trip_data():
    """Get the current trip itinerary"""
    data = load_trip_data()
    if data:
        return jsonify(data)
    else:
        return jsonify({'error': 'No trip data found'}), 404

@app.route('/api/bookings/<booking_id>', methods=['PUT'])
def update_booking(booking_id):
    """Update a specific booking"""
    data = load_trip_data()
    if not data:
        return jsonify({'error': 'No trip data found'}), 404

    # Update logic here
    updates = request.json

    # Save back to file
    with open('itinerary.json', 'w') as f:
        json.dump(data, f, indent=2)

    return jsonify({'success': True, 'data': data})

@app.route('/api/bookings', methods=['POST'])
def create_booking():
    """Create a new booking"""
    data = load_trip_data()
    if not data:
        return jsonify({'error': 'No trip data found'}), 404

    new_booking = request.json
    day_key = new_booking.get('date')

    if day_key in data['days']:
        data['days'][day_key]['bookings'].append(new_booking)

    # Save back to file
    with open('itinerary.json', 'w') as f:
        json.dump(data, f, indent=2)

    return jsonify({'success': True, 'data': data})

@app.route('/api/bookings/<day_key>/<int:booking_index>', methods=['DELETE'])
def delete_booking(day_key, booking_index):
    """Delete a booking"""
    data = load_trip_data()
    if not data:
        return jsonify({'error': 'No trip data found'}), 404

    if day_key in data['days']:
        bookings = data['days'][day_key]['bookings']
        if 0 <= booking_index < len(bookings):
            bookings.pop(booking_index)

    # Save back to file
    with open('itinerary.json', 'w') as f:
        json.dump(data, f, indent=2)

    return jsonify({'success': True, 'data': data})

@app.route('/api/extract', methods=['POST'])
def trigger_extraction():
    """Trigger Gmail extraction with new parameters"""
    from travel_extractor import TravelExtractor

    params = request.json
    label = params.get('label')
    query = params.get('query')
    start_date = params.get('start_date')
    end_date = params.get('end_date')

    try:
        extractor = TravelExtractor()
        if extractor.authenticate():
            emails = extractor.search_emails(label=label, query=query)
            bookings = extractor.process_emails(emails)
            days, unassigned = extractor.organize_by_day(bookings, start_date, end_date)

            trip_data = {
                'trip_name': params.get('trip_name', 'My Trip'),
                'start_date': start_date,
                'end_date': end_date,
                'days': days,
                'unassigned': unassigned,
                'total_bookings': len(bookings),
                'total_days': len(days)
            }

            # Save to file
            with open('itinerary.json', 'w') as f:
                json.dump(trip_data, f, indent=2)

            return jsonify({'success': True, 'data': trip_data})
        else:
            return jsonify({'error': 'Gmail authentication failed'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve the React frontend"""
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
