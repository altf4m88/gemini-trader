"""
Gemini Trader - Main Entry Point

This module serves as the main entry point for the Gemini Trader automated trading bot.
It handles command-line argument parsing, scheduling of trading cycles, and orchestrates
the overall trading workflow for both spot and perpetual futures trading modes.

Usage:
    python main.py spot --symbol XRPUSDT --interval 5
    python main.py perp --symbol BTCUSDT --interval 15
"""

import schedule
import time
import logging
import argparse
import sys
from dotenv import load_dotenv
from graph import app, GraphState
from database import init_db, SessionLocal, BalanceHistory
from bybit_tools import spot_get_account_balance, perp_get_account_balance, monitor_position_pnl

# Load environment variables
load_dotenv()

# Initialize the database
init_db()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_arguments():
    """Parse command line arguments to determine trading mode."""
    parser = argparse.ArgumentParser(description='Gemini Trader - Automated Trading Bot')
    parser.add_argument('mode', choices=['spot', 'perp'], 
                       help='Trading mode: spot for spot trading, perp for perpetual futures trading')
    parser.add_argument('--symbol', default='XRPUSDT', 
                       help='Trading symbol (default: XRPUSDT)')
    parser.add_argument('--interval', type=int, default=5, 
                       help='Trading interval in minutes (default: 5)')
    
    args = parser.parse_args()
    return args

def log_balance_history(mode: str):
    logging.info(f"---LOGGING BALANCE HISTORY ({mode.upper()})---")
    db = SessionLocal()
    try:
        # Use appropriate balance function based on trading mode
        if mode == 'spot':
            response = spot_get_account_balance("UNIFIED")
        elif mode == 'perp':
            response = perp_get_account_balance("UNIFIED")
        else:
            logging.error(f"Invalid trading mode for balance logging: {mode}")
            return
            
        if response and response.get('retCode') == 0:
            balances = response['result']['list']
            for balance in balances:
                for coin_balance in balance['coin']:
                    db_balance = BalanceHistory(
                        account_type=f"{balance['accountType']}_{mode}",  # Add mode to account type
                        balance=float(coin_balance['equity']),
                        coin=coin_balance['coin']
                    )
                    db.add(db_balance)
            db.commit()
    finally:
        db.close()

def run_spot_trading_cycle(symbol: str, interval: int):
    """Run a trading cycle for spot trading."""
    logging.info("---STARTING SPOT TRADING CYCLE---")
    print(f"Selected Symbol: {symbol}")
    print(f"Selected Interval: {interval} minutes")
    print("Mode: SPOT TRADING")
    
    # Monitor current position PnL before making decisions
    monitor_position_pnl(symbol, "spot")
    
    initial_state: GraphState = {
        "symbol": symbol,
        "interval": interval,
        "market_analysis": "",
        "llm_decision": {},
        "trade_executed": False,
        "error_message": "",
        "trading_mode": "spot"  # Add trading mode to state
    }
    
    # Invoke the graph
    final_state = app.invoke(initial_state)
    
    logging.info(f"---COMPLETED SPOT TRADING CYCLE---")
    logging.info(f"Final State: {final_state.get('llm_decision')}")

    if final_state.get("error_message"):
        logging.error(f"Error in spot trading cycle: {final_state['error_message']}")

def run_perp_trading_cycle(symbol: str, interval: int):
    """Run a trading cycle for perpetual futures trading."""
    logging.info("---STARTING PERPETUAL FUTURES TRADING CYCLE---")
    print(f"Selected Symbol: {symbol}")
    print(f"Selected Interval: {interval} minutes")
    print("Mode: PERPETUAL FUTURES TRADING")
    
    # Monitor current position PnL before making decisions
    monitor_position_pnl(symbol, "perp")
    
    initial_state: GraphState = {
        "symbol": symbol,
        "interval": interval,
        "market_analysis": "",
        "llm_decision": {},
        "trade_executed": False,
        "error_message": "",
        "trading_mode": "perp"  # Add trading mode to state
    }
    
    # Invoke the graph
    final_state = app.invoke(initial_state)
    
    logging.info(f"---COMPLETED PERPETUAL FUTURES TRADING CYCLE---")
    logging.info(f"Final State: {final_state.get('llm_decision')}")

    if final_state.get("error_message"):
        logging.error(f"Error in perpetual futures trading cycle: {final_state['error_message']}")

def main():
    """Main function to run the trading bot based on command line arguments."""
    args = parse_arguments()
    
    logging.info(f"Starting Gemini Trader in {args.mode.upper()} mode")
    logging.info(f"Symbol: {args.symbol}, Interval: {args.interval} minutes")
    
    # Choose the appropriate trading function based on mode
    if args.mode == 'spot':
        trading_function = lambda: run_spot_trading_cycle(args.symbol, args.interval)
    elif args.mode == 'perp':
        trading_function = lambda: run_perp_trading_cycle(args.symbol, args.interval)
    else:
        logging.error(f"Invalid trading mode: {args.mode}")
        sys.exit(1)
    
    balance_function = lambda: log_balance_history(args.mode)
    
    # Schedule the trading cycle and balance logging
    schedule.every(1).minutes.do(trading_function)
    schedule.every(1).minutes.do(balance_function)

    # Main loop to run the scheduler
    # Run once immediately
    trading_function()
    balance_function()
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# Main loop to run the scheduler
if __name__ == "__main__":
    main()
