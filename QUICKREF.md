# Quick Reference Guide

A quick reference for common commands and operations in Gemini Trader.

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/altf4m88/gemini-trader.git
cd gemini-trader
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # Then edit .env with your credentials

# Run spot trading
python main.py spot --symbol XRPUSDT --interval 5

# Run perpetual futures trading
python main.py perp --symbol BTCUSDT --interval 15
```

## 📝 Common Commands

### Running the Bot

```bash
# Spot trading (default symbol: XRPUSDT, interval: 5 min)
python main.py spot

# Perpetual futures trading with custom settings
python main.py perp --symbol ETHUSDT --interval 15

# Different symbols
python main.py spot --symbol BTCUSDT --interval 10
python main.py perp --symbol SOLUSDT --interval 5
```

### API Server

```bash
# Start API server
python api.py

# Access interactive docs
# Open browser: http://localhost:8000/docs

# Test endpoint
curl http://localhost:8000/analyze/XRPUSDT?interval=15
```

### Database Operations

```bash
# Connect to database
psql -U gemini_user -d gemini_trader

# View recent trades
psql -U gemini_user -d gemini_trader -c "
  SELECT timestamp, symbol, action, quantity, price, reasoning 
  FROM trade_history 
  ORDER BY timestamp DESC 
  LIMIT 10;
"

# View balance history
psql -U gemini_user -d gemini_trader -c "
  SELECT timestamp, account_type, coin, balance 
  FROM balance_history 
  ORDER BY timestamp DESC 
  LIMIT 10;
"

# Export trades to CSV
psql -U gemini_user -d gemini_trader -c "
  \COPY trade_history TO 'trades.csv' CSV HEADER;
"

# Check token usage
psql -U gemini_user -d gemini_trader -c "
  SELECT 
    DATE(timestamp) as date,
    SUM(total_tokens) as total_tokens,
    COUNT(*) as decisions
  FROM agent_token_usage 
  GROUP BY DATE(timestamp) 
  ORDER BY date DESC;
"
```

### Python Interactive Testing

```bash
# Start Python shell with environment
python

# Test components
>>> from database import init_db, SessionLocal
>>> init_db()
>>> print("Database initialized")

>>> from bybit_tools import spot_get_market_data
>>> df = spot_get_market_data("XRPUSDT", 15, limit=5)
>>> print(df)

>>> from agent_tools import analyze_market_state
>>> analysis = analyze_market_state.invoke({"symbol": "XRPUSDT", "interval": 15, "trading_mode": "spot"})
>>> print(analysis)
```

## 🔧 Configuration Quick Edits

### Change Trading Strategy

Edit `prompts.py`:
```python
# Change RSI threshold for oversold (default: 35)
"The RSI is below 30 (indicating an oversold state)."

# Change risk percentage (default: 2%)
"calculate the quantity to risk no more than 1.5% of the total account balance"

# Change leverage for perpetuals (default: 10x)
"Every position MUST use exactly 20x leverage"
```

### Change Trading Interval

Edit `main.py`:
```python
# Change from 1 minute to 5 minutes
schedule.every(5).minutes.do(trading_function)
schedule.every(5).minutes.do(balance_function)
```

### Switch from Demo to Live Trading

Edit `bybit_tools.py`:
```python
# Change from demo to live (CAREFUL!)
session = HTTP(
    testnet=False,
    demo=False,  # Changed from True
    api_key=os.environ.get("BYBIT_API_KEY"),  # Use live key
    api_secret=os.environ.get("BYBIT_API_SECRET"),
    timeout=30,
)
```

## 📊 Monitoring Queries

### Check Current Positions

```python
# In Python shell
from bybit_tools import spot_get_open_positions, perp_get_open_positions

# Check spot position
spot_pos = spot_get_open_positions("XRPUSDT")
print(spot_pos)

# Check perpetual position
perp_pos = perp_get_open_positions("XRPUSDT")
print(perp_pos)
```

### Check Account Balance

```python
from bybit_tools import spot_get_account_balance, perp_get_account_balance

