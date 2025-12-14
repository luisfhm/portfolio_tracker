import streamlit as st
from data_loader import load_positions
from price_fetcher import fetch_live_prices
from portfolio import resumen_portafolio, top_ganadoras, top_perdedoras
from opportunities import detectar_oportunidades

st.set_page_config(page_title="Luis – Tracker en Vivo", layout="wide")
st.title("📈 Tracker de Portafolio (Precios en Vivo)")

df = load_positions()
df["costo_total"] = df["costo_promedio"] * df["titulos"]  # Asegurar columna

st.write("🔄 Actualizando precios desde Yahoo Finance...")
df = fetch_live_prices(df)
st.success("✅ Precios actualizados")

# Resumen general
resumen = resumen_portafolio(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Inversión total", f"${resumen['total_inversion']:,.2f}")
col2.metric("Valor actual", f"${resumen['total_valor']:,.2f}", 
            delta=f"${resumen['ganancia_total']:,.2f}")
col3.metric("Ganancia total", f"${resumen['ganancia_total']:,.2f}")
col4.metric("Rendimiento %", f"{resumen['ganancia_pct']:.2f}%")

# Tabla de posiciones
st.header("Posiciones detalladas")
df_display = df[["ticker", "titulos", "costo_promedio", "precio_mercado", 
                 "valor_mercado", "costo_total", "ganancia_live", "var_pct"]].copy()

money_cols = ["costo_promedio", "precio_mercado", "valor_mercado", "costo_total", "ganancia_live"]
for col in money_cols:
    df_display[col] = df_display[col].map("${:,.2f}".format)

df_display["var_pct"] = df_display["var_pct"].map("{:.2f}%".format)

st.dataframe(df_display, use_container_width=True)

# Top performers
col_g, col_p = st.columns(2)
with col_g:
    st.subheader("🏆 Top 5 Ganadoras")
    top_g = top_ganadoras(df).head(5)
    st.dataframe(top_g[["ticker", "var_pct", "ganancia_live"]])

with col_p:
    st.subheader("📉 Top 5 Perdedoras")
    top_p = top_perdedoras(df).head(5)
    st.dataframe(top_p[["ticker", "var_pct", "ganancia_live"]])

# Oportunidades
st.header("🔍 Oportunidades detectadas")
ops = detectar_oportunidades(df)
for o in ops:
    st.write(o)