
from dataclasses import dataclass

@dataclass
class RiskSettings:
    equity: float
    risk_pct: float   # e.g., 0.5 (%)
    atr_value: float
    entry_price: float
    rr_ratio: float

def position_size(settings: RiskSettings):
    # risk amount in account currency (USDT)
    risk_amount = settings.equity * (settings.risk_pct / 100.0)
    sl_dist = settings.atr_value
    if sl_dist <= 0:
        return 0.0, 0.0, 0.0
    # position notional based on risk
    notional = risk_amount / sl_dist
    qty = max(0.0, notional / settings.entry_price)
    tp_price_long = settings.entry_price + sl_dist * settings.rr_ratio
    sl_price_long = settings.entry_price - sl_dist
    tp_price_short = settings.entry_price - sl_dist * settings.rr_ratio
    sl_price_short = settings.entry_price + sl_dist
    return qty, (sl_price_long, tp_price_long), (sl_price_short, tp_price_short)
