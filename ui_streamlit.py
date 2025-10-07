import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date

st.set_page_config(page_title="Crypto Trading Indicator App", layout="centered")
st.title("Crypto Trading Indicator App")

st.write("Données via Yahoo Finance (yfinance) – pas de clé API, compatible Streamlit Cloud ✅")

# ---- Inputs
pair = st.text_input("Pair (format yfinance, ex: BTC-USD / ETH-USD)", "BTC-USD")
start_date = st.date_input("Date de début", date(2024, 1, 1))
end_date = st.date_input("Date de fin", date.today())

interval = st.selectbox(
"Intervalle",
["1d", "1h", "30m", "15m", "5m"], # 1h et moins: dispo sur une période plus courte
index=0
)

@st.cache_data(show_spinner=False)
def load_data(symbol: str, start: date, end: date, interval: str) -> pd.DataFrame:
df = yf.download(symbol, start=start, end=end, interval=interval, auto_adjust=False, progress=False)
df = df.rename(columns=str.title)
return df

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
delta = series.diff()
up = delta.clip(lower=0)
down = -delta.clip(upper=0)
roll_up = up.rolling(period).mean()
roll_down = down.rolling(period).mean()
rs = roll_up / roll_down
return 100 - (100 / (1 + rs))

if st.button("Charger les données"):
try:
data = load_data(pair, start_date, end_date, interval)
if data.empty:
st.error("Aucune donnée récupérée. Essaie un autre symbole (ex: BTC-USD) ou rapproche les dates.")
else:
data["SMA20"] = data["Close"].rolling(20).mean()
data["SMA50"] = data["Close"].rolling(50).mean()
data["RSI14"] = rsi(data["Close"], 14)

st.subheader("Aperçu des données")
st.dataframe(data.tail(10))

st.subheader("Cours & Moyennes mobiles")
st.line_chart(data[["Close", "SMA20", "SMA50"]])

st.subheader("RSI (14)")
st.line_chart(data[["RSI14"]])

# Signaux simples (croisement SMA20/SMA50)
signals = []
for i in range(1, len(data)):
if pd.notna(data["SMA20"].iloc[i-1]) and pd.notna(data["SMA50"].iloc[i-1]):
if data["SMA20"].iloc[i-1] <= data["SMA50"].iloc[i-1] and data["SMA20"].iloc[i] > data["SMA50"].iloc[i]:
signals.append((data.index[i], "BUY"))
elif data["SMA20"].iloc[i-1] >= data["SMA50"].iloc[i-1] and data["SMA20"].iloc[i] < data["SMA50"].iloc[i]:
signals.append((data.index[i], "SELL"))

st.subheader("Signaux détectés")
if signals:
st.write(pd.DataFrame(signals, columns=["Date", "Signal"]).tail(20))
else:
st.info("Pas de signaux détectés sur la période choisie.")

except Exception as e:
st.error(f"Erreur lors du chargement des données : {e}")
