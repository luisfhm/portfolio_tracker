import yfinance as yf
import pandas as pd
import time

def fetch_live_prices(df, fx_rates=None):
    """
    Actualiza precios en vivo, calcula:
    - var_pct_dia: variación % del día (desde cierre anterior)
    - ganancia_dia: ganancia/pérdida en MXN del día
    - var_pct_total: rendimiento total desde compra (como antes)
    """
    if fx_rates is None:
        fx_rates = {}
        try:
            usd_mxn = yf.Ticker("USDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            usd_mxn = 20.0
        try:
            hkd_mxn = yf.Ticker("HKDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            try:
                hkd_usd = yf.Ticker("HKDUSD=X").history(period="1d")["Close"].iloc[-1]
                hkd_mxn = hkd_usd * usd_mxn
            except:
                hkd_mxn = 2.60
        fx_rates = {"USD_MXN": usd_mxn, "HKD_MXN": hkd_mxn}
        print(f"🔹 Tipos de cambio → USD/MXN: {usd_mxn:.4f}, HKD/MXN: {hkd_mxn:.4f}")

    warnings = []

    for idx, row in df.iterrows():
        ticker = str(row["ticker"])
        live_price = None
        previous_close = None

        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.fast_info

            # Precio actual
            live_price = info.get("lastPrice") or info.get("currentPrice")
            previous_close = info.get("previousClose")

            # Fallback a history si fast_info falla
            if live_price is None or previous_close is None:
                history = yf_ticker.history(period="5d")
                if len(history) >= 2:
                    live_price = history["Close"].iloc[-1]
                    previous_close = history["Close"].iloc[-2]
                elif len(history) == 1:
                    live_price = history["Close"].iloc[-1]
                    previous_close = None  # No hay dato anterior

            if live_price is not None and pd.notna(live_price):
                # Convertir a MXN según moneda
                if ticker.endswith(".MX"):
                    price_mxn = live_price
                elif ticker.endswith(".HK"):
                    price_mxn = live_price * fx_rates["HKD_MXN"]
                else:
                    price_mxn = live_price * fx_rates["USD_MXN"]

                df.at[idx, "precio_mercado"] = round(price_mxn, 4)
                df.at[idx, "valor_mercado"] = round(price_mxn * row["titulos"], 2)

                # === Cálculo variación del día ===
                if previous_close and previous_close > 0:
                    # Precio anterior también convertido a MXN
                    if ticker.endswith(".MX"):
                        prev_mxn = previous_close
                    elif ticker.endswith(".HK"):
                        prev_mxn = previous_close * fx_rates["HKD_MXN"]
                    else:
                        prev_mxn = previous_close * fx_rates["USD_MXN"]

                    var_pct_dia = (price_mxn - prev_mxn) / prev_mxn * 100
                    df.at[idx, "var_pct_dia"] = round(var_pct_dia, 2)
                    df.at[idx, "ganancia_dia"] = round((price_mxn - prev_mxn) * row["titulos"], 2)
                else:
                    df.at[idx, "var_pct_dia"] = 0.0
                    df.at[idx, "ganancia_dia"] = 0.0
            else:
                warnings.append(f"⚠️ Sin datos para {ticker}")
                df.at[idx, "var_pct_dia"] = 0.0
                df.at[idx, "ganancia_dia"] = 0.0

        except Exception as e:
            warnings.append(f"⚠️ Error en {ticker}: {e}")
            df.at[idx, "var_pct_dia"] = 0.0
            df.at[idx, "ganancia_dia"] = 0.0

        time.sleep(0.2)

    # === Recálculos finales (como antes) ===
    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct_total"] = (df["ganancia_live"] / df["costo_total"]) * 100  # Rendimiento total

    return df, warnings