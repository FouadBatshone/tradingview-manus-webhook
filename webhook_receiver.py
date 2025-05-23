from flask import Flask, request, jsonify
import os
import json
import datetime
import pandas as pd
import os.path
from pathlib import Path

app = Flask(__name__)

# Create directories if they don't exist
os.makedirs('tradingview_data', exist_ok=True)
os.makedirs('optimization_results', exist_ok=True)

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
        metrics = data['metrics']
        parameters = data['parameters']
        
        # Create timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw data to JSON file
        filename = f"tradingview_data/{strategy_name}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        # Update optimization history
        update_optimization_history(strategy_name, metrics, parameters)
        
        # Generate optimization suggestions if we have enough data
        generate_optimization_suggestions(strategy_name)
        
        return jsonify({"status": "success", "message": "Webhook received and processed"}), 200
    
    except Exception as e:
        # Log the error
        with open('error_log.txt', 'a') as f:
            f.write(f"{datetime.datetime.now()}: {str(e)}\n")
        return jsonify({"status": "error", "message": str(e)}), 500

def update_optimization_history(strategy_name, metrics, parameters):
    """Update the optimization history CSV file with new data"""
    history_file = f"tradingview_data/{strategy_name}_optimization_history.csv"
    
    # Create a row with timestamp, metrics, and parameters
    row = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'total_return_pct': metrics.get('total_return_pct', 0),
        'win_rate': metrics.get('win_rate', 0),
        'profit_factor': metrics.get('profit_factor', 0),
        'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
        'total_trades': metrics.get('total_trades', 0),
        'take_profit': parameters.get('take_profit', 0),
        'stop_loss': parameters.get('stop_loss', 0),
        'trailing_stop': parameters.get('trailing_stop', 0),
        'trailing_activation': parameters.get('trailing_activation', 0)
    }
    
    # Convert to DataFrame
    df_new = pd.DataFrame([row])
    
    # Append to existing file or create new one
    if os.path.exists(history_file):
        df_existing = pd.read_csv(history_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(history_file, index=False)
    else:
        df_new.to_csv(history_file, index=False)

def generate_optimization_suggestions(strategy_name):
    """Generate optimization suggestions based on historical performance"""
    history_file = f"tradingview_data/{strategy_name}_optimization_history.csv"
    
    # Only generate suggestions if we have enough data
    if not os.path.exists(history_file):
        return
    
    df = pd.read_csv(history_file)
    if len(df) < 3:  # Need at least 3 data points
        return
    
    # Find best performing parameters
    best_return_idx = df['total_return_pct'].idxmax()
    best_risk_adjusted_idx = df['profit_factor'].idxmax()
    
    # Get parameters for best return
    best_return_params = {
        'take_profit': df.loc[best_return_idx, 'take_profit'],
        'stop_loss': df.loc[best_return_idx, 'stop_loss'],
        'trailing_stop': df.loc[best_return_idx, 'trailing_stop'],
        'trailing_activation': df.loc[best_return_idx, 'trailing_activation']
    }
    
    # Get parameters for best risk-adjusted return
    best_risk_adjusted_params = {
        'take_profit': df.loc[best_risk_adjusted_idx, 'take_profit'],
        'stop_loss': df.loc[best_risk_adjusted_idx, 'stop_loss'],
        'trailing_stop': df.loc[best_risk_adjusted_idx, 'trailing_stop'],
        'trailing_activation': df.loc[best_risk_adjusted_idx, 'trailing_activation']
    }
    
    # Create exploratory parameters (slightly modified from best)
    exploratory_params = best_return_params.copy()
    exploratory_params['take_profit'] = float(exploratory_params['take_profit']) * 1.1  # 10% higher
    exploratory_params['stop_loss'] = float(exploratory_params['stop_loss']) * 0.9  # 10% lower
    
    # Generate Pine Script files with suggested parameters
    generate_pine_script(strategy_name, "best_return", best_return_params)
    generate_pine_script(strategy_name, "best_risk_adjusted", best_risk_adjusted_params)
    generate_pine_script(strategy_name, "exploratory", exploratory_params)
    
    # Generate visualization if we have enough data points
    if len(df) >= 5:
        generate_visualization(strategy_name, df)

def generate_pine_script(strategy_name, suggestion_type, parameters):
    """Generate a Pine Script file with suggested parameters"""
    # Use a string template instead of trying to read a file
    pine_script_template = """// TradingView Pine Script Template
// Optimized parameters for {strategy_name} - {suggestion_type}
// Generated on {date}

//@version=5
strategy("{strategy_name} - {suggestion_type}", overlay=true)

// Input parameters
takeProfit = {take_profit} // Optimized
stopLoss = {stop_loss} // Optimized
trailingStopPct = {trailing_stop} // Optimized
trailingActivationThreshold = {trailing_activation} // Optimized

// Your strategy logic goes here
// This is a placeholder template

// Example entry condition
longCondition = ta.crossover(ta.sma(close, 14), ta.sma(close, 28))
if (longCondition)
    strategy.entry("Long", strategy.long)
    
// Example exit with optimized parameters
strategy.exit("TP/SL", "Long", profit=takeProfit, loss=stopLoss, trail_points=trailingStopPct, trail_offset=trailingActivationThreshold)
"""
    
    # Format the template with parameters
    formatted_script = pine_script_template.format(
        strategy_name=strategy_name,
        suggestion_type=suggestion_type,
        date=datetime.datetime.now().strftime("%Y-%m-%d"),
        take_profit=parameters.get('take_profit', 5.0),
        stop_loss=parameters.get('stop_loss', 3.0),
        trailing_stop=parameters.get('trailing_stop', 1.0),
        trailing_activation=parameters.get('trailing_activation', 0.5)
    )
    
    # Save the new script to the optimization_results directory
    os.makedirs('optimization_results', exist_ok=True)
    output_file = f"optimization_results/{strategy_name}_{suggestion_type}_suggested.pine"
    with open(output_file, 'w') as f:
        f.write(formatted_script)

def generate_visualization(strategy_name, df):
    """Generate visualization of parameter impact on performance"""
    try:
        import matplotlib.pyplot as plt
        
        # Create a simple scatter plot of take_profit vs total_return
        plt.figure(figsize=(10, 6))
        plt.scatter(df['take_profit'], df['total_return_pct'], alpha=0.7)
        plt.title(f'{strategy_name} - Take Profit vs Total Return')
        plt.xlabel('Take Profit')
        plt.ylabel('Total Return %')
        plt.grid(True, alpha=0.3)
        
        # Save the plot
        plt.savefig(f"optimization_results/{strategy_name}_take_profit_analysis.png")
        
        # Create a simple scatter plot of stop_loss vs total_return
        plt.figure(figsize=(10, 6))
        plt.scatter(df['stop_loss'], df['total_return_pct'], alpha=0.7)
        plt.title(f'{strategy_name} - Stop Loss vs Total Return')
        plt.xlabel('Stop Loss')
        plt.ylabel('Total Return %')
        plt.grid(True, alpha=0.3)
        
        # Save the plot
        plt.savefig(f"optimization_results/{strategy_name}_stop_loss_analysis.png")
    
    except Exception as e:
        # Log visualization errors but don't fail
        with open('error_log.txt', 'a') as f:
            f.write(f"{datetime.datetime.now()}: Visualization error: {str(e)}\n")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
