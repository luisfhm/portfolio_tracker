import yfinance as yf
import pandas as pd
import time

def fetch_live_prices(df, fx_rates=None):
    """
    Soporta MXN, HKD y USD. Puedes extenderlo fácilmente.
    fx_rates: dict opcional, ej. {"HKD_MXN": 2.60, "USD_MXN": 20.50}
    """
    # --- 1. Obtener tipos de cambio si no se dan ---
    if fx_rates is None:
        fx_rates = {}
        try:
            usd_mxn = yf.Ticker("USDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            usd_mxn = 20.0
        try:
            hkd_mxn = yf.Ticker("HKDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            # Alternativa: HKD/USD + USD/MXN
            try:
                hkd_usd = yf.Ticker("HKDUSD=X").history(period="1d")["Close"].iloc[-1]
                hkd_mxn = hkd_usd * usd_mxn
            except:
                hkd_mxn = 2.60  # fallback razonable
        fx_rates = {"USD_MXN": usd_mxn, "HKD_MXN": hkd_mxn}
        print(f"🔹 Tipos de cambio → USD/MXN: {usd_mxn:.4f}, HKD/MXN: {hkd_mxn:.4f}")

    warnings = []

    for idx, row in df.iterrows():
        ticker = str(row["ticker"])
        live_price = None
        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.fast_info
            live_price = info.get("lastPrice") if info else None
            
            if live_price is None or pd.isna(live_price):
                history = yf_ticker.history(period="5d")
                if not history.empty:
                    live_price = history["Close"].iloc[-1]
            
            if live_price is not None and pd.notna(live_price):
                # --- 2. Detectar moneda por sufijo ---
                if ticker.endswith(".MX"):
                    price_mxn = live_price
                elif ticker.endswith(".HK"):
                    price_mxn = live_price * fx_rates["HKD_MXN"]
                else:
                    # Asumir USD para todo lo demás (AMZN, NIO, VWO, etc.)
                    price_mxn = live_price * fx_rates["USD_MXN"]

                df.at[idx, "precio_mercado"] = round(price_mxn, 4)
                df.at[idx, "valor_mercado"] = round(price_mxn * row["titulos"], 2)
            else:
                warnings.append(f"⚠️ Sin datos para {ticker}")
        except Exception as e:
            warnings.append(f"⚠️ Error en {ticker}: {e}")
        
        time.sleep(0.2)

    # Recálculos
    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct"] = (df["ganancia_live"] / df["costo_total"]) * 100

    return df, warnings