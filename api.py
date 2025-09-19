from fastapi import FastAPI, Query, HTTPException
from typing import Optional
from sqlalchemy import func
from agent_tools import analyze_market_state
from bybit_tools import get_bybit_trade_history, store_trade_history_to_db
from database import init_db, SessionLocal, BybitTradeHistory
import uvicorn
from datetime import datetime, timedelta

app = FastAPI()
#init db here
init_db()

@app.get("/analyze/{symbol}")
def analyze_symbol(symbol: str, interval: int = 15):
    """
    Manually trigger the analyze_market_state tool for a given symbol.
    """
    return analyze_market_state.invoke({"symbol": symbol, "interval": interval})

@app.get("/trade-history/fetch")
def fetch_and_store_trade_history(
    category: str = Query("linear", description="Product type (linear, spot, option, inverse)"),
    symbol: Optional[str] = Query(None, description="Symbol name (e.g., BTCUSDT)"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to fetch (1-100)"),
    days_back: Optional[int] = Query(7, ge=1, le=730, description="Number of days back to fetch (1-730)"),
):
    """
    Fetch trade history from Bybit API and store it in the database.
    
    Parameters:
    - category: Product type (linear, spot, option, inverse)
    - symbol: Optional symbol filter
    - limit: Number of records per request (1-100)
    - days_back: Number of days back to fetch data (1-730)
    """
    try:
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days_back)
        
        # Convert to milliseconds
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int(end_time.timestamp() * 1000)
        
        # Fetch trade history from Bybit
        response = get_bybit_trade_history(
            category=category,
            symbol=symbol,
            limit=limit,
            start_time=start_time_ms,
            end_time=end_time_ms
        )
        
        if response.get('retCode') != 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Bybit API error: {response.get('retMsg', 'Unknown error')}"
            )
        
        executions_list = response.get('result', {}).get('list', [])
        
        if not executions_list:
            return {
                "status": "success",
                "message": "No trade history found for the specified criteria",
                "fetched_count": 0,
                "storage_summary": {
                    "stored_count": 0,
                    "updated_count": 0,
                    "error_count": 0,
                    "total_processed": 0
                }
            }
        
        # Store to database
        storage_summary = store_trade_history_to_db(executions_list, category)
        
        return {
            "status": "success",
            "message": f"Successfully fetched and processed {len(executions_list)} trade records",
            "fetched_count": len(executions_list),
            "storage_summary": storage_summary,
            "time_range": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "days_back": days_back
            },
            "filters": {
                "category": category,
                "symbol": symbol,
                "limit": limit
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/trade-history/list")
def get_stored_trade_history(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip")
):
    """
    Retrieve stored trade history from the database.
    
    Parameters:
    - symbol: Optional symbol filter
    - category: Optional category filter  
    - limit: Number of records to return (1-1000)
    - offset: Number of records to skip for pagination
    """
    try:
        db = SessionLocal()
        
        # Build query
        query = db.query(BybitTradeHistory)
        
        if symbol:
            query = query.filter(BybitTradeHistory.symbol == symbol)
        if category:
            query = query.filter(BybitTradeHistory.category == category)
        
        # Order by execution time descending (newest first)
        query = query.order_by(BybitTradeHistory.exec_time.desc())
        
        # Get total count for pagination info
        total_count = query.count()
        
        # Apply pagination
        trades = query.offset(offset).limit(limit).all()
        
        # Convert to dict format
        trades_data = []
        for trade in trades:
            trade_dict = {
                "id": trade.id,
                "exec_id": trade.exec_id,
                "symbol": trade.symbol,
                "order_id": trade.order_id,
                "side": trade.side,
                "order_type": trade.order_type,
                "exec_price": trade.exec_price,
                "exec_qty": trade.exec_qty,
                "exec_value": trade.exec_value,
                "exec_fee": trade.exec_fee,
                "fee_currency": trade.fee_currency,
                "is_maker": trade.is_maker,
                "exec_time": trade.exec_time,
                "created_at": trade.created_at.isoformat() if trade.created_at else None,
                "category": trade.category,
                "pnl": trade.pnl
            }
            trades_data.append(trade_dict)
        
        db.close()
        
        return {
            "status": "success",
            "data": trades_data,
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "returned_count": len(trades_data)
            },
            "filters": {
                "symbol": symbol,
                "category": category
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.get("/trade-history/pnl-summary")
def get_pnl_summary(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    category: Optional[str] = Query(None, description="Filter by category"),
    days_back: Optional[int] = Query(30, ge=1, le=730, description="Number of days back to analyze")
):
    """
    Get PnL summary statistics for trade history.
    
    Parameters:
    - symbol: Optional symbol filter
    - category: Optional category filter
    - days_back: Number of days back to analyze (1-730)
    """
    try:
        db = SessionLocal()
        
        # Calculate time threshold
        time_threshold = datetime.now() - timedelta(days=days_back)
        time_threshold_ms = int(time_threshold.timestamp() * 1000)
        
        # Build query
        query = db.query(BybitTradeHistory).filter(
            BybitTradeHistory.exec_time >= time_threshold_ms
        )
        
        if symbol:
            query = query.filter(BybitTradeHistory.symbol == symbol)
        if category:
            query = query.filter(BybitTradeHistory.category == category)
        
        # Get all trades for detailed analysis
        trades = query.all()
        
        if not trades:
            return {
                "status": "success",
                "message": "No trades found for the specified criteria",
                "summary": {
                    "total_trades": 0,
                    "total_pnl": 0.0,
                    "profitable_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_fees": 0.0,
                    "net_pnl": 0.0
                }
            }
        
        # Calculate summary statistics
        total_trades = len(trades)
        total_pnl = sum(trade.pnl for trade in trades if trade.pnl is not None)
        total_fees = sum(trade.exec_fee for trade in trades if trade.exec_fee is not None)
        
        profitable_trades = len([t for t in trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in trades if t.pnl and t.pnl < 0])
        breakeven_trades = total_trades - profitable_trades - losing_trades
        
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Group by symbol for per-symbol analysis
        symbol_pnl = {}
        for trade in trades:
            if trade.symbol not in symbol_pnl:
                symbol_pnl[trade.symbol] = {
                    "total_pnl": 0.0,
                    "trade_count": 0,
                    "fees": 0.0
                }
            symbol_pnl[trade.symbol]["total_pnl"] += trade.pnl if trade.pnl else 0
            symbol_pnl[trade.symbol]["trade_count"] += 1
            symbol_pnl[trade.symbol]["fees"] += trade.exec_fee if trade.exec_fee else 0
        
        db.close()
        
        return {
            "status": "success",
            "summary": {
                "total_trades": total_trades,
                "total_pnl": round(total_pnl, 4),
                "profitable_trades": profitable_trades,
                "losing_trades": losing_trades,
                "breakeven_trades": breakeven_trades,
                "win_rate": round(win_rate, 2),
                "total_fees": round(total_fees, 4),
                "net_pnl": round(total_pnl, 4),  # PnL already includes fees in calculation
                "average_pnl_per_trade": round(total_pnl / total_trades, 4) if total_trades > 0 else 0
            },
            "symbol_breakdown": symbol_pnl,
            "time_range": {
                "days_back": days_back,
                "from_date": time_threshold.isoformat()
            },
            "filters": {
                "symbol": symbol,
                "category": category
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
