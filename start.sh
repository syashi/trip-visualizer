#!/bin/bash

# Trip Visualizer - Startup Script
# Starts both Flask backend and React frontend

echo "🚀 Starting Trip Visualizer..."

# Start Flask backend
echo "📡 Starting Flask API on port 5000..."
cd "$(dirname "$0")"
source venv/bin/activate
python api.py &
FLASK_PID=$!

# Wait for Flask to start
sleep 2

# Start React frontend
echo "⚛️  Starting React frontend on port 5173..."
cd frontend
npm run dev &
VITE_PID=$!

echo ""
echo "✅ Trip Visualizer is running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend API: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
trap "echo '🛑 Stopping servers...'; kill $FLASK_PID $VITE_PID; exit" INT
wait
