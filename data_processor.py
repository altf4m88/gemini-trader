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

    # Calculate StochRSI with custom settings
    # lengthRSI=5, lengthStoch=5, smoothK=3, smoothD=3
    df.ta.stochrsi(length=5, rsi_length=5, k=3, d=3, append=True)

    return df