# Spot balance
balance = spot_get_account_balance("UNIFIED")
print(balance)

# Perp balance
balance = perp_get_account_balance("UNIFIED")
print(balance)
```

### Monitor PnL

```python
from bybit_tools import monitor_position_pnl

# Check PnL for a symbol
monitor_position_pnl("XRPUSDT", "spot")
monitor_position_pnl("BTCUSDT", "perp")
```

## 🔍 Debugging

### Enable Debug Logging

Edit `main.py`:
```python
# Change INFO to DEBUG
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
```

### Check Last AI Decision

```bash
psql -U gemini_user -d gemini_trader -c "
  SELECT 
    timestamp,
    symbol,
    action,
    reasoning,
    llm_decision
  FROM trade_history 
  ORDER BY timestamp DESC 
  LIMIT 1;
"
```

### View Recent Errors

```bash
# If logging to file
tail -f gemini_trader.log | grep ERROR

# In database
psql -U gemini_user -d gemini_trader -c "
  SELECT timestamp, symbol, action, reasoning 
  FROM trade_history 
  WHERE reasoning LIKE '%error%' OR reasoning LIKE '%failed%'
  ORDER BY timestamp DESC 
  LIMIT 10;
"
```

## 🛑 Emergency Stop

```bash
# Find the bot process
ps aux | grep "python main.py"

# Kill the process
kill <PID>

# Or use Ctrl+C in the terminal where bot is running
```

## 📦 Maintenance

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Backup Database

```bash
# Backup entire database
pg_dump -U gemini_user gemini_trader > backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U gemini_user gemini_trader < backup_20260209.sql
```

### Clean Old Records

```sql
-- Delete trade history older than 90 days
DELETE FROM trade_history WHERE timestamp < NOW() - INTERVAL '90 days';

-- Delete balance history older than 30 days
DELETE FROM balance_history WHERE timestamp < NOW() - INTERVAL '30 days';

-- Vacuum database to reclaim space
VACUUM ANALYZE;
```

## 🔗 Useful Links

- **Bybit Testnet**: https://testnet.bybit.com/
- **Bybit API Docs**: https://bybit-exchange.github.io/docs/v5/intro
- **Google AI Studio**: https://makersuite.google.com/app/apikey
- **LangChain Docs**: https://python.langchain.com/docs/get_started/introduction
- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **pandas-ta Docs**: https://github.com/twopirllc/pandas-ta

## ⚡ Performance Tips

1. **Reduce data fetching**: Lower the `limit` parameter in market data calls if you don't need 1000 candles
2. **Increase interval**: Use longer intervals (15, 30 min) to reduce API calls
3. **Database indexing**: Already indexed on timestamp and symbol, but monitor query performance
4. **Clean old data**: Regularly clean up old balance_history to keep database lean

## 🐛 Common Issues

### "Connection refused" to database
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### "Invalid API key"
```bash
# Verify .env has correct credentials
cat .env | grep BYBIT
# Ensure no extra spaces or quotes
```

### "Insufficient balance"
```bash
# Check testnet balance
# Go to testnet.bybit.com and request test USDT
```

### "Rate limit exceeded"
```bash
# Increase trading interval
python main.py spot --interval 15  # Instead of 5
```

## 💡 Tips and Tricks

- **Test strategies**: Use `prompts_debug.py` for testing decision logic
- **Monitor costs**: Check `agent_token_usage` table to track AI API costs
- **Paper trade first**: Always test with demo/testnet before live trading
- **Start small**: Use minimum position sizes when going live
- **Set alerts**: Create database triggers or scripts to alert on significant events
- **Keep logs**: Redirect output to log file: `python main.py spot > trader.log 2>&1`

## 📚 Further Reading

- [README.md](README.md) - Project overview and features
- [SETUP.md](SETUP.md) - Detailed setup guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
