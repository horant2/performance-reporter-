import os
import time
import requests
import yfinance as yf
from datetime import datetime, timedelta
import pytz

TELEGRAM_PERFORMANCE_TOKEN = os.environ.get("TELEGRAM_PERFORMANCE_TOKEN")
TELEGRAM_PERFORMANCE_CHAT_ID = os.environ.get("TELEGRAM_PERFORMANCE_CHAT_ID")

MISFITS_API_KEY = os.environ.get("MISFITS_ALPACA_API_KEY")
MISFITS_SECRET_KEY = os.environ.get("MISFITS_ALPACA_SECRET_KEY")

OMNISCIENT_API_KEY = os.environ.get("OMNISCIENT_ALPACA_API_KEY")
OMNISCIENT_SECRET_KEY = os.environ.get("OMNISCIENT_ALPACA_SECRET_KEY")

ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
INCEPTION_VALUE = 100000
INCEPTION_DATE = "2026-05-08"

def send_performance(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_PERFORMANCE_TOKEN}/sendMessage"
    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        try:
            requests.post(url, json={"chat_id": TELEGRAM_PERFORMANCE_CHAT_ID, "text": chunk}, timeout=10)
        except Exception as e:
            print(f"Send error: {e}")
        time.sleep(1)

def get_alpaca_account(api_key, secret_key):
    try:
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        }
        r = requests.get(f"{ALPACA_BASE_URL}/v2/account", headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Alpaca error: {e}")
        return {}

def get_alpaca_positions(api_key, secret_key):
    try:
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        }
        r = requests.get(f"{ALPACA_BASE_URL}/v2/positions", headers=headers, timeout=10)
        return r.json()
    except Exception as e:
        print(f"Positions error: {e}")
        return []

def get_alpaca_history(api_key, secret_key, period="1W"):
    try:
        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": secret_key
        }
        r = requests.get(
            f"{ALPACA_BASE_URL}/v2/account/portfolio/history",
            headers=headers,
            params={"period": period, "timeframe": "1D"},
            timeout=10
        )
        return r.json()
    except Exception as e:
        print(f"History error: {e}")
        return {}

def get_spy_return(days=7):
    try:
        spy = yf.download("SPY", period="1mo", progress=False)["Close"].squeeze()
        spy_return = float((spy.iloc[-1] - spy.iloc[-days]) / spy.iloc[-days] * 100)
        spy_total = float((spy.iloc[-1] - spy.iloc[0]) / spy.iloc[0] * 100)
        return spy_return, spy_total
    except:
        return 0, 0

def format_positions(positions):
    if not isinstance(positions, list) or len(positions) == 0:
        return "  No open positions"
    lines = []
    for pos in positions:
        symbol = pos.get("symbol", "")
        side = pos.get("side", "long")
        qty = float(pos.get("qty", 0))
        market_val = float(pos.get("market_value", 0))
        unrealized_pnl = float(pos.get("unrealized_pl", 0))
        unrealized_pct = float(pos.get("unrealized_plpc", 0)) * 100
        pnl_emoji = "✅" if unrealized_pnl >= 0 else "⚠️"
        direction = "Long" if side == "long" else "Short"
        lines.append(f"  {pnl_emoji} {symbol} ({direction}) {qty:.2f} shares | ${market_val:,.0f} | {'+' if unrealized_pnl >= 0 else ''}{unrealized_pnl:,.0f} ({unrealized_pct:+.1f}%)")
    return "\n".join(lines)

