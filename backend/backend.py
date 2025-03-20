from flask import Flask, jsonify, request
from flask_cors import CORS
import yaml
import requests
import json
import numpy as np
import pandas as pd
import platform
from datetime import datetime
import sqlite3
import math
from ibkr_transactions import ib_transactions
import os
import sys
import time
import psutil
from decimal import Decimal
from pytz import timezone
from datetime import datetime
from options import OptionsClass

print("Working directory:", os.getcwd())
print("sys.path:", sys.path)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Allow all origins

ps = platform.system()

# if ps == "Darwin":
#     creds_file = "creds.yaml"
# if ps == "Linux":
#     creds_file = "/home/ec2-user/tt/creds.yaml"

# Get the directory where this script is located
base_dir = os.path.dirname(os.path.abspath(__file__))
creds_file = os.path.join(base_dir, "creds.yaml")
print(f"creds_file: {creds_file}")

# creds_file = "creds.yaml"  # Modify this if needed


try:
    with open(creds_file, "r") as file:
        print(f"Successfully opened {creds_file}", flush=True)
except FileNotFoundError:
    print(f"Error: {creds_file} not found", flush=True)
    raise

# Load credentials
with open(creds_file, "r") as file:
    data = yaml.safe_load(file)
    pw = data.get("pw")[0]
    user = data.get("user")[0]  

# Tastytrade API session URL
SESSION_URL = 'https://api.tastyworks.com/sessions'
TRANSACTIONS_URL = 'https://api.tastyworks.com/accounts/5WY49300/transactions'
print(f'SESSION_URL: {SESSION_URL}')
print(f'TRANSACTIONS_URL: {TRANSACTIONS_URL}')

def sanitize_data(data):
    # Recursively replace all NaN, Infinity, and -Infinity values with None
    if isinstance(data, float):
        if math.isnan(data) or math.isinf(data):
            return None
    elif isinstance(data, dict):
        return {k: sanitize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_data(v) for v in data]
    return data


