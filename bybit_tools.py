
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
    Also calculates unrealized PnL based on current market price.
    e.g., for BTCUSDT, it checks the BTC balance and calculates PnL.
    Returns detailed position information similar to perp positions.
    """
    try:
        base_currency = symbol.replace("USDT", "")
        response = session.get_wallet_balance(
            accountType="UNIFIED",
            coin=base_currency
        )
        
        # Get current market price for PnL calculation
        market_data = spot_get_market_data(symbol, 1, 1)
        current_price = 0.0
        if not market_data.empty:
            current_price = float(market_data.iloc[0]['close'])
        
        position_info = {
            'symbol': symbol,
            'side': 'None',
            'size': 0.0,
            'avgPrice': 0.0,  # We don't track entry price for spot, would need separate tracking
            'markPrice': current_price,
            'unrealisedPnl': 0.0,  # Cannot calculate without entry price
            'leverage': '1',  # Spot has no leverage
            'positionValue': 0.0,
            'has_position': False,
            'trading_mode': 'spot'
        }
        
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
                            position_info.update({
                                'side': 'Buy',  # Spot positions are always long
                                'size': balance,
                                'positionValue': balance * current_price,
                                'has_position': True
                            })
                            print(f"Open SPOT position found: {balance} {base_currency} (${balance * current_price:.2f} value)")
                            print(f"Current Price: {current_price} (PnL calculation requires entry price tracking)")
                        else:
                            print(f"No significant SPOT position for {symbol} (balance: {balance})")
                    else:
                        print(f"No SPOT position for {symbol}")
                else:
                    print(f"No coin info found for {base_currency}")
            else:
                print(f"No balance data found for {base_currency}")
        else:
            print(f"Error getting balance for {base_currency}: {response.get('retMsg', 'Unknown error')}")
        
        return position_info
        
    except Exception as e:
        print(f"Error getting open spot positions for {symbol}: {e}")
        return {
            'symbol': symbol,
            'side': 'Error',
            'size': 0.0,
            'avgPrice': 0.0,
            'markPrice': 0.0,
            'unrealisedPnl': 0.0,
            'leverage': '1',
            'positionValue': 0.0,
            'has_position': False,
            'trading_mode': 'spot',
            'error': str(e)
        }


def spot_close_position(symbol: str):
    """Places a market sell order to close the entire position of the base currency."""
    try:
        position_info = spot_get_open_positions(symbol)
        
        if position_info is None or not position_info.get('has_position', False):
            return {"retCode": -1, "retMsg": "No open position to close."}
        
        qty = position_info['size']
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

# =============================================================================
# PERPETUAL FUTURES TRADING FUNCTIONS
# =============================================================================

def calculate_perp_tp_sl_prices(current_price: float, side: str, qty: float, target_loss_usd: float = 0.50, target_profit_usd: float = 1.00):
    """
    Calculate exact take profit and stop loss prices for perpetual futures.
    
    Args:
        current_price: Current market price
        side: 'Buy' or 'Sell'
        qty: Position quantity
        target_loss_usd: Target loss in USD (default: $0.50)
        target_profit_usd: Target profit in USD (default: $1.00)
    
    Returns:
        tuple: (stop_loss_price, take_profit_price)
    """
    # Calculate price per unit change in USD
    # For perpetuals: P&L = (exit_price - entry_price) * qty * contract_size
    # Assuming contract_size = 1 for most USDT perps
    
    if side.lower() == "buy":
        # For long positions
        # Stop loss: price needs to drop by target_loss_usd / qty
        stop_loss_price = current_price - (target_loss_usd / qty)
        # Take profit: price needs to rise by target_profit_usd / qty  
        take_profit_price = current_price + (target_profit_usd / qty)
    else:
        # For short positions
        # Stop loss: price needs to rise by target_loss_usd / qty
        stop_loss_price = current_price + (target_loss_usd / qty)
        # Take profit: price needs to drop by target_profit_usd / qty
        take_profit_price = current_price - (target_profit_usd / qty)
    
    # Round to appropriate decimal places
    stop_loss_price = round(stop_loss_price, 6)
    take_profit_price = round(take_profit_price, 6)
    
    return stop_loss_price, take_profit_price

def perp_get_market_data(symbol: str, interval: int, limit: int):
    """Fetches historical OHLCV data for perpetual futures and returns it as a pandas DataFrame."""
    response = session.get_kline(
        category="linear",  # linear = perpetual futures
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

def perp_get_account_balance(account_type: str):
    """Retrieves the current balance for perpetual futures trading to calculate position sizes."""
    response = session.get_wallet_balance(accountType=account_type)
    return response

def perp_place_market_order(symbol: str, side: str, qty: float, margin_usd: float = 50.0, leverage: int = 10):
    """
    Executes a perpetual futures trade with specific risk management.
    Automatically sets stop loss (-$0.50) and take profit ($1.00) based on position size.
    
    Args:
        symbol: Trading symbol (e.g., 'XRPUSDT')
        side: 'Buy' or 'Sell'
        qty: Quantity to trade (calculated based on $500 position size with 10x leverage)
        margin_usd: Margin amount in USD (default: $50)
        leverage: Leverage multiplier (default: 10x)
    """
    try:
        print(f"Placing {side} perpetual futures order for {symbol}")
        print(f"Quantity: {qty}, Margin: ${margin_usd}, Leverage: {leverage}x")
        print(f"Position Size: ${margin_usd * leverage}")
        
        # Get current market price for stop loss and take profit calculations
        market_data = perp_get_market_data(symbol, 1, 1)  # Get latest price
        if market_data.empty:
            return {"retCode": -1, "retMsg": "Could not retrieve market data for price calculations"}
        
        current_price = float(market_data.iloc[0]['close'])
        position_size_usd = margin_usd * leverage  # $500 with default settings
        
        # Calculate precise stop loss and take profit prices
        stop_loss_price, take_profit_price = calculate_perp_tp_sl_prices(
            current_price=current_price,
            side=side,
            qty=qty,
            target_loss_usd=0.50,
            target_profit_usd=1.00
        )
        
        print(f"Current Price: {current_price}")
        print(f"Stop Loss Price: {stop_loss_price} (Target Loss: -$0.50)")
        print(f"Take Profit Price: {take_profit_price} (Target Profit: $1.00)")
        
        # Validate that prices are reasonable (not negative, not too far from current price)
        if stop_loss_price <= 0 or take_profit_price <= 0:
            return {"retCode": -1, "retMsg": "Invalid stop loss or take profit price calculated"}
        
        # Check that stop loss and take profit are in the correct direction
        if side.lower() == "buy":
            if stop_loss_price >= current_price or take_profit_price <= current_price:
                return {"retCode": -1, "retMsg": "Invalid TP/SL direction for long position"}
        else:
            if stop_loss_price <= current_price or take_profit_price >= current_price:
                return {"retCode": -1, "retMsg": "Invalid TP/SL direction for short position"}
        
        # Place the market order for perpetual futures with TP/SL
        response = session.place_order(
            category="linear",  # linear = perpetual futures
            symbol=symbol,
            side=side,
            orderType="Market",
            qty=str(qty),
            positionIdx=0,  # 0 = one-way mode (not hedge mode)
            timeInForce="IOC",  # Immediate or Cancel for market orders
            takeProfit=str(take_profit_price),  # Set take profit price
            stopLoss=str(stop_loss_price),      # Set stop loss price
            tpTriggerBy="LastPrice",            # Trigger TP by last price
            slTriggerBy="LastPrice",            # Trigger SL by last price
            tpslMode="Full",                    # Full position TP/SL
            tpOrderType="Market",               # Market order when TP triggers
            slOrderType="Market"                # Market order when SL triggers
        )

        print(f"Perpetual futures order response: {response}")
        
        # If the order is successful, log the details
        if response.get('retCode') == 0:
            order_id = response['result']['orderId']
            print(f"Order placed successfully. Order ID: {order_id}")
            print(f"Stop Loss set at {stop_loss_price} (Max Loss: $0.50)")
            print(f"Take Profit set at {take_profit_price} (Target Profit: $1.00)")
        else:
            print(f"Order failed with error: {response.get('retMsg')}")
            
        return response
        
    except Exception as e:
        print(f"Error placing perpetual futures order for {symbol}: {e}")
        return {"retCode": -1, "retMsg": str(e)}

def perp_get_open_positions(symbol: str):
    """
    Checks for open perpetual futures positions for a given symbol.
    Returns position information including size, side, and unrealized PnL.
    Always returns position info even if no position is open.
    """
    try:
        response = session.get_positions(
            category="linear",  # linear = perpetual futures
            symbol=symbol
        )
        
        if response['retCode'] == 0 and 'list' in response['result']:
            positions = response['result']['list']
            
            # Check if there are any open positions
            for position in positions:
                position_size = float(position.get('size', '0'))
                
                position_info = {
                    'symbol': position.get('symbol', symbol),
                    'side': position.get('side', 'None'),
                    'size': position_size,
                    'avgPrice': float(position.get('avgPrice', '0')),
                    'markPrice': float(position.get('markPrice', '0')),
                    'unrealisedPnl': float(position.get('unrealisedPnl', '0')),
                    'leverage': position.get('leverage', '0'),
                    'positionValue': float(position.get('positionValue', '0')),
                    'has_position': position_size > 0,
                    'trading_mode': 'perp'
                }
                
                if position_size > 0:
                    print(f"Open PERP position found: {position_info}")
                    print(f"Unrealized PnL: ${position_info['unrealisedPnl']:.2f}")
                else:
                    print(f"No open PERP position for {symbol}")
                
                return position_info
            
            # If no position data found, return empty position info
            return {
                'symbol': symbol,
                'side': 'None',
                'size': 0.0,
                'avgPrice': 0.0,
                'markPrice': 0.0,
                'unrealisedPnl': 0.0,
                'leverage': '0',
                'positionValue': 0.0,
                'has_position': False,
                'trading_mode': 'perp'
            }
            
    except Exception as e:
        print(f"Error getting open positions for {symbol}: {e}")
        return {
            'symbol': symbol,
            'side': 'Error',
            'size': 0.0,
            'avgPrice': 0.0,
            'markPrice': 0.0,
            'unrealisedPnl': 0.0,
            'leverage': '0',
            'positionValue': 0.0,
            'has_position': False,
            'trading_mode': 'perp',
            'error': str(e)
        }

def perp_close_position(symbol: str):
    """
    Closes the entire perpetual futures position for a given symbol.
    This function will close both long and short positions if they exist.
    """
    try:
        # First, get the current position info
        position_info = perp_get_open_positions(symbol)
        
        if position_info is None or not position_info.get('has_position', False):
            return {"retCode": -1, "retMsg": "No open position to close."}
        
        # Determine the opposite side to close the position
        current_side = position_info['side']
        close_side = "Sell" if current_side == "Buy" else "Buy"
        position_size = position_info['size']
        
        print(f"Closing {current_side} position of size {position_size} for {symbol}")
        
        # Place a market order to close the position
        response = session.place_order(
            category="linear",  # linear = perpetual futures
            symbol=symbol,
            side=close_side,
            orderType="Market",
            qty=str(position_size),
            positionIdx=0,  # 0 = one-way mode
            timeInForce="IOC",  # Immediate or Cancel
            reduceOnly=True,  # This ensures we're only closing, not opening new positions
            closeOnTrigger=False  # Set to True if you want it to be a close-on-trigger order
        )
        
        print(f"Close position response: {response}")
        
        if response.get('retCode') == 0:
            print(f"Successfully closed {current_side} position for {symbol}")
        
        return response
        
    except Exception as e:
        print(f"Error closing position for {symbol}: {e}")
        return {"retCode": -1, "retMsg": str(e)}

def monitor_position_pnl(symbol: str, trading_mode: str):
    """
    Monitor and log the current position and unrealized PnL for a given symbol and trading mode.
    This function should be called every trading cycle to track position performance.
    
    Args:
        symbol: Trading symbol (e.g., 'XRPUSDT')
        trading_mode: 'spot' or 'perp'
    
    Returns:
        dict: Position information with PnL details
    """
    print(f"\n---MONITORING POSITION PnL ({trading_mode.upper()})---")
    
    try:
        if trading_mode == 'spot':
            position_info = spot_get_open_positions(symbol)
        elif trading_mode == 'perp':
            position_info = perp_get_open_positions(symbol)
        else:
            print(f"Invalid trading mode: {trading_mode}")
            return None
        
        if position_info and position_info.get('has_position', False):
            # Log position details
            print(f"📊 ACTIVE POSITION - {symbol} ({trading_mode.upper()})")
            print(f"   Side: {position_info['side']}")
            print(f"   Size: {position_info['size']}")
            print(f"   Current Price: ${position_info['markPrice']:.6f}")
            print(f"   Position Value: ${position_info['positionValue']:.2f}")
            
            if trading_mode == 'perp':
                pnl = position_info['unrealisedPnl']
                print(f"   💰 Unrealized PnL: ${pnl:.2f}")
                if pnl > 0:
                    print(f"   🟢 Position is profitable (+${pnl:.2f})")
                elif pnl < 0:
                    print(f"   🔴 Position is at loss (${pnl:.2f})")
                else:
                    print(f"   🔵 Position is at breakeven")
                
                # Calculate PnL percentage if we have entry price
                if position_info['avgPrice'] > 0:
                    pnl_percentage = (pnl / (position_info['avgPrice'] * position_info['size'])) * 100
                    print(f"   📈 PnL Percentage: {pnl_percentage:.2f}%")
            else:
                print(f"   ℹ️  Spot PnL calculation requires entry price tracking")
        else:
            print(f"📭 No active position for {symbol} ({trading_mode.upper()})")
        
        print("---END POSITION MONITORING---\n")
        return position_info
        
    except Exception as e:
        print(f"Error monitoring position PnL: {e}")
        return None
