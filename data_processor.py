import pandas as pd
import pandas_ta as ta

def add_technical_indicators(df: pd.DataFrame):
    """
    Adds technical indicators to the DataFrame.
    """
    # Calculate RSI
    df.ta.rsi(append=True)

    # Calculate MACD
    df.ta.macd(append=True)

    # Calculate Bollinger Bands
    df.ta.bbands(append=True)

    return df
