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

def get_databursatil_token() -> str:
    """
    Obtiene el token de DataBursatil de forma robusta.
    Prioridades (en orden):
    1. st.secrets["DATABURSATIL_TOKEN"]           → formato directo root
    2. st.secrets["databursatil"]["token"]        → formato sección
    3. os.getenv("DATABURSATIL_TOKEN")            → variable de entorno
    4. os.getenv("DATABURSATIL_TOKEN".lower())    → tolerancia a minúsculas (raro pero pasa)

    Retorna cadena vacía si todo falla.
    Muestra mensajes de diagnóstico en la app (solo si falla o debug activado).
    """
    token_candidates = []

    # 1. Intentos con st.secrets (prioridad en cloud y local con secrets.toml)
    try:
        # Formato directo: DATABURSATIL_TOKEN = "..."
        direct = st.secrets.get("DATABURSATIL_TOKEN")
        if direct and isinstance(direct, str) and direct.strip():
            token_candidates.append(("st.secrets[DATABURSATIL_TOKEN]", direct.strip()))
    except Exception as e:
        token_candidates.append(("st.secrets[DATABURSATIL_TOKEN]", f"Error: {str(e)}"))

    try:
        # Formato sección: [databursatil] token = "..."
        section = st.secrets.get("databursatil", {})
        if isinstance(section, dict):
            section_token = section.get("token")
            if section_token and isinstance(section_token, str) and section_token.strip():
                token_candidates.append(("st.secrets[databursatil][token]", section_token.strip()))
    except Exception as e:
        token_candidates.append(("st.secrets[databursatil]", f"Error: {str(e)}"))

    # 2. Variables de entorno (local con .env o manual)
    env_keys = ["DATABURSATIL_TOKEN", "databursatil_token", "DATABURSATIL_TOKEN".lower()]
    for key in env_keys:
        try:
            value = os.getenv(key)
            if value and value.strip():
                token_candidates.append((f"os.getenv({key})", value.strip()))
        except Exception:
            pass

    # Seleccionar el primer token válido encontrado
    for source, value in token_candidates:
        if isinstance(value, str) and value.strip():
            # Éxito silencioso (o con caption si debug)
            if st.session_state.get("debug_token", False):
                st.caption(f"Token cargado desde: {source} (longitud: {len(value)})")
            return value.strip()

    # Fallo total → diagnóstico visible
    debug_msg = [
        "🚨 No se pudo cargar el token de DataBursatil",
        "Fuentes probadas:"
    ]
    for source, value in token_candidates:
        if "Error" in str(value):
            debug_msg.append(f"  • {source}: {value}")
        else:
            debug_msg.append(f"  • {source}: {'[vacío]' if not value else '[encontrado pero inválido]'}")

    debug_msg.append("\nAcciones recomendadas:")
    debug_msg.append("1. Verifica Secrets en dashboard → DATABURSATIL_TOKEN=tu-token")
    debug_msg.append("2. Haz Reboot app después de guardar")
    debug_msg.append("3. Confirma que no hay espacios ni enters extras")

    st.warning("\n".join(debug_msg))

    return ""

