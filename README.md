
# Bybit EMA20 Breakout Bot (No TradingView)

Runs 24/7 on a VPS (e.g., Hostinger) and trades Bybit USDT perpetuals using:
- EMA20 breakout over recent Resistance/Support (lookback N)
- ATR(14) for SL distance
- Fixed risk 0.5% per trade
- Risk/Reward 1:4 (TP distance = 4 × ATR)
- Auto report (TradingView-style): equity curve, stats, and trade list

## 1) Setup

```bash
# on your VPS
sudo apt update && sudo apt install -y python3-pip git
python3 -V

# clone/upload this folder or copy via SFTP
cd bybit_ema20_bot

# install deps
pip install -r requirements.txt
```

Create your `config.yaml` from example:
```bash
cp config.example.yaml config.yaml
nano config.yaml
```

Set:
- `bybit.api_key`, `bybit.api_secret`
- `bybit.testnet: false` for live
- symbol, timeframe, etc.

## 2) Run

```bash
python bot.py
```

The bot will create/update:
- SQLite: `bot.db`
- Report HTML: `report.html`
- Equity image: `equity.png`

Open `report.html` in a browser (download via SFTP) — it looks similar to TradingView summary.

## 3) Docker (optional)

```bash
docker build -t bybit-ema20-bot .
docker run -d --name ema20 --restart=always -v $(pwd)/config.yaml:/app/config.yaml -v $(pwd)/bot.db:/app/bot.db -v $(pwd)/report.html:/app/report.html -v $(pwd)/equity.png:/app/equity.png bybit-ema20-bot
```

## 4) Systemd service (optional)

Create `/etc/systemd/system/ema20.service`:

```
[Unit]
Description=Bybit EMA20 Bot
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/bybit_ema20_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always
User=ubuntu

[Install]
WantedBy=multi-user.target
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ema20 --now
sudo systemctl status ema20
```

## 5) Notes & Safety

- This example uses **market orders** and sets TP/SL via `set_trading_stop` (Bybit v5). Ensure your account is in **Unified Trading**.
- Leverage should be configured on the exchange side; qty sizing is based on ATR risk model.
- Fees are estimated for reporting; the exchange will compute actual fees.
- Always test with **testnet** first (`bybit.testnet: true`).

## 6) Backtest (quick)

You can adapt `bot.py` to run in a **backtest** mode by fetching historical klines, looping through bars and simulating fills. The current version focuses on **live** trading and logging.
```

