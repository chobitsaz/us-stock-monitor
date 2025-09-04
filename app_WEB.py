import streamlit as st
import yfinance as yf
import pandas as pd

# 📌 頁面設定
st.set_page_config(page_title="美股前8大即時漲跌幅（依權重）", layout="wide")
st.title("📈 美股前8大即時漲跌幅（依權重排序）")

# ▶ 股票與「權重」（只用來排序；不參與未加權合計）
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

REFRESH_INTERVAL = 10  # 秒（建議設 10s，避免 Yahoo Finance 過度請求）

tickers = list(stock_weights.keys())

# 🔹 取得漲跌幅
def get_pct_change(tickers):
    df_1m = yf.download(tickers, period="1d", interval="1m", progress=False, threads=True)
    last = None
    if not df_1m.empty:
        try:
            last = df_1m["Close"].iloc[-1]        # 多檔 → Series
        except KeyError:
            last = df_1m["Adj Close"].iloc[-1]    # 備援

    df_daily = yf.download(tickers, period="2d", interval="1d", progress=False, threads=True)
    prev_close = df_daily["Close"].iloc[-2]

    if last is None or last.isna().all():
        last = df_daily["Close"].iloc[-1]

    pct = (last - prev_close) / prev_close * 100
    return pct

# 🔹 漲跌幅格式（正→粉紅底、負→綠底、黑色粗體字）
def highlight_pct(val):
    if pd.isna(val):
        return ""
    style = "color: black; font-weight: bold; font-size: 18px;"  # 字大一點
    if val > 0:
        return style + "background-color: #ffd6e7;"   # 粉紅
    if val < 0:
        return style + "background-color: #d6f5d6;"   # 淺綠
    return style

# 🔹 加權平均漲跌幅
def weighted_sum(df, n):
    sub = df.head(n)
    return (sub["Change%"] * sub["Weight"]).sum(skipna=True) / sub["Weight"].sum()

# ▶ 主程式（每次刷新會重新跑）
try:
    pct_change = get_pct_change(tickers)

    # ▶ 依權重排序（大→小）
    ordered = sorted(stock_weights.items(), key=lambda x: x[1], reverse=True)
    ordered_tickers = [t for t, _ in ordered]

    # ▶ 建立表格 + 編號 1~n
    df = pd.DataFrame({
        "No.": range(1, len(ordered_tickers)+1),
        "Ticker": ordered_tickers,
        "Change%": [pct_change.get(t, float("nan")) for t in ordered_tickers],
        "Weight": [stock_weights[t] for t in ordered_tickers],
    })

    # ▶ 樣式（白色表頭、編號欄白色字）
    styled = (
        df.style
          .format({"Weight": "{:.2%}", "Change%": "{:.2f}%"})
          .applymap(highlight_pct, subset=["Change%"])
          .set_table_styles([
              {"selector": "th", "props": [("color", "white"), ("font-weight", "bold"), ("background-color", "#333"), ("font-size", "16px")]},
          ])
          .applymap(lambda x: "color: white; font-weight: bold; font-size: 16px;", subset=["No."])
          .applymap(lambda x: "font-size: 18px; font-weight: bold;", subset=["Ticker"])  # 股名字大
    )

    # ▶ 合計計算
    sum3, sum5, sum8 = df["Change%"].head(3).sum(skipna=True), df["Change%"].head(5).sum(skipna=True), df["Change%"].head(8).sum(skipna=True)
    wsum3, wsum5, wsum8 = weighted_sum(df, 3), weighted_sum(df, 5), weighted_sum(df, 8)

    # ▶ 畫面輸出
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

# ▶ 自動刷新（避免 while True 卡住）
st_autorefresh = st.experimental_rerun  # Streamlit >=1.32 改名, 舊版用 st_autorefresh
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=REFRESH_INTERVAL * 1000, key="refresh")
except:
    pass
