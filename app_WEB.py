import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh

# ── 基本設定 ─────────────────────────────────────────────
st.set_page_config(page_title="美股前8大即時漲跌幅（依權重）", layout="wide")
st.title("📈 NQ前8大即時")

# 股票清單 + 權重（僅用來排序；未加權合計不使用權重）
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

REFRESH_INTERVAL = 3  # 每幾秒自動刷新（雲端建議 ≥10s，避免過度請求）

tickers = list(stock_weights.keys())

# ── 抓取漲跌幅 ────────────────────────────────────────────
def get_pct_change(tickers):
    # 1m 最新價
    df_1m = yf.download(tickers, period="1d", interval="1m", progress=False, threads=True)
    last = None
    if not df_1m.empty:
        try:
            last = df_1m["Close"].iloc[-1]        # 多檔→Series
        except KeyError:
            last = df_1m["Adj Close"].iloc[-1]    # 備援

    # 前一交易日收盤
    df_daily = yf.download(tickers, period="2d", interval="1d", progress=False, threads=True)
    try:
        prev_close = df_daily["Close"].iloc[-2]
    except IndexError:
        prev_close = df_daily["Close"].iloc[-1]

    # 週末/收盤後取不到1m時，退回當日收盤（顯示 0%）
    if last is None or (hasattr(last, "isna") and last.isna().all()):
        last = df_daily["Close"].iloc[-1]

    pct = (last - prev_close) / prev_close * 100
    return pct

# ── 樣式：漲跌幅底色 + 最大漲幅字體更大 ──────────────────────
def style_change(col: pd.Series):
    maxv = col.max(skipna=True)
    out = []
    for v in col:
        if pd.isna(v):
            out.append("")
            continue
        style = "color: black; font-weight: bold; font-size: 18px;"
        if v > 0:
            style += "background-color: #ffd6e7;"   # 粉紅
        elif v < 0:
            style += "background-color: #d6f5d6;"   # 淺綠
        if v == maxv:
            style += " font-size: 22px;"            # 漲幅最大再加大
        out.append(style)
    return out

# ── 加權平均（用你提供的權重） ─────────────────────────────
def weighted_sum(df, n):
    sub = df.head(n)
    return (sub["Change%"] * sub["Weight"]).sum(skipna=True) / sub["Weight"].sum()

# ── 主流程（每次頁面重新執行一次） ─────────────────────────
try:
    pct_change = get_pct_change(tickers)

    # 依權重排序（大→小）
    ordered = sorted(stock_weights.items(), key=lambda x: x[1], reverse=True)
    ordered_tickers = [t for t, _ in ordered]

    # 建立表格 + 編號 1~n
    df = pd.DataFrame({
        "No.": range(1, len(ordered_tickers) + 1),
        "Ticker": ordered_tickers,
        "Change%": [pct_change.get(t, float("nan")) for t in ordered_tickers],
        "Weight": [stock_weights[t] for t in ordered_tickers],
    })

    # 表格樣式（白色表頭、編號白字、股名字體較大）
    styled = (
        df.style
          .format({"Weight": "{:.2%}", "Change%": "{:.2f}%"})
          .apply(style_change, subset=["Change%"])
          .set_table_styles([
              {"selector": "th", "props": [("color", "white"), ("font-weight", "bold"),
                                           ("background-color", "#333"), ("font-size", "16px")]},
          ])
          #.applymap(lambda _: "color: white; font-weight: bold; font-size: 16px;", subset=["No."])
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

    st.subheader("📊 前幾大合計比較")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("前3大（未加權）",  f"{sum3:.2f}%")
        st.metric("前5大（未加權）",  f"{sum5:.2f}%")
        st.metric("前8大（未加權）",  f"{sum8:.2f}%")

    with col2:
        st.metric("前3大（加權）",  f"{wsum3:.2f}%")
        st.metric("前5大（加權）",  f"{wsum5:.2f}%")
        st.metric("前8大（加權）",  f"{wsum8:.2f}%")

    st.caption(f"⏱ 每 {REFRESH_INTERVAL} 秒更新一次（資料源：Yahoo Finance；盤中可能有數十秒延遲）")

except Exception as e:
    st.error(f"取得資料時發生錯誤：{e}")

# ── 自動刷新（真正可用的元件） ─────────────────────────────
st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="auto_refresh")
