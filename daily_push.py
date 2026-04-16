import os
import yfinance as yf
import requests
from dotenv import load_dotenv

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.environ["LINE_TOKEN"]
GROUP_ID = os.environ["LINE_GROUP_ID"]

# 分組，方便排版和特殊處理
EQUITY_INDICES = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow Jones": "^DJI",
    "SOX": "^SOX",
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


def fetch_close_prev(symbol: str) -> tuple[float, float] | None:
    """回傳 (最新收盤, 前一交易日收盤)；失敗回 None。"""
    try:
        hist = yf.Ticker(symbol).history(period="5d")
        if len(hist) < 2:
            return None
        return float(hist["Close"].iloc[-1]), float(hist["Close"].iloc[-2])
    except Exception:
        return None


def format_pct(name: str, symbol: str, decimals: int = 2) -> str:
    data = fetch_close_prev(symbol)
    if data is None:
        return f"{name}: N/A"
    close, prev = data
    pct = (close - prev) / prev * 100
    arrow = "▲" if pct >= 0 else "▼"
    fmt = f"{{:,.{decimals}f}}"
    return f"{name}: {fmt.format(close)} {arrow}{pct:+.2f}%"


def format_bond(name: str, symbol: str) -> str:
    """^TNX 特殊處理：顯示殖利率 % + bps 變化。"""
    data = fetch_close_prev(symbol)
    if data is None:
        return f"{name}: N/A"
    close, prev = data
    # ^TNX 顯示值 = 殖利率 * 10，除以 10 得到真實殖利率 %
    yield_now = close / 10
    yield_prev = prev / 10
    bps = (yield_now - yield_prev) * 100  # 1% = 100 bps
    arrow = "▲" if bps >= 0 else "▼"
    return f"{name}: {yield_now:.3f}% {arrow}{bps:+.1f} bps"


def build_message() -> str:
    sections = []

    sections.append("📊 股指")
    for name, sym in EQUITY_INDICES.items():
        sections.append(format_pct(name, sym))

    sections.append("\n💱 匯率/加密")
    for name, sym in FX_CRYPTO.items():
        # BTC 價格大，小數點少一點；其他匯率保留 4 位
        decimals = 0 if name == "BTC" else 4
        sections.append(format_pct(name, sym, decimals=decimals))

    sections.append("\n🛢️ 商品")
    for name, sym in COMMODITIES.items():
        sections.append(format_pct(name, sym))

    sections.append("\n💵 債券殖利率")
    for name, sym in BONDS.items():
        sections.append(format_bond(name, sym))

    return "\n".join(sections)


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