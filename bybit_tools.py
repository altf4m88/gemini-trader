
import os
import math
from dotenv import load_dotenv
from pybit.unified_trading import HTTP
import pandas as pd

load_dotenv()

session = HTTP(
    testnet=False,
    demo=True,
    api_key=os.environ.get("BYBIT_API_KEY_TESTNET"),
    api_secret=os.environ.get("BYBIT_API_SECRET_TESTNET"),
    timeout=30,
)

def spot_get_market_data(symbol: str, interval: int, limit: int):
    """Fetches historical OHLCV data and returns it as a pandas DataFrame."""
    response = session.get_kline(
        category="spot",
        symbol=symbol,
        interval=interval,
        limit=limit
    )

    if response['retCode'] == 0 and 'list' in response['result']:
        data = response['result']['list']
        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
        
        # Convert timestamp to datetime (fix deprecation warning by converting to int first)
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Convert string values to numeric (float) for OHLCV data
        numeric_columns = ["open", "high", "low", "close", "volume", "turnover"]
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Bybit returns data in ascending order (oldest first), so we reverse it
        return df.iloc[::-1]
    return pd.DataFrame()

def spot_get_account_balance(account_type: str):
    """Retrieves the current balance to calculate position sizes."""
    response = session.get_wallet_balance(accountType=account_type)
    return response

def spot_place_market_order(symbol: str, side: str, qty: float):
    """Executes a trade. For BUY orders, places a market order followed by a separate stop loss order."""
    if side.lower() == "buy":
        # Get the current market price to calculate stop loss
        market_data = spot_get_market_data(symbol, 1, 1)  # Get latest price
        if not market_data.empty:
            current_price = float(market_data.iloc[0]['close'])
            stop_loss_price = round(current_price * 0.9925, 4)  # 0.75% below entry price
            
        print(f"Placing BUY order for {symbol} at {current_price}")
        
        # First place the market order (without stop loss)
        response = session.place_order(
            category="spot",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=str(qty)
        )

        print(f"Market order response: {response}")
        
        # If market order is successful, place a separate stop loss order
        if response.get('retCode') == 0:
            print(f"Placing stop loss order at {stop_loss_price}")
            try:
                # Place a conditional sell order that triggers when price falls to stop_loss_price
                stop_loss_response = session.place_order(
                    category="spot",
                    symbol=symbol,
                    side="Sell",
                    orderType="Market",
                    qty=str(qty),
                    triggerPrice=str(stop_loss_price),
                    orderFilter="StopOrder"  # This makes it a conditional order
                )
                print(f"Stop loss order response: {stop_loss_response}")
            except Exception as e:
                print(f"Warning: Failed to place stop loss order: {e}")
                # Don't fail the main order if stop loss fails
        
        return response
    else:
        # For sell orders, execute normally
        response = session.place_order(
            category="spot",
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=str(qty),
        )
        return response

def spot_get_open_positions(symbol: str):
    """
    Checks the balance of the base currency for a given spot symbol.
    e.g., for BTCUSDT, it checks the BTC balance.
    """
    try:
        base_currency = symbol.replace("USDT", "")
        response = session.get_wallet_balance(
            accountType="UNIFIED",
            coin=base_currency
        )
        if response['retCode'] == 0 and 'list' in response['result']:
            if len(response['result']['list']) > 0:
                coin_info = response['result']['list'][0]['coin']
                if len(coin_info) > 0:
                    wallet_balance = coin_info[0].get('walletBalance', '0')
                    # Handle empty strings and convert to float safely
                    if wallet_balance and wallet_balance.strip():
                        balance = float(wallet_balance)
                        # Disregard balances under 1 as open positions
                        if balance >= 1.0:
                            return balance
        return 0.0
    except Exception as e:
        print(f"Error getting open positions for {symbol}: {e}")
        return 0.0


def spot_close_position(symbol: str):
    """Places a market sell order to close the entire position of the base currency."""
    try:
        qty = spot_get_open_positions(symbol)
        if qty > 0:
            # Round quantity down to appropriate decimal places based on symbol
            # Most altcoins like XRP typically use 0-4 decimal places
            if "XRP" in symbol or "ADA" in symbol or "DOGE" in symbol:
                # For lower-priced coins, round down to whole numbers
                rounded_qty = math.floor(qty)  # Round down to whole numbers
            elif "BTC" in symbol or "ETH" in symbol:
                # For higher-priced coins, round down to 6 decimal places
                rounded_qty = math.floor(qty * 1000000) / 1000000  # Round down to 6 decimals
            else:
                # Default to 4 decimal places for most other coins, round down
                rounded_qty = math.floor(qty * 10000) / 10000  # Round down to 4 decimals
            
            print(f"Original quantity: {qty}, Rounded down quantity: {rounded_qty}")
            
            return spot_place_market_order(
                symbol=symbol,
                side="Sell",
                qty=str(rounded_qty)
            )
        return {"retCode": -1, "retMsg": "No open position to close."}
    except Exception as e:
        print(f"Error closing position for {symbol}: {e}")
        return {"retCode": -1, "retMsg": str(e)}
