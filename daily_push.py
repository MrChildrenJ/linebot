import os
import yfinance as yf
import requests
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.environ["LINE_TOKEN"]
GROUP_ID = os.environ["LINE_GROUP_ID"]

TICKERS = {
    "Dow Jones"
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "SOX": "^SOX",
}

def build_message() -> str:
    lines = ["📊 收盤行情摘要"]
    for name, sym in TICKERS.items():
        hist = yf.Ticker(sym).history(period="5d")
        if len(hist) < 2:
            lines.append(f"{name}: 資料不足")
            continue
        close = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        pct = (close - prev) / prev * 100
        arrow = "▲" if pct >= 0 else "▼"
        lines.append(f"{name}: {close:,.2f} {arrow}{pct:+.2f}%")
    return "\n".join(lines)

def push(text: str) -> None:
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": GROUP_ID, "messages": [{"type": "text", "text": text}]},
    )
    resp.raise_for_status()
    print("OK:", resp.status_code)

if __name__ == "__main__":
    msg = build_message()
    print(msg)
    push(msg)