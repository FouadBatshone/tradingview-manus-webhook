from flask import Flask, request, jsonify
import os
import json
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from flask_cors import CORS  # Added for CORS support

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

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
        
        # Print received data for debugging
        print(f"Webhook received with data: {data}")
        
        # Validate required fields
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
            
        # Extract strategy name if available, otherwise use a default
        strategy_name = data.get('strategy_name', 'unknown_strategy')
        
        # Extract metrics and parameters if available
        metrics = data.get('metrics', {})
        parameters = data.get('parameters', {})
        
        # Create timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save raw data to JSON file
        filename = f"tradingview_data/{strategy_name}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        
        # Update optimization history if we have metrics and parameters
        if metrics and parameters:
            update_optimization_history(strategy_name, metrics, parameters)
            
            # Generate optimization suggestions
            generate_optimization_suggestions(strategy_name)
        else:
            # Generate a sample Pine Script for testing if no metrics/parameters
            generate_sample_pine_script(strategy_name)
        
        return jsonify({
            "status": "success", 
            "message": "Webhook received and processed",
            "timestamp": timestamp,
            "strategy": strategy_name,
            "data_saved": filename
        }), 200
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        # Log the error
        with open('tradingview_data/error_log.txt', 'a') as f:
            f.write(f"{datetime.datetime.now()}: {str(e)}\n")
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

