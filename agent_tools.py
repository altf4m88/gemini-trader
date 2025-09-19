from langchain.tools import tool
from bybit_tools import spot_get_market_data, spot_get_open_positions
from data_processor import add_technical_indicators

@tool
def analyze_market_state(symbol: str, interval: int = 15) -> str:
    """
    Analyzes the market state for a given symbol and interval.
    Fetches market data, adds technical indicators, and checks for open positions.
    Returns a summary string for the LLM.
    """
    # 1. Get market data
    # Using a limit of 500 as a reasonable default for indicator calculation
    market_data = spot_get_market_data(symbol, interval, limit=1000)

    if market_data.empty:
        return "Could not retrieve market data."

    # 2. Add technical indicators
    enriched_data = add_technical_indicators(market_data)

    # print the last RSI_14, MACD_12_26_9, BBM_5_2.0_2.0, STOCHRSIk_5_5_3_3, STOCHRSId_5_5_3_3
    print(enriched_data[["RSI_14", "MACD_12_26_9", "BBM_5_2.0_2.0", "STOCHRSIk_5_5_3_3", "STOCHRSId_5_5_3_3"]].tail(5))

    # 3. Format the last few rows for the LLM
    llm_readable_data = enriched_data.tail(5).to_json(orient="records")

    # 4. Check for open positions
    open_position_qty = spot_get_open_positions(symbol)
    position_info = f"Current position quantity for {symbol}: {open_position_qty}"
    print(position_info)

    # 5. Construct the final output for the LLM
    analysis = f"Market Analysis for {symbol}:\n"
    analysis += f"Recent Data (last 5 periods):\n{llm_readable_data}\n"
    analysis += position_info

    return analysis
