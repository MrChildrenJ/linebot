import os
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf
import requests
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.environ["LINE_TOKEN"]
GROUP_ID = os.environ["LINE_GROUP_ID"]

COLOR_UP = "#00AA5B"   # 綠（漲）
COLOR_DOWN = "#D32F2F" # 紅（跌）
COLOR_FLAT = "#888888"
COLOR_HEADER = "#1DB446"
COLOR_LABEL = "#555555"

EQUITY_INDICES = {
    "Dow Jones": "^DJI",
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "SOX": "^SOX",
    "日經指數": "^N225",
    "台灣加權": "^TWII",
    "VIX": "^VIX",
}

FX_CRYPTO = {
    "DXY": "DX-Y.NYB",
    "USD/TWD": "TWD=X",
    "BTC": "BTC-USD",
}

COMMODITIES = {
    "Brent Oil": "BZ=F",
    "Gold": "GC=F",
}

BONDS = {
    "US 10Y": "^TNX",
}


def fetch_close_prev(symbol: str):
    try:
        hist = yf.Ticker(symbol).history(period="5d")
        if len(hist) < 2:
            return None
        return float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
    except Exception:
        return None


def color_of(pct: float) -> str:
    if pct > 0:
        return COLOR_UP
    if pct < 0:
        return COLOR_DOWN
    return COLOR_FLAT


def row(label: str, value_str: str, change_str: str, change_color: str) -> dict:
    """一個指標 row，三欄：名稱 / 價格 / 漲跌幅。"""
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "sm",
                "color": COLOR_LABEL,
                "flex": 3,
            },
            {
                "type": "text",
                "text": value_str,
                "size": "sm",
                "color": "#111111",
                "flex": 4,
                "align": "end",
            },
            {
                "type": "text",
                "text": change_str,
                "size": "sm",
                "color": change_color,
                "flex": 3,
                "align": "end",
                "weight": "bold",
            },
        ],
    }


def build_pct_row(name: str, symbol: str, decimals: int = 2) -> dict:
    data = fetch_close_prev(symbol)
    if data is None:
        return row(name, "N/A", "—", COLOR_FLAT)
    close, prev = data
    pct = (close - prev) / prev * 100
    fmt = f"{{:,.{decimals}f}}"
    value_str = fmt.format(close)
    change_str = f"{'▲' if pct >= 0 else '▼'}{pct:+.2f}%"
    return row(name, value_str, change_str, color_of(pct))


def build_bond_row(name: str, symbol: str) -> dict:
    """^TNX：殖利率 % + bps 變化。"""
    data = fetch_close_prev(symbol)
    if data is None:
        return row(name, "N/A", "—", COLOR_FLAT)
    close, prev = data
    y_now = close
    y_prev = prev
    bps = (y_now - y_prev) * 100
    value_str = f"{y_now:.3f}%"
    change_str = f"{'▲' if bps >= 0 else '▼'}{bps:+.1f} bps"
    return row(name, value_str, change_str, color_of(bps))


def section_header(title: str) -> dict:
    return {
        "type": "text",
        "text": title,
        "size": "sm",
        "weight": "bold",
        "color": "#333333",
        "margin": "md",
    }


def separator() -> dict:
    return {"type": "separator", "margin": "sm"}


def build_flex_message() -> dict:
    today_tw = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")

    contents = [
        # Header
        {
            "type": "text",
            "text": "📊 市場行情摘要",
            "weight": "bold",
            "size": "xl",
            "color": COLOR_HEADER,
        },
        {
            "type": "text",
            "text": today_tw,
            "size": "xs",
            "color": "#AAAAAA",
            "margin": "xs",
        },
        {"type": "separator", "margin": "md"},

        # 股指
        section_header("股指"),
    ]
    for name, sym in EQUITY_INDICES.items():
        contents.append(build_pct_row(name, sym))

    contents.append(separator())
    contents.append(section_header("匯率 / 加密"))
    for name, sym in FX_CRYPTO.items():
        decimals = 0 if name == "BTC" else 4
        contents.append(build_pct_row(name, sym, decimals=decimals))

    contents.append(separator())
    contents.append(section_header("商品"))
    for name, sym in COMMODITIES.items():
        contents.append(build_pct_row(name, sym))

    contents.append(separator())
    contents.append(section_header("債券殖利率"))
    for name, sym in BONDS.items():
        contents.append(build_bond_row(name, sym))

    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": contents,
        },
    }

    return {
        "type": "flex",
        "altText": f"美股收盤 {today_tw}",
        "contents": bubble,
    }


def push_flex(message: dict) -> None:
    resp = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers={
            "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"to": GROUP_ID, "messages": [message]},
    )
    if not resp.ok:
        print("ERROR:", resp.status_code, resp.text)
    resp.raise_for_status()
    print("OK:", resp.status_code)


if __name__ == "__main__":
    msg = build_flex_message()
    push_flex(msg)