def build_daily_report():
    et = pytz.timezone("America/New_York")
    now = datetime.now(et)
    date_str = now.strftime("%A, %B %d %Y")

    misfits_account = get_alpaca_account(MISFITS_API_KEY, MISFITS_SECRET_KEY)
    omniscient_account = get_alpaca_account(OMNISCIENT_API_KEY, OMNISCIENT_SECRET_KEY)
    misfits_positions = get_alpaca_positions(MISFITS_API_KEY, MISFITS_SECRET_KEY)
    omniscient_positions = get_alpaca_positions(OMNISCIENT_API_KEY, OMNISCIENT_SECRET_KEY)

    misfits_value = float(misfits_account.get("portfolio_value", INCEPTION_VALUE))
    omniscient_value = float(omniscient_account.get("portfolio_value", INCEPTION_VALUE))

    misfits_net = misfits_value - INCEPTION_VALUE
    omniscient_net = omniscient_value - INCEPTION_VALUE
    misfits_pct = misfits_net / INCEPTION_VALUE * 100
    omniscient_pct = omniscient_net / INCEPTION_VALUE * 100

    misfits_history = get_alpaca_history(MISFITS_API_KEY, MISFITS_SECRET_KEY, "1W")
    omniscient_history = get_alpaca_history(OMNISCIENT_API_KEY, OMNISCIENT_SECRET_KEY, "1W")

    misfits_week = 0
    omniscient_week = 0
    try:
        m_equity = misfits_history.get("equity", [])
        if len(m_equity) >= 2:
            misfits_week = (m_equity[-1] - m_equity[0]) / m_equity[0] * 100
    except:
        pass
    try:
        o_equity = omniscient_history.get("equity", [])
        if len(o_equity) >= 2:
            omniscient_week = (o_equity[-1] - o_equity[0]) / o_equity[0] * 100
    except:
        pass

    spy_week, spy_total = get_spy_return(7)

    winner = "THE MISFITS" if misfits_pct > omniscient_pct else "OMNISCIENTBOT"
    winner_margin = abs(misfits_pct - omniscient_pct)

    misfits_vs_spy = misfits_pct - spy_total
    omniscient_vs_spy = omniscient_pct - spy_total

    report = f"""📊 SATIS HOUSE TRADING SYSTEMS
Daily Performance Report
{date_str}

{'='*40}
HEAD TO HEAD SINCE INCEPTION
{'='*40}

🤖 THE MISFITS
Portfolio value: ${misfits_value:,.2f}
Net profit: {'+' if misfits_net >= 0 else ''}${misfits_net:,.0f} ({'+' if misfits_pct >= 0 else ''}{misfits_pct:.2f}%)
This week: {'+' if misfits_week >= 0 else ''}{misfits_week:.2f}%
vs SPY since inception: {'+' if misfits_vs_spy >= 0 else ''}{misfits_vs_spy:.2f}%

Open positions:
{format_positions(misfits_positions)}

⚡ OMNISCIENTBOT
Portfolio value: ${omniscient_value:,.2f}
Net profit: {'+' if omniscient_net >= 0 else ''}${omniscient_net:,.0f} ({'+' if omniscient_pct >= 0 else ''}{omniscient_pct:.2f}%)
This week: {'+' if omniscient_week >= 0 else ''}{omniscient_week:.2f}%
vs SPY since inception: {'+' if omniscient_vs_spy >= 0 else ''}{omniscient_vs_spy:.2f}%

Open positions:
{format_positions(omniscient_positions)}

📈 SPY BENCHMARK
This week: {'+' if spy_week >= 0 else ''}{spy_week:.2f}%
Since inception: {'+' if spy_total >= 0 else ''}{spy_total:.2f}%

{'='*40}
🏆 CURRENTLY WINNING: {winner}
Margin: {winner_margin:.2f}%
{'='*40}

Both systems started at ${INCEPTION_VALUE:,}
Inception date: {INCEPTION_DATE}

-- Satis House Consulting"""

    return report

def run():
    et = pytz.timezone("America/New_York")
    last_report_date = None

    print("Performance reporter started")
    send_performance("📊 Performance reporter online. Daily reports fire at 9 AM ET.\n\n-- Satis House Consulting")

    while True:
        now = datetime.now(et)
        today = now.date()

        if (now.hour == 9 and now.minute < 15 and
                last_report_date != today and
                now.weekday() < 5):

            print(f"Generating daily report for {today}")
            try:
                report = build_daily_report()
                send_performance(report)
                last_report_date = today
                print("Daily report sent")
            except Exception as e:
                print(f"Report error: {e}")
                send_performance(f"Performance reporter error: {e}")

        time.sleep(60)

if __name__ == "__main__":
    run()
