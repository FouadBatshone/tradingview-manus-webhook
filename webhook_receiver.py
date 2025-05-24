from flask import Flask, request, jsonify
import os
import json
import datetime
from flask_cors import CORS  # Added for CORS support

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

@app.route('/')
def home():
    return "TradingView Webhook Receiver is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Get webhook data
        data = request.json
        
        # Validate required fields
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
            
        print(f"Webhook received with data: {data}")
        
        return jsonify({
            "status": "success", 
            "message": "Webhook received and processed",
            "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        }), 200
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Simple test endpoint that accepts both GET and POST
@app.route('/test', methods=['GET', 'POST'])
def test():
    print("Test endpoint hit!")
    if request.method == 'POST':
        try:
            data = request.json
            print(f"Test endpoint received POST data: {data}")
        except:
            print("Test endpoint received POST but no JSON data")
    return "Test endpoint successful", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