def fetch_live_prices(df, token=None, days_back=7, intervalo="1m", fx_rates=None):
    """
    Actualiza precios con prioridad DataBursatil intradía + fallback a yfinance.
    - URL manual para preservar * literal
    - Parsing anidado por ticker
    - Fallback silencioso a yfinance en fallos comunes
    - Mensaje único de fallback al final
    - Retorna (df actualizado, warnings)
    """
    if token is None:
        token = get_databursatil_token()

    # Inicializar fx_rates si no se pasan
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
        st.info(f"Tipos de cambio → USD/MXN: {usd_mxn:.4f}, HKD/MXN: {hkd_mxn:.4f}")

    base_url = "https://api.databursatil.com/v2/intradia"

    hoy = datetime.now().date()
    final = hoy.strftime("%Y-%m-%d")
    inicio = (hoy - timedelta(days=days_back)).strftime("%Y-%m-%d")

    warnings = []
    fallback_count = 0
    fallback_tickers = []

    st.info(f"Consultando intradía DataBursatil → {inicio} a {final} (intervalo {intervalo})")

    for idx, row in df.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        if not ticker:
            warnings.append(f"⚠️ Ticker vacío en fila {idx}")
            df.at[idx, "var_pct_dia"] = 0.0
            df.at[idx, "ganancia_dia"] = 0.0
            continue

        # URL manual → * literal
        url = (
            f"{base_url}?"
            f"token={token}&"
            f"intervalo={intervalo}&"
            f"inicio={inicio}&"
            f"final={final}&"
            f"emisora_serie={ticker}&"
            f"bolsa=BMV"
        )

        success_databursatil = False
        live_price = None
        previous_close = None

        # === DataBursatil ===
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, dict) or not data:
                raise ValueError("Respuesta vacía")

            ticker_key = ticker
            ticker_data = data.get(ticker_key, {})
            if not ticker_data:
                alt_key = ticker.replace("*", "")
                ticker_data = data.get(alt_key, {})
                if not ticker_data:
                    raise KeyError(f"No se encontró '{ticker}' ni '{alt_key}'")

            timestamps = sorted(ticker_data.keys(), reverse=True)
            if not timestamps:
                raise ValueError("No hay timestamps")

            ultimo_ts = timestamps[0]
            live_price = float(ticker_data[ultimo_ts])

            if len(timestamps) >= 2:
                prev_ts = timestamps[1]
                previous_close = float(ticker_data[prev_ts])

            if pd.notna(live_price):
                success_databursatil = True
                price_mxn = live_price
                df.at[idx, "precio_mercado"] = round(price_mxn, 4)
                df.at[idx, "valor_mercado"] = round(price_mxn * row["titulos"], 2)

                if previous_close is not None and previous_close > 0:
                    var_pct = (price_mxn - previous_close) / previous_close * 100
                    df.at[idx, "var_pct_dia"] = round(var_pct, 2)
                    df.at[idx, "ganancia_dia"] = round((price_mxn - previous_close) * row["titulos"], 2)
                else:
                    df.at[idx, "var_pct_dia"] = 0.0
                    df.at[idx, "ganancia_dia"] = 0.0

                st.write(f"✓ {ticker:12} (DataBursatil) → {ultimo_ts} ${price_mxn:,.4f} | var {df.at[idx, 'var_pct_dia']:+.2f}%")

        except Exception as db_err:
            fallback_count += 1
            fallback_tickers.append(ticker)
            # No agregamos warning aquí → lo mostramos uno solo al final

        # === Fallback yfinance si DataBursatil falló ===
        if not success_databursatil:
            try:
                yf_ticker_str = ticker.replace("*", "").replace(".MX", "")
                yf_t = yf.Ticker(yf_ticker_str)
                info = yf_t.fast_info

                live_price_yf = info.get("lastPrice") or info.get("currentPrice")
                prev_close_yf = info.get("previousClose")

                if live_price_yf is None or prev_close_yf is None:
                    hist = yf_t.history(period="5d")
                    if len(hist) >= 1:
                        live_price_yf = hist["Close"].iloc[-1]
                    if len(hist) >= 2:
                        prev_close_yf = hist["Close"].iloc[-2]

                if live_price_yf is not None and pd.notna(live_price_yf):
                    if yf_ticker_str.endswith(".MX"):
                        price_mxn = live_price_yf
                        prev_mxn = prev_close_yf if prev_close_yf else live_price_yf
                    elif yf_ticker_str.endswith(".HK"):
                        price_mxn = live_price_yf * fx_rates["HKD_MXN"]
                        prev_mxn = prev_close_yf * fx_rates["HKD_MXN"] if prev_close_yf else price_mxn
                    else:
                        price_mxn = live_price_yf * fx_rates["USD_MXN"]
                        prev_mxn = prev_close_yf * fx_rates["USD_MXN"] if prev_close_yf else price_mxn

                    df.at[idx, "precio_mercado"] = round(price_mxn, 4)
                    df.at[idx, "valor_mercado"] = round(price_mxn * row["titulos"], 2)

                    if prev_close_yf and prev_mxn > 0:
                        var_pct = (price_mxn - prev_mxn) / prev_mxn * 100
                        df.at[idx, "var_pct_dia"] = round(var_pct, 2)
                        df.at[idx, "ganancia_dia"] = round((price_mxn - prev_mxn) * row["titulos"], 2)
                    else:
                        df.at[idx, "var_pct_dia"] = 0.0
                        df.at[idx, "ganancia_dia"] = 0.0

                    st.write(f"→ {ticker:12} (yfinance) → ${price_mxn:,.4f} | var {df.at[idx, 'var_pct_dia']:+.2f}%")

                else:
                    raise ValueError("No se obtuvo precio de yfinance")

            except Exception as yf_err:
                warnings.append(f"⚠️ yfinance también falló para {ticker}: {str(yf_err)}")
                df.at[idx, "var_pct_dia"] = 0.0
                df.at[idx, "ganancia_dia"] = 0.0
                df.at[idx, "precio_mercado"] = 0.0
                df.at[idx, "valor_mercado"] = 0.0

        time.sleep(0.6)  # Rate-limit combinado

    # Mensaje único de fallback
    if fallback_count > 0:
        tickers_list = ", ".join(fallback_tickers[:5])
        if len(fallback_tickers) > 5:
            tickers_list += "..."
        warnings.append(
            f"Nota: {fallback_count} posiciones usaron datos de yfinance "
            f"(DataBursatil no disponible o suspendida): {tickers_list}"
        )

    # Recálculos finales
    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct_total"] = (df["ganancia_live"] / df["costo_total"]) * 100

    return df, warnings