import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import time
import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()  # Para .env en desarrollo local

from typing import Optional

def get_databursatil_token(debug: bool = False) -> str:
    """
    Obtiene el token de DataBursatil de forma robusta y compatible con:
    - Local: .streamlit/secrets.toml o .env
    - Cloud: secrets en dashboard de Streamlit

    Prioridades:
    1. st.secrets["DATABURSATIL_TOKEN"]          → formato directo (más común en cloud)
    2. st.secrets["databursatil"]["token"]       → formato sección
    3. os.getenv("DATABURSATIL_TOKEN")           → .env local o manual

    Parámetro debug=True muestra más información en la app.
    """
    token = None
    source = "ninguna"

    # 1. Intentar st.secrets (funciona en cloud y local con secrets.toml)
    try:
        # Formato directo (recomendado)
        token = st.secrets.get("DATABURSATIL_TOKEN")
        if token and isinstance(token, str) and token.strip():
            source = "st.secrets[DATABURSATIL_TOKEN]"
    except Exception:
        pass

    if not token:
        try:
            # Formato sección
            section = st.secrets.get("databursatil", {})
            if isinstance(section, dict):
                token = section.get("token")
                if token and isinstance(token, str) and token.strip():
                    source = "st.secrets[databursatil][token]"
        except Exception:
            pass

    # 2. Fallback a variables de entorno (.env local)
    if not token:
        token = os.getenv("DATABURSATIL_TOKEN", "").strip()
        if token:
            source = "os.getenv(DATABURSATIL_TOKEN)"

    # 3. Último intento: key en minúsculas (raro pero a veces pasa por error de tipeo)
    if not token:
        token = os.getenv("databursatil_token", "").strip()
        if token:
            source = "os.getenv(databursatil_token)"

    # Limpieza final: quitar comillas dobles o simples si vienen incluidas (muy común en secrets.toml)
    if token:
        token = token.strip()
        if token.startswith(('"', "'")) and token.endswith(('"', "'")):
            token = token[1:-1].strip()  # quita comillas de ambos lados

    # Feedback según debug
    if debug:
        if token:
            st.caption(f"[DEBUG] Token cargado desde: {source} | longitud: {len(token)} | primeros 6: {token[:6]}...")
        else:
            st.caption("[DEBUG] No se encontró token en ninguna fuente")

    # Warning suave si no hay token (solo una vez)
    if not token and not debug and "token_warning_shown" not in st.session_state:
        st.session_state.token_warning_shown = True
        st.warning("No se encontró token de DataBursatil. Las consultas intradía usarán yfinance.")

    return token if token else ""


