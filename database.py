"""
Gemini Trader - Database Models and Configuration

This module defines the SQLAlchemy ORM models and database configuration for the trading bot.
It manages trade history, balance tracking, token usage, and Bybit trade imports.

Models:
- TradeHistory: All trading decisions including HOLD actions
- BybitTradeHistory: Imported execution history from Bybit API
- BalanceHistory: Account balance snapshots over time
- AgentTokenUsage: AI model token consumption tracking

Database: PostgreSQL configured via DATABASE_URL environment variable
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, Boolean, Text, BigInteger
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import datetime

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- ORM Models ---

class TradeHistory(Base):
    __tablename__ = "trade_history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    symbol = Column(String)
    action = Column(String)
    quantity = Column(Float)
    price = Column(Float)
    reasoning = Column(String)
    order_id = Column(String)
    llm_decision = Column(JSON)

class BybitTradeHistory(Base):
    __tablename__ = "bybit_trade_history"
    id = Column(Integer, primary_key=True, index=True)
    
    # Bybit execution details
    exec_id = Column(String, unique=True, index=True)  # Unique execution ID from Bybit
    symbol = Column(String, index=True)
    order_id = Column(String, index=True)
    order_link_id = Column(String)
    side = Column(String)  # Buy/Sell
    order_type = Column(String)  # Market/Limit
    
    # Price and quantity information
    order_price = Column(Float)
    order_qty = Column(Float)
    leaves_qty = Column(Float)
    exec_price = Column(Float)
    exec_qty = Column(Float)
    exec_value = Column(Float)
    
    # Fees and financial details
    exec_fee = Column(Float)
    exec_fee_v2 = Column(Float)
    fee_currency = Column(String)
    fee_rate = Column(Float)
    
    # Trading details
    is_maker = Column(Boolean)
    exec_type = Column(String)
    stop_order_type = Column(String)
    create_type = Column(String)
    
    # Options-specific fields
    trade_iv = Column(String)
    mark_iv = Column(String)
    mark_price = Column(Float)
    index_price = Column(Float)
    underlying_price = Column(Float)
    
    # Additional fields
    block_trade_id = Column(String)
    closed_size = Column(Float)
    seq = Column(BigInteger)
    extra_fees = Column(Text)
    
    # Timing
    exec_time = Column(BigInteger, index=True)  # Execution timestamp from Bybit
    created_at = Column(DateTime, default=datetime.datetime.utcnow)  # When we inserted this record
    
    # Category for the trade (linear, spot, option, etc.)
    category = Column(String, index=True)
    
    # Calculated PnL for the trade
    pnl = Column(Float)  # Profit/Loss calculated based on side and execution details

class BalanceHistory(Base):
    __tablename__ = "balance_history"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    account_type = Column(String)
    balance = Column(Float)
    coin = Column(String)

class AgentTokenUsage(Base):
    __tablename__ = "agent_token_usage"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    model_name = Column(String)
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)

def init_db():
    Base.metadata.create_all(bind=engine)
