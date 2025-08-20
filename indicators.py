
import numpy as np
import pandas as pd

def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False).mean()

def atr(df: pd.DataFrame, length: int) -> pd.Series:
    # df must have columns: high, low, close
    high, low, close = df['high'], df['low'], df['close']
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(length).mean()

def support_resistance_breakout(df: pd.DataFrame, lookback: int):
    # Use highest/lowest of previous lookback bars (exclude current)
    res = df['high'].shift(1).rolling(lookback).max()
    sup = df['low'].shift(1).rolling(lookback).min()
    return sup, res
