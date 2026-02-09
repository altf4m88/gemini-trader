# Gemini Trader

An automated cryptocurrency trading bot powered by Google's Gemini AI model, supporting both spot and perpetual futures trading on Bybit exchange.

## 🚀 Features

- **AI-Powered Trading Decisions**: Utilizes Google's Gemini 2.0 Flash model for intelligent market analysis and trading decisions
- **Dual Trading Modes**: 
  - **Spot Trading**: Long-only positions with actual asset ownership
  - **Perpetual Futures**: Both long and short positions with leverage support
- **Technical Analysis**: 
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - Stochastic RSI
- **Risk Management**:
  - Fixed position sizing (2% of account balance for spot)
  - Stop-loss and take-profit targets
  - Position monitoring and PnL tracking
- **LangGraph Workflow**: Structured decision-making process using LangGraph state machine
- **Database Tracking**: 
  - SQLAlchemy-based trade history
  - Balance history logging
  - Token usage tracking
  - Bybit trade history import
- **REST API**: FastAPI-based API for manual market analysis and trade history queries
- **Automated Scheduling**: Configurable trading intervals with scheduled execution

## 📋 Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Bybit account (Demo/Testnet recommended for testing)
- Google API key for Gemini AI model

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/altf4m88/gemini-trader.git
cd gemini-trader
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with the following variables:
```env
# Bybit API Credentials (Demo/Testnet)
BYBIT_API_KEY_TESTNET=your_api_key_here
BYBIT_API_SECRET_TESTNET=your_api_secret_here

# Google Gemini API Key
GOOGLE_API_KEY=your_google_api_key_here

# Database Connection
DATABASE_URL=postgresql://username:password@localhost:5432/gemini_trader
```

## 🎯 Usage

### Running the Trading Bot

The bot supports two trading modes: `spot` and `perp` (perpetual futures).

#### Spot Trading Mode
```bash
python main.py spot --symbol XRPUSDT --interval 5
```

#### Perpetual Futures Trading Mode
```bash
python main.py perp --symbol XRPUSDT --interval 5
```

#### Command Line Arguments
- `mode`: Trading mode - `spot` or `perp` (required)
- `--symbol`: Trading symbol (default: XRPUSDT)
- `--interval`: Trading interval in minutes (default: 5)

### Running the API Server

Start the FastAPI server for manual analysis and querying:
```bash
python api.py
```

The API will be available at `http://localhost:8000`. Access the interactive documentation at `http://localhost:8000/docs`.

### API Endpoints

#### Market Analysis
```
GET /analyze/{symbol}?interval=15
```
Manually trigger market analysis for a specific symbol.

#### Trade History Management
```
GET /trade-history/fetch
```
Fetch and store trade history from Bybit API.

```
GET /trade-history/list
```
Retrieve stored trade history from the database.

```
GET /trade-history/pnl-summary
```
Get PnL summary statistics for trade history.

## 📁 Project Structure

```
gemini-trader/
├── main.py                   # Main entry point for the trading bot
├── api.py                    # FastAPI server for manual operations
├── graph.py                  # LangGraph workflow definition
├── agent_tools.py            # Market analysis tool
├── bybit_tools.py            # Bybit API integration
├── database.py               # Database models and configuration
├── data_processor.py         # Technical indicator calculations
├── prompts.py                # AI prompts for different trading modes
├── prompts_debug.py          # Debug prompts
├── prompts_perpetual.py      # Legacy perpetual prompts
├── migrate_add_pnl.py        # Database migration script
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (create this)
├── .gitignore               # Git ignore patterns
└── Gemini Trader Doc.pdf    # Original documentation
```

## 🤖 Trading Strategy

### Spot Trading Strategy

**Entry Conditions (BUY):**
- RSI below 35 (oversold)
- Price touching or below lower Bollinger Band
- Stochastic RSI %K below 20 and crossing above %D

**Exit Conditions (CLOSE):**
- Price touches upper Bollinger Band AND RSI above 65 (overbought)
- Stop loss: 0.75% below entry price
- Stochastic RSI %K above 80 and crossing below %D

### Perpetual Futures Strategy

**Long Entry Conditions (BUY):**
- RSI below 35 (oversold)
- Price touching or below lower Bollinger Band
- Stochastic RSI %K below 20 and crossing above %D

**Short Entry Conditions (SELL):**
- RSI above 65 (overbought)
- Price touching or above upper Bollinger Band
- Stochastic RSI %K above 80 and crossing below %D

**Position Management:**
- Fixed margin: $50 USD per position
- Fixed leverage: 10x ($500 USD position size)
- Stop loss: -$0.50 maximum loss
- Take profit: $1.00 target profit
- Risk-to-reward ratio: 2:1

## 🗄️ Database Schema

The bot uses PostgreSQL with the following main tables:

- **trade_history**: Stores all trading decisions (including HOLD)
- **bybit_trade_history**: Imported trade execution history from Bybit
- **balance_history**: Account balance snapshots over time
- **agent_token_usage**: Tracks AI model token consumption

## ⚠️ Important Notes

- **Paper Trading**: The bot is configured to use Bybit's demo/testnet environment by default. Update `bybit_tools.py` to switch to live trading.
- **Risk Warning**: Cryptocurrency trading involves substantial risk. This bot is for educational purposes. Never risk more than you can afford to lose.
- **API Limits**: Be aware of Bybit API rate limits when configuring trading intervals.
- **Position Safety**: The bot includes safety checks to prevent opening multiple positions simultaneously.

## 🔧 Configuration

### Modifying Trading Parameters

Edit `prompts.py` to adjust:
- Risk percentage per trade
- Technical indicator thresholds
- Entry/exit conditions

Edit `main.py` to adjust:
- Trading cycle frequency
- Balance logging interval

### Database Migration

If you need to add the PnL column to an existing database:
```bash
python migrate_add_pnl.py
```

## 📊 Monitoring

The bot logs all activities including:
- Trading decisions and reasoning
- Market analysis results
- Trade execution status
- Balance updates
- Token usage statistics

Check the console output and database tables for detailed monitoring.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is open source and available for anyone to use and modify.

## ⚠️ Disclaimer

This trading bot is provided as-is for educational purposes only. The authors are not responsible for any financial losses incurred through the use of this software. Always test thoroughly with paper trading before risking real capital.

## 🙏 Acknowledgments

- Built with [LangChain](https://github.com/langchain-ai/langchain) and [LangGraph](https://github.com/langchain-ai/langgraph)
- Powered by [Google Gemini AI](https://deepmind.google/technologies/gemini/)
- Trading on [Bybit](https://www.bybit.com/)
- Technical indicators via [pandas-ta](https://github.com/twopirllc/pandas-ta)
