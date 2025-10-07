# ui_streamlit.py
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import date

# Page config
st.set_page_config(page_title="Crypto Trading Indicator App", layout="wide", page_icon="📈")

# --------- Protection par mot de passe simple (utilise st.secrets) ----------
def check_password():
    """
    Demande un mot de passe simple. Le mot de passe doit être ajouté dans
    Streamlit Cloud -> Settings -> Secrets sous la clé: password
    Ex: password = "tonMotDePasseIci"
    """
    if "password_correct" in st.session_state and st.session_state["password_correct"]:
        return True

    def password_entered():
        # Vérifie le mot de passe entré avec celui stocké dans st.secrets
        if "password" not in st.secrets:
            st.error("Le mot de passe n'est pas configuré dans les Secrets (Settings → Secrets).")
            return
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            # on supprime le mot de passe de la session pour sécurité
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    # Si pas encore entré, afficher le champ
    if "password_correct" not in st.session_state:
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        st.error("Mot de passe incorrect")
        return False
    else:
        return True

# Si la vérification passe, on affiche l'app
if check_password():

    st.sidebar.markdown("### 🔒 Accès protégé")
    st.sidebar.write("Vous êtes connecté(e). Pour vous déconnecter, fermez l'onglet ou cliquez sur 'Reset' ci-dessous.")
    if st.sidebar.button("Reset"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.experimental_rerun()

    # --- Titre et description
    st.title("📈 Crypto Trading Indicator App — Signaux")
    st.caption("Générateur de signaux basé sur SMA / RSI. **Ne constitue pas un conseil financier.**")

    # ---- Inputs (main)
    with st.container():
        col_a, col_b, col_c = st.columns([2, 1, 1])
        with col_a:
            pair = st.text_input("Pair (format yfinance) — ex: BTC-USD, ETH-USD", "BTC-USD")
        with col_b:
            start_date = st.date_input("Date de début", date(2024, 1, 1))
        with col_c:
            end_date = st.date_input("Date de fin", date.today())

        col_d, col_e = st.columns([1, 1])
        with col_d:
            interval = st.selectbox("Intervalle", ["1d", "1h", "30m", "15m", "5m"], index=0)
        with col_e:
            strategy = st.selectbox("Stratégie", ["SMA cross", "RSI zones"], index=0)

    # ---- Paramètres réglables
    with st.expander("⚙️ Paramètres indicateurs", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            sma_fast = st.number_input("SMA courte (période)", min_value=2, max_value=200, value=20)
        with col2:
            sma_slow = st.number_input("SMA longue (période)", min_value=3, max_value=400, value=50)
        with col3:
            rsi_len = st.number_input("RSI période", min_value=5, max_value=50, value=14)

    # ---- Chargement des données (cache pour accélérer)
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
        # si MultiIndex (cas yfinance multi-asset), on aplati au niveau 0
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
        # uniformiser la casse (Close, Open, High, Low, Volume)
        df = df.rename(columns=str.title)
        # retirer tz si existant pour compatibilité plotly
        try:
            if hasattr(df.index, "tz") and df.index.tz is not None:
                df.index = df.index.tz_convert(None)
        except Exception:
            pass
        return df

    # Bouton pour charger
    if st.button("Charger les données"):
        try:
            data = load_data(pair, start_date, end_date, interval)
            if data is None or data.empty:
                st.error("Aucune donnée récupérée — vérifie le symbole, les dates ou l'intervalle.")
            elif "Close" not in data.columns:
                st.error(f"Colonne 'Close' introuvable. Colonnes disponibles : {list(data.columns)}")
            else:
                # Calcul des indicateurs
                data[f"SMA{sma_fast}"] = data["Close"].rolling(int(sma_fast)).mean()
                data[f"SMA{sma_slow}"] = data["Close"].rolling(int(sma_slow)).mean()
                data[f"RSI{rsi_len}"] = (data["Close"].diff().clip(lower=0).rolling(int(rsi_len)).mean() /
                                         data["Close"].diff().abs().rolling(int(rsi_len)).mean() * 100).fillna(method="bfill")
                # fallback RSI simple si calcul ci-dessus non fiable
                def rsi_calc(series, period):
                    delta = series.diff()
                    up = delta.clip(lower=0)
                    down = -delta.clip(upper=0)
                    roll_up = up.rolling(period).mean()
                    roll_down = down.rolling(period).mean()
                    rs = roll_up / roll_down
                    return 100 - (100 / (1 + rs))
                data[f"RSI{rsi_len}"] = rsi_calc(data["Close"], int(rsi_len))

                # Affichage données
                st.subheader("Aperçu (dernières lignes)")
                st.dataframe(data.tail(10))

                # Candlestick Plotly
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
                fig.update_layout(xaxis_rangeslider_visible=False, height=500)
                st.plotly_chart(fig, use_container_width=True)

                # Graphiques rapides
                st.subheader("Cours & Moyennes mobiles")
                st.line_chart(data[["Close", f"SMA{sma_fast}", f"SMA{sma_slow}"]])

                st.subheader(f"RSI ({rsi_len})")
                st.line_chart(data[[f"RSI{rsi_len}"]])

                # Generer les signaux selon la stratégie choisie
                signals = []
                if strategy == "SMA cross":
                    a = data[f"SMA{sma_fast}"]
                    b = data[f"SMA{sma_slow}"]
                    for i in range(1, len(data)):
                        if pd.notna(a.iloc[i-1]) and pd.notna(b.iloc[i-1]) and pd.notna(a.iloc[i]) and pd.notna(b.iloc[i]):
                            if a.iloc[i-1] <= b.iloc[i-1] and a.iloc[i] > b.iloc[i]:
                                signals.append((data.index[i], "BUY"))
                            elif a.iloc[i-1] >= b.iloc[i-1] and a.iloc[i] < b.iloc[i]:
                                signals.append((data.index[i], "SELL"))
                elif strategy == "RSI zones":
                    r = data[f"RSI{rsi_len}"]
                    for i in range(1, len(data)):
                        if pd.notna(r.iloc[i-1]) and pd.notna(r.iloc[i]):
                            # sortie de survente -> BUY ; sortie de surachat -> SELL
                            if r.iloc[i-1] < 30 <= r.iloc[i]:
                                signals.append((data.index[i], "BUY"))
                            elif r.iloc[i-1] > 70 >= r.iloc[i]:
                                signals.append((data.index[i], "SELL"))

                # Affichage signaux
                st.subheader("Signaux détectés (historique)")
                if signals:
                    sig_df = pd.DataFrame(signals, columns=["Date", "Signal"])
                    st.dataframe(sig_df.tail(50))
                    last_ts, last_sig = signals[-1]
                    st.success(f"Dernier signal : {last_sig} • {last_ts}")
                else:
                    sig_df = pd.DataFrame(columns=["Date", "Signal"])
                    st.info("Pas de signaux détectés sur la période choisie.")

                # Téléchargement CSV
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

    # Footer / info
    st.markdown("---")
    st.caption("⚠️ Ce service fournit des signaux basés sur des règles techniques. Ce n'est pas un conseil financier.")

    
