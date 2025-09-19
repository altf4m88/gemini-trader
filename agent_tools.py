from langchain.tools import tool
from bybit_tools import spot_get_market_data, spot_get_open_positions, perp_get_market_data, perp_get_open_positions
from data_processor import add_technical_indicators

@tool
def analyze_market_state(symbol: str, interval: int = 15, trading_mode: str = "spot") -> str:
    """
    Analyzes the market state for a given symbol and interval.
    Fetches market data, adds technical indicators, and checks for open positions.
    Supports both spot and perpetual futures trading modes.
    Returns a summary string for the LLM.
    """
    # 1. Get market data based on trading mode
    if trading_mode == "spot":
        market_data = spot_get_market_data(symbol, interval, limit=1000)
    elif trading_mode == "perp":
        market_data = perp_get_market_data(symbol, interval, limit=1000)
    else:
        return f"Invalid trading mode: {trading_mode}. Use 'spot' or 'perp'."

    if market_data.empty:
        return f"Could not retrieve {trading_mode} market data."

    # 2. Add technical indicators
    enriched_data = add_technical_indicators(market_data)

    # print the last RSI_14, MACD_12_26_9, BBM_5_2.0_2.0, STOCHRSIk_5_5_3_3, STOCHRSId_5_5_3_3
    print(enriched_data[["RSI_14", "MACD_12_26_9", "BBM_5_2.0_2.0", "STOCHRSIk_5_5_3_3", "STOCHRSId_5_5_3_3"]].tail(5))

    # 3. Format the last few rows for the LLM
    llm_readable_data = enriched_data.tail(5).to_json(orient="records")

    # 4. Check for open positions based on trading mode
    if trading_mode == "spot":
        open_position_info = spot_get_open_positions(symbol)
        if open_position_info and open_position_info.get('has_position', False):
            position_info = f"Current spot position for {symbol}: {open_position_info['size']} units (${open_position_info['positionValue']:.2f} value)"
        else:
            position_info = f"No open spot positions for {symbol}"
    elif trading_mode == "perp":
        open_position_info = perp_get_open_positions(symbol)
        if open_position_info and open_position_info.get('has_position', False):
            pnl = open_position_info['unrealisedPnl']
            position_info = f"Current perpetual position for {symbol}: {open_position_info['side']} {open_position_info['size']} units, PnL: ${pnl:.2f}"
        else:
            position_info = f"No open perpetual positions for {symbol}"
    
    print(position_info)

    # 5. Construct the final output for the LLM
    analysis = f"Market Analysis for {symbol} ({trading_mode.upper()} mode):\n"
    analysis += f"Recent Data (last 5 periods):\n{llm_readable_data}\n"
    analysis += position_info

    return analysis
