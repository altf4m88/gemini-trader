# Setup Guide

This guide will walk you through setting up Gemini Trader step by step.

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] Python 3.8 or higher installed
- [ ] PostgreSQL database installed and running
- [ ] Git installed
- [ ] A Bybit account (demo/testnet recommended for testing)
- [ ] A Google Cloud account with Gemini API access

## Step 1: Install Python and Dependencies

### Check Python Version
```bash
python --version
# or
python3 --version
```

If Python is not installed or the version is below 3.8, download and install it from [python.org](https://www.python.org/downloads/).

### Install PostgreSQL

**On Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**On macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**On Windows:**
Download and install from [postgresql.org](https://www.postgresql.org/download/windows/)

## Step 2: Clone the Repository

```bash
git clone https://github.com/altf4m88/gemini-trader.git
cd gemini-trader
```

## Step 3: Set Up Virtual Environment

### Create Virtual Environment
```bash
python -m venv venv
```

### Activate Virtual Environment

**On Linux/macOS:**
```bash
source venv/bin/activate
```

**On Windows:**
```bash
venv\Scripts\activate
```

### Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 4: Set Up Database

### Create Database
```bash
# Access PostgreSQL
sudo -u postgres psql

# Create database and user
CREATE DATABASE gemini_trader;
CREATE USER gemini_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE gemini_trader TO gemini_user;
\q
```

## Step 5: Get API Credentials

### Bybit API (Testnet)

1. Go to [Bybit Testnet](https://testnet.bybit.com/)
2. Sign up for a testnet account
3. Navigate to API Management
4. Create a new API key
5. Save your API Key and API Secret securely

**Required Permissions:**
- Read: Account, Position, Order
- Write: Position, Order
- Trade: Spot Trading, Derivatives Trading

### Google Gemini API

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Save your API key securely

## Step 6: Configure Environment Variables

### Create .env File
```bash
cp .env.example .env  # If example exists
# or
touch .env
```

### Edit .env File
Open `.env` in your favorite text editor and add:

```env
# Bybit API Credentials (Testnet)
BYBIT_API_KEY_TESTNET=your_bybit_api_key_here
BYBIT_API_SECRET_TESTNET=your_bybit_api_secret_here

# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# Database Configuration
DATABASE_URL=postgresql://gemini_user:your_secure_password@localhost:5432/gemini_trader
```

**Important**: Replace the placeholder values with your actual credentials.

## Step 7: Initialize Database

The database will be automatically initialized when you first run the bot. The tables will be created based on the SQLAlchemy models.

To manually initialize or verify:
```python
python -c "from database import init_db; init_db(); print('Database initialized successfully')"
```

## Step 8: Verify Installation

### Test Database Connection
```python
python -c "from database import engine; print('Database connection successful' if engine else 'Failed')"
```

### Test Bybit Connection
```python
python -c "from bybit_tools import session; print(session.get_server_time())"
```

### Test Google Gemini API
```python
python -c "from langchain_google_genai import GoogleGenerativeAI; import os; llm = GoogleGenerativeAI(model='gemini-2.0-flash', google_api_key=os.environ.get('GOOGLE_API_KEY')); print('Gemini API working' if llm else 'Failed')"
```

## Step 9: First Run

### Start with Spot Mode (Recommended for Testing)
```bash
python main.py spot --symbol XRPUSDT --interval 5
```

This will:
1. Fetch market data for XRPUSDT
2. Calculate technical indicators
3. Analyze the market using Gemini AI
4. Make trading decisions (BUY/HOLD/CLOSE)
5. Execute trades if conditions are met
6. Log all activities to the database

### Monitor the Output
You should see logs like:
```
2026-02-09 12:00:00 - INFO - Starting Gemini Trader in SPOT mode
2026-02-09 12:00:00 - INFO - Symbol: XRPUSDT, Interval: 5 minutes
---STARTING SPOT TRADING CYCLE---
Selected Symbol: XRPUSDT
Selected Interval: 5 minutes
Mode: SPOT TRADING
---ANALYZING MARKET---
---MAKING TRADE DECISION---
---LOGGING DECISION---
Logged HOLD decision for XRPUSDT in SPOT mode
---COMPLETED SPOT TRADING CYCLE---
```

## Step 10: Test API Server (Optional)

### Start the API Server
```bash
python api.py
```

### Access the API Documentation
Open your browser and navigate to:
```
http://localhost:8000/docs
```

You should see the FastAPI interactive documentation where you can test endpoints.

### Test an Endpoint
Try the market analysis endpoint:
```bash
curl http://localhost:8000/analyze/XRPUSDT?interval=15
```

## Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution**: Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Issue: "Could not connect to database"
**Solution**: 
1. Verify PostgreSQL is running: `sudo systemctl status postgresql`
2. Check DATABASE_URL in `.env` is correct
3. Verify database and user exist

### Issue: "Bybit API error"
**Solution**:
1. Verify API credentials in `.env`
2. Ensure you're using testnet credentials with testnet environment
3. Check API key permissions
4. Verify internet connection

### Issue: "Google API error"
**Solution**:
1. Verify GOOGLE_API_KEY in `.env`
2. Check API key is active in Google AI Studio
3. Verify API quotas and limits

### Issue: "Table does not exist"
**Solution**:
```bash
python migrate_add_pnl.py  # Run migration if needed
# or
python -c "from database import init_db; init_db()"
```

## Next Steps

### Explore Different Modes
Try perpetual futures trading:
```bash
python main.py perp --symbol XRPUSDT --interval 5
```

### Monitor Performance
Query the database to see your trading history:
```bash
psql -U gemini_user -d gemini_trader -c "SELECT * FROM trade_history ORDER BY timestamp DESC LIMIT 10;"
```

### Adjust Parameters
Edit `prompts.py` to modify trading strategy parameters based on your risk tolerance.

### Set Up Production
When ready for live trading:
1. Change `demo=True` to `demo=False` in `bybit_tools.py`
2. Update to use live API credentials (not testnet)
3. Start with small position sizes
4. Monitor closely

## Security Recommendations

1. **Never commit `.env` file** - It's in `.gitignore` for a reason
2. **Use strong passwords** for database
3. **Limit API key permissions** to only what's needed
4. **Start with testnet** before going live
5. **Regular backups** of your database
6. **Monitor API usage** to avoid rate limits
7. **Keep dependencies updated** for security patches

## Getting Help

If you encounter issues:
1. Check the [README.md](README.md) for general information
2. Review the [ARCHITECTURE.md](ARCHITECTURE.md) for system details
3. Look at [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
4. Open an issue on GitHub with detailed information

## Useful Commands

### View Running Processes
```bash
ps aux | grep python
```

### Stop the Bot
Press `Ctrl+C` in the terminal where the bot is running

### Check Database Size
```bash
psql -U gemini_user -d gemini_trader -c "SELECT pg_size_pretty(pg_database_size('gemini_trader'));"
```

### Export Trade History
```bash
psql -U gemini_user -d gemini_trader -c "\COPY trade_history TO 'trades.csv' CSV HEADER;"
```

### Clear Old Logs (if logging to file)
```bash
find . -name "*.log" -mtime +30 -delete
```

## Success Indicators

You'll know the setup is successful when:
- ✅ Bot starts without errors
- ✅ Market data is fetched successfully
- ✅ Technical indicators are calculated
- ✅ AI generates trading decisions
- ✅ Database records are created
- ✅ No API authentication errors
- ✅ Logs show normal operation

Happy Trading! 🚀
