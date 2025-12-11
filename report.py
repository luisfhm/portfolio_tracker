import streamlit as st
from data_loader import load_positions
from price_fetcher import fetch_live_prices
from portfolio import resumen_portafolio
from opportunities import detectar_oportunidades

st.set_page_config(page_title="Luis – Tracker en Vivo", layout="wide")

st.title("📈 Tracker de Portafolio (Con precios en vivo)")

df = load_positions()

st.write("🔄 Actualizando precios en Yahoo Finance...")
df = fetch_live_prices(df)

st.success("Precios actualizados correctamente")

# ---- Panel general ----
resumen = {
    "total_inversion": df["costo_total"].sum(),
    "total_valor": df["valor_mercado"].sum(),
    "ganancia_total": df["ganancia_live"].sum(),
    "ganancia_pct": (df["ganancia_live"].sum() / df["costo_total"].sum()) * 100,
}

col1, col2, col3, col4 = st.columns(4)

col1.metric("Inversión total", f"${resumen['total_inversion']:,.2f}")
col2.metric("Valor actual", f"${resumen['total_valor']:,.2f}")
col3.metric("Ganancia (live)", f"${resumen['ganancia_total']:,.2f}")
col4.metric("Variación % (live)", f"{resumen['ganancia_pct']:.2f}%")

# ---- Tabla actualizada ----
st.header("Posiciones actualizadas")
# ---- Formatear columnas numéricas para visualización ----
df_display = df.copy()

cols_money = [
    "costo_promedio",
    "precio_mercado",
    "valor_mercado",
    "costo_total",
    "ganancia_live"
]

for c in cols_money:
    df_display[c] = df_display[c].apply(lambda x: f"${x:,.2f}")

# Porcentajes
if "var_pct" in df_display.columns:
    df_display["var_pct"] = df_display["var_pct"].apply(
        lambda x: f"{x:.2f}%"
    )

st.dataframe(df_display)

# ---- Oportunidades ----
st.header("🔍 Oportunidades detectadas con precio actual")
ops = detectar_oportunidades(df)

for o in ops:
    st.write(o)
