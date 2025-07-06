import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import datetime
import time

st.set_page_config(page_title="Super Investor Screener", layout="wide")

@st.cache_data(ttl=3600)
def get_dataroma_tickers():
    url = "https://www.dataroma.com/m/grid.php"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table', {'class': 'grid'})
    rows = table.find_all('tr')[1:]  # skip header

    stocks = []
    for row in rows:
        cols = row.find_all('td')
        ticker = cols[0].text.strip()
        name = cols[1].text.strip()
        investors = cols[2].text.strip()
        price = cols[3].text.strip()
        stocks.append({
            "Ticker": ticker,
            "Company": name,
            "# of Investors": int(investors),
            "Holding Price": price.replace("$", "").replace(",", "")
        })

    return pd.DataFrame(stocks)

@st.cache_data(ttl=3600)
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        current_price = info.get("regularMarketPrice", None)
        low_52w = info.get("fiftyTwoWeekLow", None)
        high_52w = info.get("fiftyTwoWeekHigh", None)

        if not all([current_price, low_52w, high_52w]):
            return None

        above_low_pct = round((current_price - low_52w) / low_52w * 100, 2)
        below_high_pct = round((high_52w - current_price) / high_52w * 100, 2)

        return {
            "Current Price": current_price,
            "52W Low": low_52w,
            "52W High": high_52w,
            "% Above 52W Low": f"{above_low_pct}%",
            "% Below 52W High": f"{below_high_pct}%"
        }
    except Exception:
        return None

st.title("📈 Super Investor Stock Screener")
st.caption("Scraped from Dataroma and enriched with Yahoo Finance")

st.info("Fetching data from Dataroma...")
df = get_dataroma_tickers()

enriched_data = []
progress = st.progress(0)

for i, row in df.iterrows():
    stock_data = get_stock_data(row["Ticker"])
    if stock_data:
        enriched_data.append({
            **row.to_dict(),
            **stock_data
        })
    else:
        enriched_data.append(row.to_dict())
    progress.progress((i + 1) / len(df))

progress.empty()

result_df = pd.DataFrame(enriched_data)
cols = ["Ticker", "Company", "# of Investors", "Holding Price", "Current Price",
        "52W Low", "52W High", "% Above 52W Low", "% Below 52W High"]

result_df["Holding Price"] = pd.to_numeric(result_df["Holding Price"], errors="coerce")
result_df["Current Price"] = pd.to_numeric(result_df["Current Price"], errors="coerce")

st.dataframe(result_df[cols].sort_values(by="# of Investors", ascending=False), use_container_width=True)

csv = result_df[cols].to_csv(index=False)
st.download_button("📥 Download CSV", csv, "super_investor_stocks.csv", "text/csv")
