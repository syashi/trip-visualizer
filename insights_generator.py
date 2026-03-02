# Dynamic Insights Generator for Trip Visualizer

from datetime import datetime
from typing import Dict, List
import json

# Weather data by month for different destinations
WEATHER_DATA = {
    # Europe
    'paris': {
        'spring': {'temp': '10-18°C', 'desc': 'Mild spring weather, occasional rain', 'icon': '🌸'},
        'summer': {'temp': '18-25°C', 'desc': 'Warm and pleasant, peak season', 'icon': '☀️'},
        'fall': {'temp': '10-18°C', 'desc': 'Cool and rainy, beautiful foliage', 'icon': '🍂'},
        'winter': {'temp': '3-8°C', 'desc': 'Cold with occasional snow', 'icon': '❄️'}
    },
    'vienna': {
        'spring': {'temp': '8-18°C', 'desc': 'Pleasant spring, blooming gardens', 'icon': '🌸'},
        'summer': {'temp': '18-26°C', 'desc': 'Warm, perfect for outdoor concerts', 'icon': '☀️'},
        'fall': {'temp': '8-16°C', 'desc': 'Cool autumn, cozy café season', 'icon': '🍂'},
        'winter': {'temp': '-2-5°C', 'desc': 'Cold with Christmas markets', 'icon': '❄️'}
    },
    'salzburg': {
        'spring': {'temp': '5-15°C', 'desc': 'Cool spring, mountain views', 'icon': '🌸'},
        'summer': {'temp': '15-24°C', 'desc': 'Warm, festival season', 'icon': '☀️'},
        'fall': {'temp': '5-15°C', 'desc': 'Cool autumn, fewer crowds', 'icon': '🍂'},
        'winter': {'temp': '-5-3°C', 'desc': 'Cold, snowy Alps nearby', 'icon': '❄️'}
    },
    'innsbruck': {
        'spring': {'temp': '5-16°C', 'desc': 'Cool spring, skiing still possible', 'icon': '🌸'},
        'summer': {'temp': '15-24°C', 'desc': 'Perfect hiking weather', 'icon': '☀️'},
        'fall': {'temp': '5-14°C', 'desc': 'Cool, beautiful mountain colors', 'icon': '🍂'},
        'winter': {'temp': '-5-2°C', 'desc': 'Snowy, prime skiing season', 'icon': '⛷️'}
    },
    # Thailand
    'phuket': {
        'all': {'temp': '26-32°C', 'desc': 'Hot and humid year-round', 'icon': '☀️'}
    },
    'bangkok': {
        'all': {'temp': '28-35°C', 'desc': 'Hot and humid, monsoon Jul-Oct', 'icon': '☀️'}
    }
}

# Key facts about destinations
DESTINATION_FACTS = {
    'paris': [
        {'icon': '🗼', 'text': 'Eiffel Tower sparkles every hour after sunset'},
        {'icon': '🥐', 'text': 'Best croissants found in local bakeries, not tourist spots'},
        {'icon': '🚇', 'text': 'Metro closes around 1 AM (2 AM weekends)'},
        {'icon': '💶', 'text': 'Most museums free on first Sunday of month'},
        {'icon': '🚶', 'text': 'Walking along the Seine is free and beautiful'}
    ],
    'versailles': [
        {'icon': '👑', 'text': 'Palace opens 9 AM - arrive early to beat crowds'},
        {'icon': '🌳', 'text': 'Gardens are massive - rent a bike or golf cart'},
        {'icon': '🎫', 'text': 'Book skip-the-line tickets online in advance'},
        {'icon': '🏰', 'text': "Marie Antoinette's estate is a hidden gem"}
    ],
    'vienna': [
        {'icon': '🎻', 'text': 'Classical music concerts daily - book in advance'},
        {'icon': '☕', 'text': 'Viennese coffee culture is UNESCO heritage'},
        {'icon': '🏛️', 'text': 'Schönbrunn Palace rivals Versailles in grandeur'},
        {'icon': '🎨', 'text': 'Many museums open late on Thursdays'},
        {'icon': '🚃', 'text': '72-hour transport pass covers most attractions'}
    ],
    'salzburg': [
        {'icon': '🎵', 'text': 'Sound of Music tour is iconic but touristy'},
        {'icon': '🏔️', 'text': 'Cable car up Untersberg offers stunning Alpine views'},
        {'icon': '🎭', 'text': 'Salzburg Festival in summer is world-famous'},
        {'icon': '🏰', 'text': 'Hohensalzburg Fortress offers panoramic city views'}
    ],
    'innsbruck': [
        {'icon': '⛷️', 'text': 'Skiing accessible year-round on Stubai Glacier'},
        {'icon': '🚡', 'text': 'Nordkette cable car takes you from city to 2,000m in 20 min'},
        {'icon': '🏔️', 'text': 'Hiking trails accessible directly from the city'},
        {'icon': '🏛️', 'text': 'Historic Old Town with Imperial Palace'}
    ],
    'lyon': [
        {'icon': '🍷', 'text': 'Food capital of France - try a bouchon restaurant'},
        {'icon': '🎨', 'text': 'Famous murals throughout the city'},
        {'icon': '🏛️', 'text': 'Vieux Lyon is a UNESCO World Heritage Site'},
        {'icon': '🚶', 'text': 'Traboules (secret passageways) are unique to Lyon'}
    ],
    'hallstatt': [
        {'icon': '📸', 'text': 'One of most photographed villages in Austria'},
        {'icon': '⛰️', 'text': 'Salt mine tours show 7,000 years of history'},
        {'icon': '🚢', 'text': 'Boat rides on the lake are stunning'},
        {'icon': '⚠️', 'text': 'Very crowded in summer - arrive early morning'}
    ],
    'phuket': [
        {'icon': '🏝️', 'text': 'Island hopping tours to Phi Phi are popular'},
        {'icon': '🌊', 'text': 'Best beaches: Kata, Karon (less crowded than Patong)'},
        {'icon': '🍜', 'text': 'Night markets offer cheap, delicious food'},
        {'icon': '💰', 'text': 'Tipping not expected but appreciated (10%)'}
    ],
    'bangkok': [
        {'icon': '🏯', 'text': 'Grand Palace requires modest dress (no shorts/tanks)'},
        {'icon': '🛺', 'text': 'Tuk-tuks are fun but negotiate price first'},
        {'icon': '🍜', 'text': 'Street food is safe, delicious, and incredibly cheap'},
        {'icon': '🚇', 'text': 'BTS Skytrain and MRT are best for getting around'}
    ]
}

