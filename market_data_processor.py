#!/usr/bin/env python3

import platform
import ssl
import websocket
from websocket_init import TastyworksSession
import json
import pandas as pd
from typing import List, Tuple, Any, Dict
from datetime import datetime, timedelta
import sys
from tabulate import tabulate
import yfinance as yf


class MarketDataProcessor:
    def __init__(self, token: str, symbols: List[str]):
        self.ws_url = 'wss://tasty-openapi-ws.dxfeed.com/realtime'
        self.channel_number = 3
        self.token = token
        self.symbols = symbols
        self.prev_close_prices = self.get_previous_close_prices()
        self.ws_client = MarketDataWebSocket(self.ws_url, self.token, self.channel_number)
        self.ws_client.set_prev_close_prices(self.prev_close_prices)
        self.columns_to_check = [
            'bidPrice', 'askPrice', 'bidSize', 'askSize', 
        ]
        self.numeric_columns = ['bidPrice', 'askPrice']

    def get_previous_close_prices(self) -> Dict[str, float]:
        """Fetch previous day's closing prices for all symbols."""
        prev_close_prices = {}
        for symbol in self.symbols:
            try:
                # Get yesterday's date
                yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
                # Fetch data using yfinance
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=yesterday)
                if not hist.empty:
                    prev_close_prices[symbol] = hist['Close'].iloc[-1]
                    print(f"Previous close for {symbol}: {prev_close_prices[symbol]}")
                else:
                    print(f"No data found for {symbol}")
                    prev_close_prices[symbol] = None
            except Exception as e:
                print(f"Error fetching previous close for {symbol}: {e}")
                prev_close_prices[symbol] = None
        return prev_close_prices

    def get_streamer_symbols(self) -> List[str]:
        """Retrieve symbols to track."""
        return self.symbols

    def parse_market_data(self, received_data: List[Tuple[str, List[Any]]]) -> pd.DataFrame:
        """Parse received WebSocket market data into a DataFrame."""
        parsed_data = []
        for item in received_data:
            feed_type, market_data = item
            for i in range(0, len(market_data), 6):
                if i + 5 < len(market_data):
                    parsed_data.append([
                        feed_type,
                        market_data[i],
                        market_data[i+1],
                        market_data[i+2],
                        market_data[i+3],
                        market_data[i+4],
                        market_data[i+5]
                    ])
        df_parsed = pd.DataFrame(parsed_data, columns=[
            'eventType', 'eventType2', 'streamer-symbol', 'bidPrice', 'askPrice', 'bidSize', 'askSize'
        ])
        return df_parsed.drop_duplicates(subset='streamer-symbol', keep='last')

    def convert_columns_to_numeric(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert specified columns to numeric, coercing errors."""
        for column in self.numeric_columns:
            df[column] = pd.to_numeric(df[column], errors='coerce')
        return df

    def reorder_columns(self, df: pd.DataFrame, new_columns: list) -> pd.DataFrame:
        """Reorder the DataFrame columns to place new columns at the end."""
        available_new_columns = [col for col in new_columns if col in df.columns]
        if len(available_new_columns) != len(new_columns):
            missing_columns = set(new_columns) - set(available_new_columns)
            print(f"Warning: Missing columns in DataFrame: {missing_columns}. Skipping them.")
        existing_columns = [col for col in df.columns if col not in available_new_columns]
        return df[existing_columns + available_new_columns]

    def calculate_performance_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate performance metrics based on previous close prices."""
        df['prev_close'] = df['streamer-symbol'].map(self.prev_close_prices)
        df['price_change'] = df['midPrice'] - df['prev_close']
        df['price_change_pct'] = (df['price_change'] / df['prev_close'] * 100).round(2)
        return df

    def process_market_data(self) -> pd.DataFrame:
        """Main function to process WebSocket market data."""
        symbols = self.get_streamer_symbols()
        print(f'Symbols: {symbols}')
        self.ws_client.set_symbols_to_track(symbols)
        self.ws_client.connect()

        # Parse received data
        df_parsed = self.parse_market_data(self.ws_client.received_data)

        # Process numeric columns
        df_parsed = self.convert_columns_to_numeric(df_parsed)

        # Calculate mid prices
        df_parsed = self.calculate_mid_prices(df_parsed)

        # Calculate performance metrics
        df_parsed = self.calculate_performance_metrics(df_parsed)

        # Reorder and return
        return self.reorder_columns(df_parsed, ['midPrice', 'prev_close', 'price_change', 'price_change_pct'])

    def calculate_mid_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate mid prices."""
        if 'bidPrice' in df.columns and 'askPrice' in df.columns:
            df['midPrice'] = (df['bidPrice'] + df['askPrice']) / 2
        else:
            print("Warning: 'bidPrice' or 'askPrice' not found. Skipping midPrice calculation.")
        return df


class MarketDataWebSocket:
    def __init__(self, ws_url: str, token: str, channel_number: int):
        self.ws_url = ws_url
        self.token = token
        self.channel_number = channel_number
        self.symbols_to_track = {}
        self.received_data = []
        self.prev_close_prices = {}

    def set_prev_close_prices(self, prev_close_prices: Dict[str, float]):
        """Set the previous closing prices for symbols."""
        self.prev_close_prices = prev_close_prices

    def connect(self):
        headers = {'Authorization': f'Bearer {self.token}'}
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            header=headers,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def on_open(self, ws):
        print("### connection opened ###")
        setup_message = {
            "type": "SETUP",
            "channel": 0,
            "version": "0.1-DXF-JS/0.3.0",
            "keepaliveTimeout": 120,
            "acceptKeepaliveTimeout": 120
        }
        ws.send(json.dumps(setup_message))

    def on_message(self, ws, message):
        data = json.loads(message)

        if data.get('type') == 'AUTH_STATE' and data.get('state') == 'UNAUTHORIZED':
            ws.send(json.dumps({"type": "AUTH", "channel": 0, "token": self.token}))
        elif data.get('type') == 'AUTH_STATE' and data.get('state') == 'AUTHORIZED':
            ws.send(json.dumps({
                "type": "CHANNEL_REQUEST",
                "channel": self.channel_number,
                "service": "FEED",
                "parameters": {"contract": "AUTO"}
            }))
        elif data.get('type') == 'CHANNEL_OPENED' and data.get('channel') == self.channel_number:
            ws.send(json.dumps({
                "type": "FEED_SETUP",
                "channel": self.channel_number,
                "acceptAggregationPeriod": 0.1,
                "acceptDataFormat": "COMPACT",
                "acceptEventFields": {
                    "Quote": ["eventType", "eventSymbol", "bidPrice", "askPrice", "bidSize", "askSize"]
                }
            }))
        elif data.get('type') == 'FEED_CONFIG' and data.get('channel') == self.channel_number:
            ws.send(json.dumps({
                "type": "FEED_SUBSCRIPTION",
                "channel": self.channel_number,
                "reset": True,
                "add": [{"type": "Quote", "symbol": symbol} for symbol in self.symbols_to_track]
            }))
        elif data.get('type') == 'FEED_DATA' and data.get('channel') == self.channel_number:
            feed_data = data['data']
            self.received_data.append(feed_data)
            
            feed_type, market_data = feed_data
            if feed_type == "Quote":
                # Process each quote
                for i in range(1, len(market_data), 6):
                    symbol = market_data[i]
                    bid_price = float(market_data[i+2])
                    ask_price = float(market_data[i+3])
                    mid_price = (bid_price + ask_price) / 2
                    
                    # Calculate deviation from previous close if available
                    if symbol in self.prev_close_prices and self.prev_close_prices[symbol] is not None:
                        prev_close = self.prev_close_prices[symbol]
                        price_change = mid_price - prev_close
                        price_change_pct = (price_change / prev_close * 100)
                        print(f"Symbol: {symbol}")
                        print(f"Bid Price: {bid_price:.2f}")
                        print(f"Ask Price: {ask_price:.2f}")
                        print(f"Mid Price: {mid_price:.2f}")
                        print(f"Previous Close: {prev_close:.2f}")
                        print(f"Change: {price_change:+.2f} ({price_change_pct:+.2f}%)")
                        print("---")
                    
                    if symbol in self.symbols_to_track:
                        self.symbols_to_track[symbol] = True

            if self.check_all_data_received():
                print("all tickers received at least once...")

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"### connection closed ### with status code: {close_status_code} and message: {close_msg}")

    def check_all_data_received(self):
        all_received = all(self.symbols_to_track.values())
        print(f"Check all data received: {all_received}")
        return all_received

    def set_symbols_to_track(self, symbols: List[str]):
        self.symbols_to_track = {symbol: False for symbol in symbols}
        print(f"Symbols to track initialized: {self.symbols_to_track}")


def px_flow(symbols: List[str]) -> MarketDataProcessor:
    """
    Create and return a MarketDataProcessor instance.
    """
    creds_path = "/Users/michaelkilchenmann/icloud/C_Code/J_Workbench/AA_Libraries_Mutual/creds.yaml" if platform.system() == "Darwin" else "/home/ec2-user/tt/creds.yaml"
    session = TastyworksSession()
    streamer_token = session.run()
    return MarketDataProcessor(streamer_token['data']['token'], symbols)

def main():
    # Define the symbols to retrieve prices for
    symbols = ["MSTR", "MSTU"]

    # Create a MarketDataProcessor instance
    processor = px_flow(symbols)

    # Process and retrieve market data
    prices = processor.process_market_data()

    ts = datetime.now()
    prices.insert(0, 'timestamp', ts)
    prices = prices[['timestamp', 'streamer-symbol', 'eventType', 'eventType2', 
                    'bidPrice', 'askPrice', 'midPrice', 'prev_close', 
                    'price_change', 'price_change_pct', 'bidSize', 'askSize']]
    prices.insert(10, 'bidoffer', prices['askPrice'] - prices['bidPrice'])
    prices.insert(11, 'bidoffer_pct', (prices['askPrice'] - prices['bidPrice'])/prices['midPrice']*100)
    prices.insert(12, 'bidoffer_bp', (prices['askPrice'] - prices['bidPrice'])/prices['midPrice']*10000)
    prices['bidoffer_pct'] = prices['bidoffer_pct'].round(2)
    prices['bidoffer_bp'] = prices['bidoffer_bp'].round(1)

    # Display the retrieved prices
    print("Retrieved Prices:")
    print(prices)
    # Display the retrieved prices as a formatted table
    print("Retrieved Prices:")
    print(tabulate(prices, headers='keys', tablefmt='pretty'))

if __name__ == "__main__":
    main() 