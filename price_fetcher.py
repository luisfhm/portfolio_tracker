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
    Versión reforzada con diagnóstico detallado de errores.
    """
    if token is None:
        token = get_databursatil_token()

    if not token.strip():
        st.warning("Sin token de DataBursatil → usando yfinance para todos los tickers")
        token = ""  # forzamos que no intente API

    # Tipos de cambio (USD/MXN y HKD/MXN)
    if fx_rates is None:
        fx_rates = {}
        try:
            usd_mxn = yf.Ticker("USDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            usd_mxn = 20.0
            st.warning("No se pudo obtener USD/MXN → usando valor por defecto 20.0")
        try:
            hkd_mxn = yf.Ticker("HKDMXN=X").history(period="1d")["Close"].iloc[-1]
        except:
            hkd_mxn = 2.60
            st.warning("No se pudo obtener HKD/MXN → usando valor por defecto 2.60")
        fx_rates = {"USD_MXN": usd_mxn, "HKD_MXN": hkd_mxn}
        st.info(f"Tipos de cambio usados → USD/MXN: {usd_mxn:.4f} | HKD/MXN: {hkd_mxn:.4f}")

    base_url = "https://api.databursatil.com/v2/intradia"

    hoy = datetime.now().date()
    final = hoy.strftime("%Y-%m-%d")
    inicio = (hoy - timedelta(days=days_back)).strftime("%Y-%m-%d")

    warnings = []
    error_details = []          # ← para guardar el motivo real de cada fallo
    fallback_count = 0
    fallback_tickers = []

    st.info(f"Consultando intradía DataBursatil → {inicio} → {final} (intervalo: {intervalo})")

    for idx, row in df.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        if not ticker:
            warnings.append(f"⚠️ Ticker vacío en fila {idx}")
            df.at[idx, "var_pct_dia"] = 0.0
            df.at[idx, "ganancia_dia"] = 0.0
            continue

        # Construcción de URL
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

        # === Intento principal: DataBursatil ===
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            if not isinstance(data, dict) or not data:
                raise ValueError("Respuesta JSON vacía o no es diccionario")

            # Intentamos encontrar la clave del ticker (con y sin *)
            ticker_key = ticker
            ticker_data = data.get(ticker_key) or data.get(ticker.replace("*", ""))
            if not ticker_data or not isinstance(ticker_data, dict):
                raise KeyError(f"No se encontraron datos para '{ticker}' ni '{ticker.replace('*','')}'")

            timestamps = sorted(ticker_data.keys(), reverse=True)
            if not timestamps:
                raise ValueError("No hay timestamps disponibles en la respuesta")

            ultimo_ts = timestamps[0]
            live_price = float(ticker_data[ultimo_ts])

            if len(timestamps) >= 2:
                prev_ts = timestamps[1]
                previous_close = float(ticker_data[prev_ts])

            # Éxito → actualizamos el dataframe
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

            # Feedback visual (puedes comentarlo en producción si es demasiado verbose)
            # st.caption(f"✓ {ticker:12} → DataBursatil OK | ${price_mxn:,.4f} | var {df.at[idx, 'var_pct_dia']:+.2f}%")

        except requests.exceptions.Timeout:
            error_details.append(f"{ticker}: Timeout después de 30 segundos")
            fallback_count += 1
            fallback_tickers.append(ticker)
        except requests.exceptions.HTTPError as http_err:
            status_code = response.status_code if 'response' in locals() else '?'
            error_details.append(f"{ticker}: HTTP {status_code} - {str(http_err)}")
            fallback_count += 1
            fallback_tickers.append(ticker)
        except (KeyError, ValueError, TypeError) as parse_err:
            error_details.append(f"{ticker}: Error de parsing → {type(parse_err).__name__}: {str(parse_err)}")
            fallback_count += 1
            fallback_tickers.append(ticker)
        except Exception as unexpected:
            error_details.append(f"{ticker}: Error inesperado → {type(unexpected).__name__}: {str(unexpected)}")
            fallback_count += 1
            fallback_tickers.append(ticker)

        # === Fallback a yfinance ===
        if not success_databursatil:
            try:
                yf_ticker_str = ticker.replace("*", "").replace(".MX", "")
                yf_t = yf.Ticker(yf_ticker_str)
                info = yf_t.fast_info

                live_price_yf = info.get("lastPrice") or info.get("currentPrice")
                prev_close_yf = info.get("previousClose")

                if live_price_yf is None or prev_close_yf is None:
                    hist = yf_t.history(period="5d")
                    if not hist.empty:
                        live_price_yf = hist["Close"].iloc[-1]
                        if len(hist) >= 2:
                            prev_close_yf = hist["Close"].iloc[-2]

                if live_price_yf is not None and pd.notna(live_price_yf):
                    # Ajuste por divisa
                    if ".MX" in ticker or yf_ticker_str in ["CEMEXCPO", "FEMSAUBD"]:  # ajusta según tus tickers
                        price_mxn = live_price_yf
                        prev_mxn = prev_close_yf if prev_close_yf else live_price_yf
                    elif ".HK" in ticker:
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

                    # Feedback
                    st.caption(f"→ {ticker:12} (yfinance fallback) → ${price_mxn:,.4f}")

                else:
                    raise ValueError("No se obtuvo precio válido de yfinance")

            except Exception as yf_err:
                warnings.append(f"⚠️ yfinance también falló para {ticker}: {str(yf_err)}")
                df.at[idx, "precio_mercado"] = 0.0
                df.at[idx, "valor_mercado"] = 0.0
                df.at[idx, "var_pct_dia"] = 0.0
                df.at[idx, "ganancia_dia"] = 0.0

        time.sleep(0.8)  # Rate limiting más conservador

    # === Reporte final ===
    if fallback_count > 0:
        warnings.append(
            f"DataBursatil falló en {fallback_count} de {len(df)} tickers → usaron yfinance"
        )
        if error_details:
            warnings.append("Detalles de los errores en DataBursatil:")
            for detail in error_details:
                warnings.append(f"  • {detail}")

    # Recálculos finales del dataframe
    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct_total"] = (df["ganancia_live"] / df["costo_total"]) * 100

    return df, warnings