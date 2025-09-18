
import os
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

def get_market_data(symbol: str, interval: int, limit: int):
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

def get_account_balance(account_type: str):
    """Retrieves the current balance to calculate position sizes."""
    response = session.get_wallet_balance(accountType=account_type)
    return response

def place_market_order(symbol: str, side: str, qty: float):
    """Executes a trade."""
    response = session.place_order(
        category="spot",
        symbol=symbol,
        side=side,
        orderType="Market",
        qty=str(qty),
    )
    return response

def get_open_positions(symbol: str):
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
                        return float(wallet_balance)
        return 0.0
    except Exception as e:
        print(f"Error getting open positions for {symbol}: {e}")
        return 0.0


def close_position(symbol: str):
    """Places a market sell order to close the entire position of the base currency."""
    try:
        qty = get_open_positions(symbol)
        if qty > 0:
            # Bybit may have precision rules for order quantity.
            # This is a simplification. A real implementation would need to handle this.
            return place_market_order(
                symbol=symbol,
                side="Sell",
                qty=qty
            )
        return {"retCode": -1, "retMsg": "No open position to close."}
    except Exception as e:
        print(f"Error closing position for {symbol}: {e}")
        return {"retCode": -1, "retMsg": str(e)}
