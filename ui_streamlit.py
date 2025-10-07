import streamlit as st
import pandas as pd
import ccxt
import datetime
import matplotlib.pyplot as plt

st.title("Crypto Trading Indicator App")

# Inputs utilisateur
symbol = st.text_input("Pair (ex: BTC/USDT)", "BTC/USDT")
exchange_name = "binance"
start = st.date_input("Date de début", datetime.date(2024,1,1))
end = st.date_input("Date de fin", datetime.date.today())

# Charger les données avec CCXT
if st.button("Charger les données"):
    try:
        exchange = getattr(ccxt, exchange_name)()
        ohlcv = exchange.fetch_ohlcv(symbol, "1d", since=exchange.parse8601(str(start)+"T00:00:00Z"))
        df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df[df["timestamp"]<=pd.to_datetime(end)]

        st.write(df.tail())

        fig, ax = plt.subplots()
        ax.plot(df["timestamp"], df["close"], label="Close Price")
        ax.legend()
        st.pyplot(fig)

    except Exception as e:
        st.error(f"Erreur: {e}")
