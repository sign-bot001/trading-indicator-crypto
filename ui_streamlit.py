import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import date

st.set_page_config(page_title="Crypto Trading Indicator App", layout="centered")
st.title("Crypto Trading Indicator App")

st.write("Données via Yahoo Finance (yfinance) – pas de clé API, compatible Streamlit Cloud ✅")

pair = st.text_input("Pair (format yfinance, ex: BTC-USD / ETH-USD)", "BTC-USD")
start_date = st.date_input("Date de début", date(2024, 1, 1))
end_date = st.date_input("Date de fin", date.today())
interval = st.selectbox("Intervalle", ["1d", "1h", "30m", "15m", "5m"], index=0)

@st.cache_data(show_spinner=False)
def load_data(symbol: str, start: date, end: date, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=True,
        progress=False
    )
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
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
            if "Close" not in data.columns:
                st.error(f"Colonne 'Close' non trouvée. Colonnes disponibles : {list(data.columns)}")
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

                signals = []
                for i in range(1, len(data)):
                    a1, b1 = data["SMA20"].iloc[i-1], data["SMA50"].iloc[i-1]
                    a2, b2 = data["SMA20"].iloc[i],   data["SMA50"].iloc[i]
                    if pd.notna(a1) and pd.notna(b1) and pd.notna(a2) and pd.notna(b2):
                        if a1 <= b1 and a2 > b2:
                            signals.append((data.index[i], "BUY"))
                        elif a1 >= b1 and a2 < b2:
                            signals.append((data.index[i], "SELL"))

                st.subheader("Signaux détectés")
                if signals:
                    st.write(pd.DataFrame(signals, columns=["Date", "Signal"]).tail(20))
                else:
                    st.info("Pas de signaux détectés sur la période choisie.")
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
import plotly.graph_objects as go

st.subheader("Graphique en bougies")
fig = go.Figure(data=[go.Candlestick(
    x=data.index,
    open=data["Open"],
    high=data["High"],
    low=data["Low"],
    close=data["Close"]
)])
# Ajoute les moyennes sur le graphe
fig.add_trace(go.Scatter(x=data.index, y=data["SMA20"], name="SMA20"))
fig.add_trace(go.Scatter(x=data.index, y=data["SMA50"], name="SMA50"))
st.plotly_chart(fig, use_container_width=True)
st.subheader("Téléchargements")

# CSV des données
csv_data = data.to_csv().encode("utf-8")
st.download_button(
    "📥 Télécharger les données (CSV)",
    data=csv_data,
    file_name=f"{pair.replace('-','_')}_{interval}.csv",
    mime="text/csv"
)

# CSV des signaux
import io
import pandas as pd
signals_df = pd.DataFrame(signals, columns=["Date", "Signal"]) if signals else pd.DataFrame(columns=["Date","Signal"])
csv_signals = signals_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Télécharger les signaux (CSV)",
    data=csv_signals,
    file_name=f"{pair.replace('-','_')}_signals.csv",
    mime="text/csv",
    disabled=signals_df.empty
)
col1, col2, col3 = st.columns(3)
with col1:
    sma_fast = st.number_input("SMA courte", 5, 100, 20)
with col2:
    sma_slow = st.number_input("SMA longue", 10, 200, 50)
with col3:
    rsi_len = st.number_input("RSI période", 5, 50, 14)

# Remplace tes calculs par :
data[f"SMA{sma_fast}"] = data["Close"].rolling(sma_fast).mean()
data[f"SMA{sma_slow}"] = data["Close"].rolling(sma_slow).mean()
data[f"RSI{rsi_len}"] = rsi(data["Close"], rsi_len)

# Et adapte les lignes de graphiques/colonnes :
st.line_chart(data[["Close", f"SMA{sma_fast}", f"SMA{sma_slow}"]])
st.line_chart(data[[f"RSI{rsi_len}"]])
