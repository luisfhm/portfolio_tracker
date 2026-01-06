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
    Prioridad: DataBursatil con ticker limpio → fallback yfinance con ticker + sufijo.
    """
    if token is None:
        token = get_databursatil_token()

    if not token.strip():
        st.warning("Sin token válido de DataBursatil → fallback completo a yfinance")

    # Tipos de cambio
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
    error_details = []
    fallback_count = 0
    fallback_tickers = []

    st.info(f"Intradía DataBursatil: {inicio} → {final} ({intervalo})")

    for idx, row in df.iterrows():
        ticker_original = str(row["ticker"]).strip().upper()
        if not ticker_original:
            continue

        # ────────────────────────────────────────────────────────────────
        # 1. Preparar ticker para DataBursatil (limpio, sin .MX/.HK, con * si internacional)
        # ────────────────────────────────────────────────────────────────
        ticker_db = ticker_original
        # Quitar sufijos que DataBursatil no usa
        ticker_db = ticker_db.replace(".MX", "").replace(".HK", "").replace("*", "")
        # Si NO es mexicano (no tenía .MX originalmente), agregar * (estilo AMZN*, AAPL*)
        if not ticker_original.endswith(".MX"):
            ticker_db += "*"

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
            resp = requests.get(url, timeout=30)
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

            st.caption(f"✓ {ticker_original} → DataBursatil ({ticker_db}) OK")

        except Exception as e:
            error_msg = f"{ticker_original}: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                error_msg += f" (HTTP {e.response.status_code})"
            error_details.append(error_msg)
            fallback_count += 1
            fallback_tickers.append(ticker_original)

        # ────────────────────────────────────────────────────────────────
        # 2. Fallback yfinance → usa ticker con sufijo correcto
        # ────────────────────────────────────────────────────────────────
        if not success_db:
            ticker_yf = ticker_original.replace("*", "")  # solo quita *, mantiene .MX / .HK

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

                    st.caption(f"→ {ticker_original} ({ticker_yf}) → yfinance fallback OK")
                else:
                    raise ValueError("Sin precio válido en yfinance")

            except Exception as yf_err:
                warnings.append(f"⚠️ yfinance falló para {ticker_original}: {str(yf_err)}")
                # Deja ceros o valores anteriores

        time.sleep(0.8)

    # Reporte final
    if fallback_count > 0:
        warnings.append(f"DataBursatil falló en {fallback_count}/{len(df)} tickers")
        if error_details:
            warnings.append("Detalles:")
            for d in error_details:
                warnings.append(f"  • {d}")

    # Recálculos
    df["costo_total"] = df["costo_promedio"] * df["titulos"]
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct_total"] = df["ganancia_live"] / df["costo_total"] * 100

    return df, warnings