# Gemini Trader Architecture

This document provides an overview of the Gemini Trader system architecture, design decisions, and component interactions.

## 🏗️ System Overview

Gemini Trader is an AI-powered automated cryptocurrency trading bot built on a modular architecture that combines market analysis, AI decision-making, and trade execution in a structured workflow.

```
┌─────────────────────────────────────────────────────────────┐
│                     Main Trading Loop                        │
│                      (main.py)                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Workflow                          │
│                    (graph.py)                                │
├─────────────────────────────────────────────────────────────┤
│  1. Analyze Market  →  2. Make Decision  →  3. Log Decision │
│          ↓                                          ↓        │
│     Market Data                            4. Execute Trade  │
└────────────────────────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
  ┌──────────┐ ┌──────────┐ ┌──────────┐
  │  Bybit   │ │  Gemini  │ │ Database │
  │   API    │ │    AI    │ │   (PG)   │
  └──────────┘ └──────────┘ └──────────┘
```

## 📦 Core Components

### 1. Main Application (main.py)

**Purpose**: Entry point for the trading bot, handles scheduling and mode selection.

**Key Features**:
- Command-line argument parsing for trading mode selection
- Scheduled execution of trading cycles (configurable interval)
- Balance history logging
- Support for both spot and perpetual futures modes

**Flow**:
1. Parse command-line arguments (mode, symbol, interval)
2. Initialize database and logging
3. Schedule trading cycles using `schedule` library
4. Run main event loop with continuous execution

### 2. LangGraph Workflow (graph.py)

**Purpose**: Orchestrates the trading decision-making process using a state machine.

**State Definition** (`GraphState`):
```python
{
    "symbol": str,           # Trading symbol (e.g., XRPUSDT)
    "interval": int,         # Time interval in minutes
    "market_analysis": str,  # Formatted market data with indicators
    "llm_decision": dict,    # AI trading decision (action, quantity, reasoning)
    "trade_executed": bool,  # Execution status
    "error_message": str,    # Error tracking
    "trading_mode": str      # "spot" or "perp"
}
```

**Workflow Nodes**:

1. **analyze_market**: 
   - Fetches market data via agent_tools
   - Retrieves technical indicators
   - Checks for open positions
   
2. **make_trade_decision**:
   - Sends market analysis to Gemini AI
   - Uses mode-specific prompts (spot vs perp)
   - Parses JSON decision response
   - Logs token usage

3. **log_decision**:
   - Records all decisions (including HOLD) to database
   - Stores reasoning and LLM decision details

4. **execute_trade** (conditional):
   - Executes only if action is BUY, SELL, or CLOSE
   - Includes safety checks for existing positions
   - Updates trade record with execution details

**Conditional Edge Logic**:
- If action is BUY, SELL, or CLOSE → execute_trade
- If action is HOLD → END

### 3. Agent Tools (agent_tools.py)

**Purpose**: Market analysis tool wrapped with LangChain @tool decorator.

**analyze_market_state function**:
```python
Inputs: symbol, interval, trading_mode
Process:
  1. Fetch market data (spot or perp)
  2. Calculate technical indicators
  3. Get current position status
  4. Format data for LLM consumption
Output: Formatted analysis string
```

**Technical Indicators**:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands (BBM)
- Stochastic RSI (k and d lines)

### 4. Bybit Integration (bybit_tools.py)

**Purpose**: Interface with Bybit API for market data and trade execution.

**Key Functions**:

**Market Data**:
- `spot_get_market_data()`: Fetch OHLCV data for spot
- `perp_get_market_data()`: Fetch OHLCV data for perpetuals
- Returns pandas DataFrame with price data

**Position Management**:
- `spot_get_open_positions()`: Check current spot holdings
- `perp_get_open_positions()`: Check perpetual positions
- Returns position details including size, value, and PnL

**Trade Execution**:
- `spot_place_market_order()`: Place spot market order
- `spot_close_position()`: Close spot position
- `perp_place_market_order()`: Place perpetual order with leverage
- `perp_close_position()`: Close perpetual position

**PnL Monitoring**:
- `monitor_position_pnl()`: Track unrealized profit/loss
- Logs PnL information before each trading cycle

**Trade History Import**:
- `get_bybit_trade_history()`: Fetch historical trades from Bybit
- `store_trade_history_to_db()`: Import trades to local database

### 5. Data Processing (data_processor.py)

**Purpose**: Calculate technical indicators using pandas-ta.

**add_technical_indicators function**:
```python
Input: pandas DataFrame with OHLCV data
Process:
  - RSI (14 period default)
  - MACD (12, 26, 9)
  - Bollinger Bands (5 period, 2 std)
  - Stochastic RSI (5,5,3,3)
Output: DataFrame with added indicator columns
```

### 6. Database Layer (database.py)

**Purpose**: SQLAlchemy ORM models and database initialization.

**Models**:

1. **TradeHistory**:
   - Stores all trading decisions (including HOLD)
   - Fields: timestamp, symbol, action, quantity, price, reasoning, order_id, llm_decision

2. **BybitTradeHistory**:
   - Imported execution history from Bybit API
   - Detailed execution data including fees, PnL, timestamps
   - Supports multiple categories (spot, linear, inverse, options)

3. **BalanceHistory**:
   - Account balance snapshots over time
   - Fields: timestamp, account_type, balance, coin

4. **AgentTokenUsage**:
   - Tracks Gemini AI token consumption
   - Fields: timestamp, model_name, input_tokens, output_tokens, total_tokens

**Database**: PostgreSQL (configurable via DATABASE_URL environment variable)

### 7. Prompts (prompts.py)