def fetch_live_prices(df, token=None, days_back=7, intervalo="1m", fx_rates=None):
    """
    Prioridad: DataBursatil con ticker limpio → fallback yfinance con ticker + sufijo.
    """
    if token is None:
        token = get_databursatil_token()

    if not token or len(token) < 8:  # chequeo mínimo razonable
        st.warning("Token de DataBursatil no válido o demasiado corto → fallback completo a yfinance")
        token = ""

    # Tipos de cambio (fallback hardcoded si falla yfinance)
    if fx_rates is None:
        fx_rates = {}
        try:
            usd_mxn = yf.Ticker("USDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            usd_mxn = 20.0
        try:
            hkd_mxn = yf.Ticker("HKDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            hkd_mxn = 2.60
        fx_rates = {"USD_MXN": usd_mxn, "HKD_MXN": hkd_mxn}
        st.info(f"USD/MXN: {usd_mxn:.4f} | HKD/MXN: {hkd_mxn:.4f}")

    base_url = "https://api.databursatil.com/v2/intradia"

    hoy = datetime.now().date()
    final = hoy.strftime("%Y-%m-%d")
    inicio_dt = hoy - timedelta(days=days_back)
    inicio = inicio_dt.strftime("%Y-%m-%d")

    if inicio_dt > hoy:
        inicio = final

    warnings = []
    fallback_count = 0
    fallback_tickers = []

    st.info(f"Intradía DataBursatil: {inicio} → {final} ({intervalo})")

    for idx, row in df.iterrows():
        ticker_original = str(row["ticker"]).strip().upper()
        if not ticker_original:
            continue

        # Preparar ticker para DataBursatil (sin .MX/.HK, con * si internacional)
        ticker_db = ticker_original.replace(".MX", "").replace(".HK", "")

        url = (
            f"{base_url}?"
            f"token={token}&"
            f"intervalo={intervalo}&"
            f"inicio={inicio}&"
            f"final={final}&"
            f"emisora_serie={ticker_db}&"
            f"bolsa=BMV"
        )

        success_db = False

        try:
            if not token:
                raise ValueError("Sin token → saltando DataBursatil")

            resp = requests.get(url, timeout=30)
            # Debug clave
            st.caption(f"[DEBUG-DB] Ticker: {ticker_db} | Status: {resp.status_code}")
            if resp.status_code != 200:
                st.caption(f"[DEBUG-DB] Error body: {resp.text[:300]}")  # muestra mensaje de error
            else:
                st.caption(f"[DEBUG-DB] Respuesta OK - Claves principales: {list(resp.json().keys())}")
            
            resp.raise_for_status()
            data = resp.json()

            if not isinstance(data, dict) or not data:
                raise ValueError("Respuesta vacía o inválida")

            # Buscar clave (con y sin *)
            ticker_key = ticker_db
            ticker_data = data.get(ticker_key) or data.get(ticker_db.replace("*", ""))
            if not ticker_data or not isinstance(ticker_data, dict):
                raise KeyError(f"No datos para {ticker_key}")

            ts_sorted = sorted(ticker_data.keys(), reverse=True)
            if not ts_sorted:
                raise ValueError("Sin timestamps")

            last_price = float(ticker_data[ts_sorted[0]])
            prev_price = float(ticker_data[ts_sorted[1]]) if len(ts_sorted) >= 2 else None

            success_db = True
            price_mxn = last_price
            df.at[idx, "precio_mercado"] = round(price_mxn, 4)
            df.at[idx, "valor_mercado"] = round(price_mxn * row["titulos"], 2)

            if prev_price and prev_price > 0:
                var_pct = (price_mxn - prev_price) / prev_price * 100
                df.at[idx, "var_pct_dia"] = round(var_pct, 2)
                df.at[idx, "ganancia_dia"] = round((price_mxn - prev_price) * row["titulos"], 2)
            else:
                df.at[idx, "var_pct_dia"] = 0.0
                df.at[idx, "ganancia_dia"] = 0.0

            st.caption(f"✓ {ticker_original} → DataBursatil ({ticker_db})")

        except Exception as e:
            error_msg = f"{ticker_original}: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" (HTTP {e.response.status_code})"
            fallback_count += 1
            fallback_tickers.append(ticker_original)
            # No imprimimos todos los errores para no saturar, pero se guardan en warnings al final

        # Fallback yfinance
        if not success_db:
            # Intentamos con sufijo .MX por default (puedes ajustar según tu portafolio)
            ticker_yf = ticker_original.replace("*", ".MX")

            try:
                yf_obj = yf.Ticker(ticker_yf)
                info = yf_obj.fast_info

                last_yf = info.get("lastPrice") or info.get("currentPrice")
                prev_yf = info.get("previousClose")

                if last_yf is None:
                    hist = yf_obj.history(period="5d")
                    if not hist.empty:
                        last_yf = hist["Close"].iloc[-1]
                        prev_yf = hist["Close"].iloc[-2] if len(hist) >= 2 else last_yf

                if last_yf is not None and pd.notna(last_yf):
                    if ".MX" in ticker_yf:
                        price_mxn = last_yf
                        prev_mxn = prev_yf if prev_yf else last_yf
                    elif ".HK" in ticker_yf:
                        price_mxn = last_yf * fx_rates["HKD_MXN"]
                        prev_mxn = prev_yf * fx_rates["HKD_MXN"] if prev_yf else price_mxn
                    else:
                        price_mxn = last_yf * fx_rates["USD_MXN"]
                        prev_mxn = prev_yf * fx_rates["USD_MXN"] if prev_yf else price_mxn

                    df.at[idx, "precio_mercado"] = round(price_mxn, 4)
                    df.at[idx, "valor_mercado"] = round(price_mxn * row["titulos"], 2)

                    if prev_yf and prev_mxn > 0:
                        var_pct = (price_mxn - prev_mxn) / prev_mxn * 100
                        df.at[idx, "var_pct_dia"] = round(var_pct, 2)
                        df.at[idx, "ganancia_dia"] = round((price_mxn - prev_mxn) * row["titulos"], 2)

                    st.caption(f"→ {ticker_original} ({ticker_yf}) → yfinance fallback")
                else:
                    raise ValueError("Sin precio válido en yfinance")

            except Exception as yf_err:
                warnings.append(f"⚠️ yfinance falló para {ticker_original}: {str(yf_err)}")

        time.sleep(0.8)  # evita rate limiting

    # Reporte final
    if fallback_count > 0:
        warnings.append(
            f"DataBursatil falló en {fallback_count}/{len(df)} tickers → yfinance usado: {', '.join(fallback_tickers)}"
        )

    # Recálculos globales
    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct_total"] = df["ganancia_live"] / df["costo_total"] * 100

    return df, warnings