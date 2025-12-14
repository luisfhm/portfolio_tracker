import yfinance as yf
import pandas as pd

def fetch_live_prices(df):
    """Descarga precios actuales y actualiza el DataFrame con precios live."""
    
    # Mapa de tickers a Yahoo Finance
    ticker_map = {}
    for t in df["ticker"]:
        if t in ["AGUA", "ALSEA", "CEMEX", "FMTY", "FUNO", "GMXT", "KOF", "NAFTRAC"]:
            ticker_map[t] = t + ".MX"
        elif t == "1211":
            ticker_map[t] = "1211.HK"
        else:
            # La mayoría son US (AMZN, NIO, NU, BOTZ, ICLN, etc.)
            ticker_map[t] = t
    
    yf_tickers = list(ticker_map.values())
    
    try:
        data = yf.download(yf_tickers, period="2d", auto_adjust=True, progress=False)["Close"]
        latest_prices = data.iloc[-1]  # Último precio disponible
    except Exception as e:
        st.error(f"Error descargando precios: {e}")
        return df  # Devuelve sin cambios
    
    # Actualizar precios
    for idx, row in df.iterrows():
        yf_ticker = ticker_map[row["ticker"]]
        if yf_ticker in latest_prices.index and pd.notna(latest_prices[yf_ticker]):
            live_price = latest_prices[yf_ticker]
        else:
            live_price = row["precio_mercado"]  # fallback al estático
            st.warning(f"No se pudo obtener precio live para {row['ticker']} ({yf_ticker})")
        
        df.at[idx, "precio_mercado"] = live_price
        df.at[idx, "valor_mercado"] = live_price * row["titulos"]
    
    # Recálculos
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct"] = (df["ganancia_live"] / df["costo_total"]) * 100
    
    return df