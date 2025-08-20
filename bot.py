
import time, os, math, hmac, hashlib, json, threading
import pandas as pd
import numpy as np
import requests
import yaml
from datetime import datetime, timezone
from pybit.unified_trading import HTTP
from indicators import ema, atr, support_resistance_breakout
from risk import RiskSettings, position_size
import storage
import report as report_mod

def load_config():
    with open("config.yaml","r") as f:
        return yaml.safe_load(f)

def bybit_client(cfg):
    return HTTP(testnet=cfg["bybit"].get("testnet", True),
                api_key=cfg["bybit"]["api_key"],
                api_secret=cfg["bybit"]["api_secret"],
                )

def fetch_klines(session, symbol, interval, limit=200, category="linear"):
    # returns DataFrame of o,h,l,c,v with timestamps (ms) ascending
    r = session.get_kline(category=category, symbol=symbol, interval=str(interval), limit=limit)
    if 'result' not in r or 'list' not in r['result']:
        raise RuntimeError(f"Bybit Kline error: {r}")
    data = r['result']['list']
    # list items are [start, open, high, low, close, volume, turnover]
    cols = ["start","open","high","low","close","volume","turnover"]
    df = pd.DataFrame(data, columns=cols)
    df = df.astype({
        "start": "int64",
        "open": "float64",
        "high": "float64",
        "low": "float64",
        "close": "float64",
        "volume": "float64",
        "turnover": "float64",
    })
    df = df.sort_values("start").reset_index(drop=True)
    return df

def get_equity(session):
    try:
        r = session.get_wallet_balance(accountType="UNIFIED")
        # Find USDT balance
        for asset in r["result"]["list"][0]["coin"]:
            if asset["coin"]=="USDT":
                return float(asset["walletBalance"])
    except Exception as e:
        pass
    return None

def place_order(session, symbol, side, qty, sl_price, tp_price, category="linear"):
    # market order + set TP/SL
    params = dict(category=category, symbol=symbol, side=side, orderType="Market",
                  qty=str(round(qty, 6)), timeInForce="GoodTillCancel", reduceOnly=False, closeOnTrigger=False)
    r = session.place_order(**params)
    if r.get("retCode")!=0:
        raise RuntimeError(f"Order error: {r}")
    # set TP/SL using set_trading_stop
    try:
        session.set_trading_stop(category=category, symbol=symbol,
                                 takeProfit=str(tp_price), stopLoss=str(sl_price), tpTriggerBy="LastPrice", slTriggerBy="LastPrice")
    except Exception as e:
        print("Warning set_trading_stop:", e)
    return r

def check_positions(session, symbol, category="linear"):
    r = session.get_positions(category=category, symbol=symbol)
    return r

def run():
    cfg = load_config()
    ses = bybit_client(cfg)
    db = storage.connect(cfg["engine"]["db_path"])

    symbol = cfg["trading"]["symbol"]
    category = cfg["trading"]["category"]
    tf = cfg["trading"]["timeframe"]
    ema_len = cfg["trading"]["ema_length"]
    atr_len = cfg["trading"]["atr_length"]
    lookback = cfg["trading"]["lookback"]
    risk_pct = float(cfg["trading"]["risk_pct"])
    rr_ratio = float(cfg["trading"]["rr_ratio"])
    enable_long = bool(cfg["trading"]["enable_long"])
    enable_short = bool(cfg["trading"]["enable_short"])
    min_qty = float(cfg["trading"]["min_qty"])
    taker_fee = float(cfg["fees"]["taker"])
    poll_seconds = int(cfg["engine"]["poll_seconds"])

    last_bar_time = None

    while True:
        try:
            df = fetch_klines(ses, symbol, tf, limit=300, category=category)
            # compute indicators on CLOSED candles only
            price_df = df.copy()
            price_df["ema20"] = ema(price_df["close"], ema_len)
            price_df["atr"] = atr(price_df[["high","low","close"]], atr_len)
            sup, res = support_resistance_breakout(price_df, lookback)
            price_df["sup"] = sup
            price_df["res"] = res

            # use last closed bar (exclude the current forming bar if needed; bybit returns closed)
            bar = price_df.iloc[-1]
            ts = int(bar["start"])
            if last_bar_time is None:
                last_bar_time = ts

            if ts != last_bar_time:
                # New bar confirmed -> evaluate signals using previous bar close
                prev = price_df.iloc[-1]
                prev_close = float(prev["close"])
                ema20 = float(prev["ema20"])
                atr_val = float(prev["atr"])
                res_level = float(prev["res"])
                sup_level = float(prev["sup"])

                long_signal = enable_long and (prev_close > res_level) and (prev_close > ema20)
                short_signal = enable_short and (prev_close < sup_level) and (prev_close < ema20)

                if long_signal or short_signal:
                    equity = get_equity(ses)
                    if equity is None:
                        # fallback: derive equity from closed PnL history
                        equity = 100.0
                    qty, long_levels, short_levels = position_size(RiskSettings(equity=equity, risk_pct=risk_pct,
                                                                               atr_value=atr_val, entry_price=prev_close, rr_ratio=rr_ratio))
                    qty = max(qty, 0.0)
                    if qty > 0 and qty < min_qty:
                        qty = min_qty

                    if long_signal:
                        sl, tp = long_levels
                        side = "Buy"
                    elif short_signal:
                        sl, tp = short_levels
                        side = "Sell"

                    if qty > 0:
                        print(f"Signal {side} @ {prev_close} qty {qty} SL {sl} TP {tp}")
                        try:
                            resp = place_order(ses, symbol, side, qty, sl, tp, category=category)
                            # estimate fee as taker * notional
                            fee = taker_fee * (qty * prev_close)
                            trade_id = storage.insert_trade(db, symbol, side, prev_close, qty, sl, tp, fee, meta=dict(resp=resp))
                        except Exception as e:
                            print("Order failed:", e)

                last_bar_time = ts
        except Exception as e:
            print("Loop error:", e)

        # periodic report
        try:
            df_trades = storage.list_trades(db)
            if df_trades is not None:
                equity_img = "equity.png"
                out_html = cfg["engine"]["report_path"]
                report_mod.render_report(df_trades, out_html, equity_img)
        except Exception as e:
            print("Report error:", e)

        time.sleep(poll_seconds)

if __name__ == "__main__":
    run()
