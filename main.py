import schedule
import time
import logging
from dotenv import load_dotenv
from graph import app, GraphState
from database import init_db, SessionLocal, BalanceHistory
from bybit_tools import get_account_balance

# Load environment variables
load_dotenv()

# Initialize the database
init_db()

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def log_balance_history():
    logging.info("---LOGGING BALANCE HISTORY---")
    db = SessionLocal()
    try:
        response = get_account_balance("UNIFIED")
        if response and response.get('retCode') == 0:
            balances = response['result']['list']
            for balance in balances:
                for coin_balance in balance['coin']:
                    db_balance = BalanceHistory(
                        account_type=balance['accountType'],
                        balance=float(coin_balance['equity']),
                        coin=coin_balance['coin']
                    )
                    db.add(db_balance)
            db.commit()
    finally:
        db.close()

def run_trading_cycle():

    logging.info("---STARTING TRADING CYCLE---")
    print("Selected Symbol: XRPUSDT")
    print("Selected Interval: 5 minutes")
    
    initial_state: GraphState = {
        "symbol": "XRPUSDT",
        "interval": 5,
        "market_analysis": "",
        "llm_decision": {},
        "trade_executed": False,
        "error_message": ""
    }
    
    # Invoke the graph
    final_state = app.invoke(initial_state)
    
    logging.info(f"---COMPLETED TRADING CYCLE---")
    logging.info(f"Final State: {final_state.get("llm_decision")}")

    if final_state.get("error_message"):
        logging.error(f"Error in trading cycle: {final_state['error_message']}")

# Schedule the trading cycle and balance logging
schedule.every(1).minutes.do(run_trading_cycle)
schedule.every(1).minutes.do(log_balance_history)

# Main loop to run the scheduler
if __name__ == "__main__":
    # Run once immediately
    run_trading_cycle()
    log_balance_history()
    
    while True:
        schedule.run_pending()
        time.sleep(1)