def get_session_token():
    data = {
        "login": user,
        "password": pw,
        "remember-me": True
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(SESSION_URL, data=json.dumps(data), headers=headers)
    response.raise_for_status()
    session_data = response.json()
    return session_data['data']['session-token']

def get_tastytrade_transactions(session_token):
    headers = {
        'Authorization': session_token,
        'Content-Type': 'application/json'
    }
    response = requests.get(TRANSACTIONS_URL, headers=headers)
    response.raise_for_status()
    transactions_data = response.json()
    return pd.DataFrame(transactions_data['data']['items'])

def close_session(session_token):
    headers = {
        'Authorization': session_token,
        'Content-Type': 'application/json'
    }
    response = requests.delete(SESSION_URL, headers=headers)
    response.raise_for_status()

@app.route('/trades', methods=['GET'], strict_slashes=False)
def fetch_trades():
    try:
        print('Start Trade Feed Process...')
        # Get session token and transactions
        session_token = get_session_token()
        transactions_df = get_tastytrade_transactions(session_token)
        transactions_df = transactions_df[transactions_df['transaction-type'] == 'Trade']
        transactions_df['source'] = 'Tastytrade'
        close_session(session_token)
        # print(transactions_df.head())

        # Convert 'executed-at' timestamps from UTC to CT
        # transactions_df['executed-at'] = pd.to_datetime(transactions_df['executed-at']).dt.tz_convert('US/Central').dt.strftime('%Y-%m-%d %H:%M:%S.%3f')
        transactions_df['executed-at'] = pd.to_datetime(transactions_df['executed-at']) \
                .dt.tz_convert('US/Central') \
                .apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S.') + f"{x.microsecond // 1000:03d}")

        print('placeholder Close Potential Hung Session')
        for process in psutil.process_iter(['pid', 'name']):
            try:
                if 'python' in process.info['name'].lower():  # Check if the process is Python
                    for conn in psutil.net_connections(kind='inet'):  # Use net_connections
                        if conn.laddr.port == 4001 and conn.pid == process.info['pid']:  # Check port and PID match
                            print(f"Killing process {process.info['name']} (PID: {process.info['pid']}) on port 4001")
                            process.terminate()  # Terminate the process
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Skip processes that no longer exist or cannot be accessed
                continue
        
        # dfib['Time'] are CT timestamps, can you change the formatting to match this 

        try:
            dfib = pd.DataFrame()
            dfib = ib_transactions()
            dfib['source'] = 'IBKR'
            dfib.drop(columns=['Currency_y'], inplace=True)
            dfib['Time'] = pd.to_datetime(dfib['Time'], format='%Y%m%d  %H:%M:%S') \
                .dt.tz_localize('US/Central') \
                .apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S.') + f"{x.microsecond // 1000:03d}")
                    

            dfib.rename(columns={
                'Account': 'account-number',
                'Symbol': 'symbol',
                'SecType': 'instrument-type',
                'Currency_x': 'currency',
                'Action': 'action',
                'Quantity': 'quantity',
                'Price': 'price',
                'Time': 'executed-at',
                'Account': 'account-number',
                'ExecId': 'exec-id',
                'OrderId': 'order-id',
                'Exchange': 'exchange',
                'Liquidation': 'ext-group-id',
                'Commission': 'commission',
                # Add more column renames as needed
            }, inplace=True)
        except Exception as e:
            print(f"Error (IB Feed): {e}")
            dfib = pd.DataFrame()
            

        # dfub = pd.DataFrame()
        transactions_df = pd.concat([transactions_df, dfib], ignore_index=True)
        transactions_df.sort_values(by='executed-at', ascending=False, inplace=True)


        # Sanitize data to handle NaN, Infinity, and -Infinity
        transactions_json = transactions_df.to_dict(orient='records')
        sanitized_data = sanitize_data(transactions_json)

        # print(sanitized_data, flush=True)
        # print("This is a log message from Python!")
        return jsonify(sanitized_data)
    except Exception as e:
        return jsonify({"error": str(e)})


# myopt = OptionsClass()

@app.route('/option/init', methods=['GET'])
def option_init():
    global myopt
    try:
        myopt = OptionsClass()  # (Re)initialize the options object
        timestamp = datetime.now().isoformat()
        return jsonify({"result": "Option initialized", "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/option/get_total_pnl_tos', methods=['GET'])
def get_total_pnl_tos():
    try:
        result = myopt.get_total_pnl_tos()
        # Round and format with thousands separator
        rounded_result = format(round(float(result), 2), ',')
        timestamp = datetime.now().isoformat()
        return jsonify({"result": rounded_result, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/option/get_total_exposure', methods=['GET'])
def get_total_exposure():
    try:
        result = myopt.get_total_exposure()
        # Round and format with thousands separator
        rounded_result = format(round(float(result), 2), ',')
        timestamp = datetime.now().isoformat()
        return jsonify({"result": rounded_result, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/option/get_opt_exposure', methods=['GET'])
def get_opt_exposure():
    try:
        result = myopt.get_opt_exposure()
        # Round and format with thousands separator
        rounded_result = format(round(float(result), 2), ',')
        timestamp = datetime.now().isoformat()
        return jsonify({"result": rounded_result, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/option/get_hedge_pnl_tos', methods=['GET'])
def get_hedge_pnl_tos():
    try:
        result = myopt.get_hedge_pnl_tos()
        # Round and format with thousands separator
        rounded_result = format(round(float(result), 2), ',')
        timestamp = datetime.now().isoformat()
        return jsonify({"result": rounded_result, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/option/get_option_pnl_tos', methods=['GET'])
def get_option_pnl_tos():
    try:
        result = myopt.get_option_pnl_tos()
        # Round and format with thousands separator
        rounded_result = format(round(float(result), 2), ',')
        timestamp = datetime.now().isoformat()
        return jsonify({"result": rounded_result, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/option/push_hedge_trades', methods=['POST'])
def push_hedge_trades():
    try:
        myopt.push_hedge_trades_tos()
        timestamp = datetime.now().isoformat()
        return jsonify({"result": "push hedge trades executed", "timestamp": timestamp})
    except Exception as e:
        return jsonify({"error": str(e)})

# Toolbar action endpoints
@app.route('/toolbar/play', methods=['POST'])
def toolbar_play():
    try:
        # Placeholder functionality - would be replaced with actual implementation
        message = "Blotter active"
        print(f"TOOLBAR ACTION: {message}")
        timestamp = datetime.now().isoformat()
        return jsonify({"status": "success", "message": message, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/toolbar/pause', methods=['POST'])
def toolbar_pause():
    try:
        # Placeholder functionality - would be replaced with actual implementation
        message = "System paused"
        print(f"TOOLBAR ACTION: {message}")
        timestamp = datetime.now().isoformat()
        return jsonify({"status": "success", "message": message, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route('/toolbar/stop', methods=['POST'])
def toolbar_stop():
    try:
        # Placeholder functionality - would be replaced with actual implementation
        message = "System stopped"
        print(f"TOOLBAR ACTION: {message}")
        timestamp = datetime.now().isoformat()
        return jsonify({"status": "success", "message": message, "timestamp": timestamp})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

if __name__ == "__main__":
    app.run(port=5000, debug=True, use_reloader=False)