**Purpose**: Define trading strategies and instructions for the AI model.

**spot_system_prompt**:
- Long-only spot trading strategy
- Entry: RSI < 35, price at lower BB, Stoch RSI crossing up
- Exit: RSI > 65 at upper BB, or stop loss, or Stoch RSI crossing down
- Risk: 2% of account per trade

**perp_system_prompt**:
- Long and short perpetual futures strategy
- Fixed parameters: $50 margin, 10x leverage, $500 position size
- Risk-reward: 2:1 ratio (-$0.50 SL, $1.00 TP)
- Entry/exit based on similar technical conditions

**Output Format**: Structured JSON with action, quantity, and reasoning

### 8. API Server (api.py)

**Purpose**: FastAPI REST API for manual operations and queries.

**Endpoints**:

1. **GET /analyze/{symbol}**:
   - Manual market analysis trigger
   - Returns technical indicator data

2. **GET /trade-history/fetch**:
   - Fetch and store Bybit trade history
   - Parameters: category, symbol, limit, days_back

3. **GET /trade-history/list**:
   - Query stored trade history
   - Supports filtering and pagination

4. **GET /trade-history/pnl-summary**:
   - Calculate PnL statistics
   - Grouped by symbol with win rate analysis

## 🔄 Data Flow

### Trading Cycle Flow

```
1. Scheduled Trigger (every N minutes)
   ↓
2. Fetch Market Data (Bybit API)
   ↓
3. Calculate Technical Indicators (pandas-ta)
   ↓
4. Check Current Positions (Bybit API)
   ↓
5. Format Analysis for AI (agent_tools)
   ↓
6. Generate Trading Decision (Gemini AI)
   ↓
7. Log Decision to Database (SQLAlchemy)
   ↓
8. Execute Trade if needed (Bybit API)
   ↓
9. Update Database with Execution Details
```

### Balance Logging Flow

```
1. Scheduled Trigger (every N minutes)
   ↓
2. Fetch Account Balance (Bybit API)
   ↓
3. Store Balance Snapshot (Database)
```

## 🔐 Security Architecture

### API Key Management
- All sensitive credentials stored in `.env` file
- Environment variables loaded via `python-dotenv`
- Never committed to version control

### Demo Mode
- Default configuration uses Bybit demo/testnet
- Configured in `bybit_tools.py`: `demo=True`
- Safe for testing and development

### Position Safety Checks
- Prevents opening multiple positions simultaneously
- Validates existing positions before new trades
- Implemented in `execute_trade` node

## 🎛️ Configuration

### Environment Variables
```env
BYBIT_API_KEY_TESTNET      # Bybit API key
BYBIT_API_SECRET_TESTNET   # Bybit API secret
GOOGLE_API_KEY             # Google Gemini API key
DATABASE_URL               # PostgreSQL connection string
```

### Adjustable Parameters

**Trading Strategy** (prompts.py):
- Risk percentage
- Technical indicator thresholds
- Entry/exit conditions
- Position sizing rules

**Trading Execution** (main.py):
- Trading cycle interval
- Balance logging frequency
- Default symbol and interval

**Market Analysis** (agent_tools.py):
- Number of candlesticks (limit=1000)
- Displayed periods (tail 5)

## 🔍 Monitoring and Observability

### Logging
- Console output with timestamps
- Trading decisions and reasoning
- Market analysis results
- Execution status and errors

### Database Tracking
- Complete trade history with reasoning
- Token usage for cost monitoring
- Balance history for portfolio tracking
- Imported Bybit executions for reconciliation

### API Monitoring
- FastAPI interactive docs at `/docs`
- Manual trigger for analysis
- Query historical data and PnL

## 🚀 Deployment Considerations

### Requirements
- Python 3.8+
- PostgreSQL database
- Stable internet connection
- API access to Bybit and Google Gemini

### Scalability
- Single-threaded execution (one trading cycle at a time)
- Database connection pooling via SQLAlchemy
- Suitable for personal/small-scale trading
- Can be extended for multi-symbol trading

### Failure Handling
- Error messages captured in state
- Database transactions for data integrity
- Continues operation on non-critical errors
- Manual intervention may be needed for API failures

## 🔮 Future Architecture Enhancements

### Potential Improvements
1. **Microservices**: Separate market analysis, decision-making, and execution
2. **Message Queue**: Async processing with Redis/RabbitMQ
3. **Caching**: Redis for market data and positions
4. **Multi-Exchange**: Abstraction layer for multiple exchanges
5. **Backtesting Engine**: Historical strategy validation
6. **Web Dashboard**: Real-time monitoring UI
7. **Distributed Execution**: Multiple symbols/strategies in parallel
8. **Machine Learning**: Model training on historical decisions
9. **Risk Engine**: Centralized risk management service
10. **Alert System**: Notifications via Telegram/Discord/Email

## 📚 Technology Stack

- **Language**: Python 3.8+
- **AI/LLM**: Google Gemini 2.0 Flash via LangChain
- **Workflow**: LangGraph state machine
- **Exchange API**: Bybit Unified Trading API (pybit)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Technical Analysis**: pandas-ta
- **API Framework**: FastAPI
- **Scheduling**: schedule library
- **Environment**: python-dotenv

## 🤝 Design Principles

1. **Modularity**: Clear separation of concerns
2. **Configurability**: Environment-based configuration
3. **Observability**: Comprehensive logging and tracking
4. **Safety**: Multiple checks before trade execution
5. **Extensibility**: Easy to add new strategies and exchanges
6. **Testability**: Demo mode for safe testing
7. **Simplicity**: Straightforward architecture for maintainability
