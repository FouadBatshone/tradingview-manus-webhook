from flask import Flask, request, jsonify
import os
import json
import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return "TradingView Webhook Receiver is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Get webhook data
        data = request.json
        
        # Validate required fields
        if not data or 'strategy_name' not in data:
            return jsonify({"status": "error", "message": "Invalid webhook format"}), 400
        
        # Extract data
        strategy_name = data['strategy_name']
        metrics = data.get('metrics', {})
        parameters = data.get('parameters', {})
        
        # Create timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Log the received data
        print(f"Received webhook for {strategy_name} with metrics: {metrics} and parameters: {parameters}")
        
        return jsonify({
            "status": "success", 
            "message": "Webhook received and processed",
            "timestamp": timestamp,
            "strategy": strategy_name
        }), 200
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
