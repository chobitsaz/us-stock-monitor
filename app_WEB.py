import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ── 基本設定 ─────────────────────────────────────────────
st.set_page_config(page_title="美股前8大漲跌幅", layout="wide")
st.title("📈 NQ前8大漲跌幅")

# 股票清單 + 權重
stock_weights = {
    "MSFT": 0.115,
    "AAPL": 0.105,
    "NVDA": 0.12,
    "AMZN": 0.075,
    "GOOGL": 0.06,
    "META": 0.059,
    "AVGO": 0.049,
    "TSLA": 0.024,
}
tickers = list(stock_weights.keys())

REFRESH_INTERVAL = 3  # 秒

# ── Sidebar 選擇模式 ─────────────────────────────────────
mode = st.sidebar.radio("選擇模式", ["盤中", "盤前"], index=0)

# ── 抓取盤中漲跌幅 ──────────────────────────────────────
def get_pct_change_intraday(tickers):
    df_1m = yf.download(tickers, period="1d", interval="1m", progress=False, threads=True)
    last = None
    if not df_1m.empty:
        try:
            last = df_1m["Close"].iloc[-1]
        except KeyError:
            last = df_1m["Adj Close"].iloc[-1]

    df_daily = yf.download(tickers, period="2d", interval="1d", progress=False, threads=True)
    try:
        prev_close = df_daily["Close"].iloc[-2]
    except IndexError:
        prev_close = df_daily["Close"].iloc[-1]

    if last is None or (hasattr(last, "isna") and last.isna().all()):
        last = df_daily["Close"].iloc[-1]

    pct = (last - prev_close) / prev_close * 100
    return pct

# ── 抓取盤前漲跌幅 ──────────────────────────────────────
def get_pct_change_premarket(tickers):
    pct_dict = {}
    for t in tickers:
        info = yf.Ticker(t).fast_info
        try:
            last = info.last_price
            prev_close = info.previous_close
            pct_dict[t] = (last - prev_close) / prev_close * 100 if prev_close else float("nan")
        except Exception:
            pct_dict[t] = float("nan")
    return pd.Series(pct_dict)

# ── 樣式 ───────────────────────────────────────────────
def style_change(col: pd.Series):
    maxv = col.max(skipna=True)
    out = []
    for v in col:
        if pd.isna(v):
            out.append("")
            continue
        style = "color: black; font-weight: bold; font-size: 18px;"
        if v > 0:
            style += "background-color: #ffd6e7;"
        elif v < 0:
            style += "background-color: #d6f5d6;"
        if v == maxv:
            style += " font-size: 22px;"
        out.append(style)
    return out

def weighted_sum(df, n):
    sub = df.head(n)
    return (sub["Change%"] * sub["Weight"]).sum(skipna=True) / sub["Weight"].sum()

# ── 主流程 ──────────────────────────────────────────────
try:
    if mode == "盤中":
        pct_change = get_pct_change_intraday(tickers)
    else:
        pct_change = get_pct_change_premarket(tickers)

    # 排序
    ordered = sorted(stock_weights.items(), key=lambda x: x[1], reverse=True)
    ordered_tickers = [t for t, _ in ordered]

    # 建立表格
    df = pd.DataFrame({
        "No.": range(1, len(ordered_tickers) + 1),
        "Ticker": ordered_tickers,
        "Change%": [pct_change.get(t, float("nan")) for t in ordered_tickers],
        "Weight": [stock_weights[t] for t in ordered_tickers],
    })

    styled = (
        df.style
          .format({"Weight": "{:.2%}", "Change%": "{:.2f}%"})
          .apply(style_change, subset=["Change%"])
          .set_table_styles([{
              "selector": "th",
              "props": [("color", "white"), ("font-weight", "bold"),
                        ("background-color", "#333"), ("font-size", "16px")]
          }])
          .applymap(lambda _: "font-size: 18px; font-weight: bold;", subset=["Ticker"])
    )

    # 合計
    sum3, sum5, sum8 = (
        df["Change%"].head(3).sum(skipna=True),
        df["Change%"].head(5).sum(skipna=True),
        df["Change%"].head(8).sum(skipna=True),
    )
    wsum3, wsum5, wsum8 = weighted_sum(df, 3), weighted_sum(df, 5), weighted_sum(df, 8)

    # 輸出
    st.dataframe(styled, height=350, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("前3大（未加權）",  f"{sum3:.2f}%")
        st.metric("前5大（未加權）",  f"{sum5:.2f}%")
        st.metric("前8大（未加權）",  f"{sum8:.2f}%")
    with col2:
        st.metric("前3大（加權）",  f"{wsum3:.2f}%")
        st.metric("前5大（加權）",  f"{wsum5:.2f}%")
        st.metric("前8大（加權）",  f"{wsum8:.2f}%")

    st.caption(f"⏱ {mode}模式，每 {REFRESH_INTERVAL} 秒更新一次（資料源：Yahoo Finance；盤中可能有延遲）")

except Exception as e:
    st.error(f"取得資料時發生錯誤：{e}")

# 自動刷新
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresh")
