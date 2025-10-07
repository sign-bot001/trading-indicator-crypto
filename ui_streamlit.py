import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import date

st.set_page_config(page_title="Crypto Trading Indicator App", layout="centered")
st.title("Crypto Trading Indicator App")
st.write("Données via Yahoo Finance (yfinance) – pas de clé API, compatible Streamlit Cloud ✅")

# ---- Inputs
pair = st.text_input("Pair (format yfinance, ex: BTC-USD / ETH-USD)", "BTC-USD")
start_date = st.date_input("Date de début", date(2024, 1, 1))
end_date = st.date_input("Date de fin", date.today())
interval = st.selectbox("Intervalle", ["1d", "1h", "30m", "15m", "5m"], index=0)

col1, col2, col3 = st.columns(3)
with col1:
    sma_fast = st.number_input("SMA courte", 5, 100, 20)
with col2:
    sma_slow = st.number_input("SMA longue", 10, 300, 50)
with col3:
    rsi_len = st.number_input("RSI période", 5, 50, 14)

@st.cache_data(show_spinner=False)
def load_data(symbol: str, start: date, end: date, interval: str) -> pd.DataFrame:
    df = yf.download(
        symbol, start=start, end=end, interval=interval,
        auto_adjust=True, progress=False
    )
    # yfinance renvoie parfois des colonnes MultiIndex -> on aplatit
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.title)             # Open, High, Low, Close, Volume
    if hasattr(df.index, "tz_convert"):           # retire le timezone si présent (plotly/streamlit aiment naïf)
        try:
            df.index = df.index.tz_localize(None)
        except Exception:
            pass
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
        elif "Close" not in data.columns:
            st.error(f"Colonne 'Close' introuvable. Colonnes = {list(data.columns)}")
        else:
            # Indicateurs
            data[f"SMA{sma_fast}"] = data["Close"].rolling(int(sma_fast)).mean()
            data[f"SMA{sma_slow}"] = data["Close"].rolling(int(sma_slow)).mean()
            data[f"RSI{rsi_len}"] = rsi(data["Close"], int(rsi_len))

            st.subheader("Aperçu des données")
            st.dataframe(data.tail(10))

            # -------- Graphique bougies + SMA --------
            st.subheader("Graphique en bougies")
            fig = go.Figure(data=[go.Candlestick(
                x=data.index,
                open=data["Open"],
                high=data["High"],
                low=data["Low"],
                close=data["Close"],
                name="OHLC"
            )])
            fig.add_trace(go.Scatter(x=data.index, y=data[f"SMA{sma_fast}"], name=f"SMA{sma_fast}"))
            fig.add_trace(go.Scatter(x=data.index, y=data[f"SMA{sma_slow}"], name=f"SMA{sma_slow}"))
            fig.update_layout(xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            # -------- Lignes Close + SMA --------
            st.subheader("Cours & Moyennes mobiles")
            st.line_chart(data[["Close", f"SMA{sma_fast}", f"SMA{sma_slow}"]])

            # -------- RSI --------
            st.subheader(f"RSI ({rsi_len})")
            st.line_chart(data[[f"RSI{rsi_len}"]])

            # -------- Signaux croisement SMA --------
            signals = []
            for i in range(1, len(data)):
                a1, b1 = data[f"SMA{sma_fast}"].iloc[i-1], data[f"SMA{sma_slow}"].iloc[i-1]
                a2, b2 = data[f"SMA{sma_fast}"].iloc[i],   data[f"SMA{sma_slow}"].iloc[i]
                if pd.notna(a1) and pd.notna(b1) and pd.notna(a2) and pd.notna(b2):
                    if a1 <= b1 and a2 > b2:
                        signals.append((data.index[i], "BUY"))
                    elif a1 >= b1 and a2 < b2:
                        signals.append((data.index[i], "SELL"))

            st.subheader("Signaux détectés")
            sig_df = pd.DataFrame(signals, columns=["Date", "Signal"])
            if not sig_df.empty:
                st.dataframe(sig_df.tail(50))
            else:
                st.info("Pas de signaux détectés sur la période choisie.")

            # -------- Téléchargements --------
            st.subheader("Téléchargements")
            st.download_button(
                "📥 Télécharger les données (CSV)",
                data=data.to_csv().encode("utf-8"),
                file_name=f"{pair.replace('-','_')}_{interval}.csv",
                mime="text/csv"
            )
            st.download_button(
                "📥 Télécharger les signaux (CSV)",
                data=sig_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{pair.replace('-','_')}_signals.csv",
                mime="text/csv",
                disabled=sig_df.empty
            )

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