def get_season(month: int) -> str:
    """Get season from month number."""
    if month in [3, 4, 5]:
        return 'spring'
    elif month in [6, 7, 8]:
        return 'summer'
    elif month in [9, 10, 11]:
        return 'fall'
    else:
        return 'winter'

def get_weather_insight(location: str, month: int) -> Dict:
    """Get weather insight for a location and month."""
    if location not in WEATHER_DATA:
        return None

    weather = WEATHER_DATA[location]
    if 'all' in weather:
        return weather['all']

    season = get_season(month)
    return weather.get(season)

def generate_insights(trip_data: Dict) -> List[Dict]:
    """Generate dynamic insights based on trip data."""
    insights = []

    if not trip_data or 'days' not in trip_data:
        return insights

    days = trip_data['days']

    # Extract unique locations
    locations = set()
    start_month = None

    for day_key, day_data in days.items():
        location = day_data.get('location', '')
        if location:
            locations.add(location)

        # Get start month from first day
        if not start_month:
            try:
                date_obj = datetime.strptime(day_key, '%Y-%m-%d')
                start_month = date_obj.month
            except:
                pass

    # Add weather insights for main locations
    if start_month:
        weather_added = 0
        for location in list(locations)[:2]:  # Top 2 locations
            weather = get_weather_insight(location, start_month)
            if weather and weather_added < 2:
                insights.append({
                    'icon': weather['icon'],
                    'text': f"**{location.title().replace('_', ' ')}:** {weather['desc']} ({weather['temp']})"
                })
                weather_added += 1

    # Add destination-specific facts
    for location in locations:
        if location in DESTINATION_FACTS:
            facts = DESTINATION_FACTS[location]
            # Add top 2 facts per location
            for fact in facts[:2]:
                insights.append(fact)

    # Add booking-specific insights
    booking_types = set()
    has_flights = False
    has_trains = False

    for day_data in days.values():
        for booking in day_data.get('bookings', []):
            booking_type = booking.get('type', '')
            booking_types.add(booking_type)

            if booking_type == 'flights':
                has_flights = True

            # Check for train mentions
            activity = booking.get('activity_name', '').lower()
            if 'train' in activity:
                has_trains = True

    # Flight insights
    if has_flights:
        insights.append({
            'icon': '✈️',
            'text': '**Airport arrival:** Arrive 2-3 hours early for international flights'
        })

    # Train insights for Europe
    if has_trains and any(loc in ['paris', 'vienna', 'salzburg', 'innsbruck', 'lyon'] for loc in locations):
        insights.append({
            'icon': '🚄',
            'text': '**Train travel:** Book seat reservations in advance for long routes'
        })

    # Multi-country insights
    if len(locations) > 3:
        insights.append({
            'icon': '🗺️',
            'text': '**Multi-city trip:** Keep copies of important documents'
        })

    # Ferry/boat insights
    if 'ferries' in booking_types:
        insights.append({
            'icon': '⛴️',
            'text': '**Ferry travel:** Check luggage limits (usually 20kg)'
        })

    # General travel tip
    insights.append({
        'icon': '💳',
        'text': '**Payment:** Notify your bank of travel dates to avoid card blocks'
    })

    return insights

def get_top_insights(insights: List[Dict], count: int = 5) -> List[Dict]:
    """Get top N insights to display."""
    return insights[:count]

def get_remaining_insights(insights: List[Dict], skip: int = 5) -> List[Dict]:
    """Get remaining insights for 'See More' section."""
    return insights[skip:]