def update_optimization_history(strategy_name, metrics, parameters):
    """Update the optimization history CSV file with new data"""
    history_file = f"tradingview_data/{strategy_name}_optimization_history.csv"
    
    # Create a row with timestamp, metrics, and parameters
    row = {
        'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Add metrics with proper error handling
    for key in ['total_return_pct', 'win_rate', 'profit_factor', 'max_drawdown_pct', 'total_trades']:
        if key in metrics:
            # Handle different formats from TradingView
            if isinstance(metrics[key], dict) and 'value' in metrics[key]:
                row[key] = float(metrics[key]['value'])
            elif isinstance(metrics[key], (int, float)):
                row[key] = float(metrics[key])
            else:
                try:
                    row[key] = float(metrics[key])
                except (ValueError, TypeError):
                    row[key] = 0
        else:
            row[key] = 0
    
    # Add parameters with proper error handling
    for key in ['take_profit', 'stop_loss', 'trailing_stop', 'trailing_activation']:
        if key in parameters:
            # Handle different formats from TradingView
            if isinstance(parameters[key], dict) and 'value' in parameters[key]:
                row[key] = float(parameters[key]['value'])
            elif isinstance(parameters[key], (int, float)):
                row[key] = float(parameters[key])
            else:
                try:
                    row[key] = float(parameters[key])
                except (ValueError, TypeError):
                    row[key] = 0
        else:
            row[key] = 0
    
    # Convert to DataFrame
    df_new = pd.DataFrame([row])
    
    # Append to existing file or create new one
    if os.path.exists(history_file):
        df_existing = pd.read_csv(history_file)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.to_csv(history_file, index=False)
    else:
        df_new.to_csv(history_file, index=False)
    
    print(f"Updated optimization history for {strategy_name}")

def generate_optimization_suggestions(strategy_name):
    """Generate optimization suggestions based on historical performance"""
    history_file = f"tradingview_data/{strategy_name}_optimization_history.csv"
    
    # Only generate suggestions if we have enough data
    if not os.path.exists(history_file):
        print(f"No history file found for {strategy_name}")
        generate_sample_pine_script(strategy_name)
        return
    
    df = pd.read_csv(history_file)
    if len(df) < 3:  # Need at least 3 data points
        print(f"Not enough data points for {strategy_name} (need at least 3, have {len(df)})")
        generate_sample_pine_script(strategy_name)
        return
    
    print(f"Generating optimization suggestions for {strategy_name} with {len(df)} data points")
    
    # Find best performing parameters
    best_return_idx = df['total_return_pct'].idxmax()
    
    # Calculate risk-adjusted return (profit_factor * win_rate / max_drawdown_pct)
    # Add small value to avoid division by zero
    df['risk_adjusted_return'] = df['profit_factor'] * df['win_rate'] / (df['max_drawdown_pct'] + 0.1)
    best_risk_adjusted_idx = df['risk_adjusted_return'].idxmax()
    
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
    
    # Save summary of suggestions
    summary = {
        "strategy_name": strategy_name,
        "data_points": len(df),
        "best_return": {
            "parameters": best_return_params,
            "metrics": {
                "total_return_pct": df.loc[best_return_idx, 'total_return_pct'],
                "win_rate": df.loc[best_return_idx, 'win_rate'],
                "profit_factor": df.loc[best_return_idx, 'profit_factor'],
                "max_drawdown_pct": df.loc[best_return_idx, 'max_drawdown_pct']
            }
        },
        "best_risk_adjusted": {
            "parameters": best_risk_adjusted_params,
            "metrics": {
                "total_return_pct": df.loc[best_risk_adjusted_idx, 'total_return_pct'],
                "win_rate": df.loc[best_risk_adjusted_idx, 'win_rate'],
                "profit_factor": df.loc[best_risk_adjusted_idx, 'profit_factor'],
                "max_drawdown_pct": df.loc[best_risk_adjusted_idx, 'max_drawdown_pct']
            }
        },
        "exploratory_suggestion": {
            "parameters": exploratory_params
        },
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with open(f"optimization_results/{strategy_name}_suggestions.json", 'w') as f:
        json.dump(summary, f, indent=4)
    
    print(f"Generated optimization suggestions for {strategy_name}")

def generate_sample_pine_script(strategy_name):
    """Generate a simple Pine Script file for testing"""
    pine_script = f"""// TradingView Pine Script Template
// Sample script for {strategy_name}
// Generated on {datetime.datetime.now().strftime("%Y-%m-%d")}

//@version=5
strategy("{strategy_name} - Sample", overlay=true)

// Input parameters
takeProfit = 5.0
stopLoss = 3.0
trailingStop = 1.5
trailingActivation = 2.0

// Example entry condition
longCondition = ta.crossover(ta.sma(close, 14), ta.sma(close, 28))
if (longCondition)
    strategy.entry("Long", strategy.long)
    
// Example exit with parameters
strategy.exit("TP/SL", "Long", profit=takeProfit, loss=stopLoss, trail_points=trailingStop, trail_offset=trailingActivation)
"""
    
    # Save the script to the optimization_results directory
    output_file = f"optimization_results/{strategy_name}_sample.pine"
    with open(output_file, 'w') as f:
        f.write(pine_script)
    
    print(f"Generated sample Pine Script for {strategy_name}")

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
    
    print(f"Generated Pine Script for {strategy_name} ({suggestion_type})")

def generate_visualization(strategy_name, df):
    """Generate visualization of parameter impact on performance"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs('optimization_results', exist_ok=True)
        
        # Create a figure with multiple subplots
        fig, axs = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'{strategy_name} - Parameter Impact Analysis', fontsize=16)
        
        # Plot 1: Take Profit vs Total Return
        axs[0, 0].scatter(df['take_profit'], df['total_return_pct'], alpha=0.7)
        axs[0, 0].set_title('Take Profit vs Total Return')
        axs[0, 0].set_xlabel('Take Profit')
        axs[0, 0].set_ylabel('Total Return %')
        axs[0, 0].grid(True, alpha=0.3)
        
        # Plot 2: Stop Loss vs Total Return
        axs[0, 1].scatter(df['stop_loss'], df['total_return_pct'], alpha=0.7)
        axs[0, 1].set_title('Stop Loss vs Total Return')
        axs[0, 1].set_xlabel('Stop Loss')
        axs[0, 1].set_ylabel('Total Return %')
        axs[0, 1].grid(True, alpha=0.3)
        
        # Plot 3: Trailing Stop vs Total Return
        axs[1, 0].scatter(df['trailing_stop'], df['total_return_pct'], alpha=0.7)
        axs[1, 0].set_title('Trailing Stop vs Total Return')
        axs[1, 0].set_xlabel('Trailing Stop')
        axs[1, 0].set_ylabel('Total Return %')
        axs[1, 0].grid(True, alpha=0.3)
        
        # Plot 4: Win Rate vs Profit Factor
        scatter = axs[1, 1].scatter(df['win_rate'], df['profit_factor'], 
                          c=df['total_return_pct'], cmap='viridis', 
                          alpha=0.7, s=100)
        axs[1, 1].set_title('Win Rate vs Profit Factor (color = Total Return)')
        axs[1, 1].set_xlabel('Win Rate')
        axs[1, 1].set_ylabel('Profit Factor')
        axs[1, 1].grid(True, alpha=0.3)
        fig.colorbar(scatter, ax=axs[1, 1], label='Total Return %')
        
        # Adjust layout and save
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        plt.savefig(f"optimization_results/{strategy_name}_parameter_analysis.png")
        
        # Create a correlation heatmap
        plt.figure(figsize=(10, 8))
        corr_columns = ['take_profit', 'stop_loss', 'trailing_stop', 'trailing_activation', 
                        'total_return_pct', 'win_rate', 'profit_factor', 'max_drawdown_pct']
        corr_df = df[corr_columns].corr()
        plt.imshow(corr_df, cmap='coolwarm', interpolation='none', aspect='auto')
        plt.colorbar(label='Correlation Coefficient')
        plt.title(f'{strategy_name} - Parameter Correlation Analysis', fontsize=14)
        plt.xticks(range(len(corr_columns)), corr_columns, rotation=45, ha='right')
        plt.yticks(range(len(corr_columns)), corr_columns)
        
        # Add correlation values
        for i in range(len(corr_columns)):
            for j in range(len(corr_columns)):
                plt.text(j, i, f'{corr_df.iloc[i, j]:.2f}', 
                        ha='center', va='center', 
                        color='white' if abs(corr_df.iloc[i, j]) > 0.5 else 'black')
        
        plt.tight_layout()
        plt.savefig(f"optimization_results/{strategy_name}_correlation_analysis.png")
        
        print(f"Generated visualization for {strategy_name}")
        
    except Exception as e:
        # Log visualization errors but don't fail
        print(f"Visualization error: {str(e)}")
        with open('tradingview_data/error_log.txt', 'a') as f:
            f.write(f"{datetime.datetime.now()}: Visualization error: {str(e)}\n")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
