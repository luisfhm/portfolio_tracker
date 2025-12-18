import streamlit as st
from data_loader import load_positions
from price_fetcher import fetch_live_prices
from portfolio import resumen_portafolio, top_ganadoras, top_perdedoras
from opportunities import detectar_oportunidades
from news_fetcher import fetch_ticker_news, suggest_similar_opportunities
import plotly.express as px

st.set_page_config(page_title="Luis – Tracker Pro", layout="wide")
st.title("📈 Portfolio Tracker Pro – Precios en Vivo")

# --- Cargar y actualizar precios ---
df = load_positions()

# Botón manual de refresh
if st.button("🔄 Actualizar precios ahora"):
    st.cache_data.clear()  # Limpia cache para forzar refresh
    st.rerun()

st.write("🔄 Cargando precios en vivo desde Yahoo Finance...")
df, warnings = fetch_live_prices(df)

for warning in warnings:
    st.warning(warning)

if not warnings:
    st.success("✅ Todos los precios actualizados")
else:
    st.success("✅ Precios actualizados (con algunos fallbacks)")

# --- Clasificar por mercado ---
df["mercado"] = df["ticker"].apply(
    lambda x: "México" if x.endswith(".MX") else "Global"
)

# --- Ganancias y pérdidas del día ---
st.markdown("### 💰 Ganancias y pérdidas del día")

total_valor = df["valor_mercado"].sum()
ganancia_dia_total = df["ganancia_dia"].sum()
pct_dia_total = (ganancia_dia_total / total_valor * 100) if total_valor > 0 else 0

ganancia_dia_mex = df[df["mercado"] == "México"]["ganancia_dia"].sum() if not df[df["mercado"] == "México"].empty else 0
ganancia_dia_global = df[df["mercado"] == "Global"]["ganancia_dia"].sum() if not df[df["mercado"] == "Global"].empty else 0

col_d1, col_d2, col_d3, col_d4 = st.columns(4)
col_d1.metric(
    "Ganancia del día (Total)",
    f"${ganancia_dia_total:,.0f}",
    f"{pct_dia_total:+.2f}%"
)
col_d2.metric("México (día)", f"${ganancia_dia_mex:,.0f}")
col_d3.metric("Global (día)", f"${ganancia_dia_global:,.0f}")
col_d4.metric("Variación promedio hoy", f"{pct_dia_total:+.2f}%")

# --- Sidebar con filtros rápidos ---
with st.sidebar:
    st.header("🔧 Filtros y Consultas Rápidas")
    
    search = st.text_input("🔍 Buscar ticker", placeholder="Ej: AMZN o CEMEXCPO")
    
    var_min, var_max = st.slider(
        "Rango de variación diaria %",
        min_value=-50.0,
        max_value=50.0,
        value=(-20.0, 20.0),
        step=1.0
    )
    
    solo_ganancia = st.checkbox("Solo posiciones en ganancia total")
    mercado_filter = st.multiselect("Mercado", ["Global", "México"], default=["Global", "México"])

# Aplicar filtros (usando var_pct_dia para el slider)
df_filtered = df.copy()

if search:
    df_filtered = df_filtered[df_filtered["ticker"].str.contains(search.upper(), case=False)]

df_filtered = df_filtered[
    (df_filtered["var_pct_dia"] >= var_min) &
    (df_filtered["var_pct_dia"] <= var_max) &
    (df_filtered["mercado"].isin(mercado_filter))
]

if solo_ganancia:
    df_filtered = df_filtered[df_filtered["ganancia_live"] > 0]

# --- Badges destacados (rendimiento del día) ---
st.markdown("### 🔥 Resumen rápido del día")

# Tops del día usando var_pct_dia
top_gan = df.loc[df["var_pct_dia"].idxmax()]
top_perd = df.loc[df["var_pct_dia"].idxmin()]

col_b1, col_b2, col_b3 = st.columns(3)
col_b1.metric("🏆 Mayor ganadora hoy", f"{top_gan['ticker']}", f"{top_gan['var_pct_dia']:+.2f}%")
col_b2.metric("📉 Mayor perdedora hoy", f"{top_perd['ticker']}", f"{top_perd['var_pct_dia']:+.2f}%")
col_b3.metric(
    "🌍 Diversificación",
    f"{(df[df['mercado']=='México']['valor_mercado'].sum() / total_valor * 100):.1f}% México"
)

# --- Resumen general + por mercado (rendimiento total) ---
resumen_total = resumen_portafolio(df)
resumen_mex = resumen_portafolio(df[df["mercado"] == "México"])
resumen_global = resumen_portafolio(df[df["mercado"] == "Global"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Inversión total", f"${resumen_total['total_inversion']:,.0f}")
col2.metric(
    "Valor actual total",
    f"${resumen_total['total_valor']:,.0f}",
    delta=f"${resumen_total['ganancia_total']:,.0f}"
)
col3.metric("México", f"${resumen_mex['total_valor']:,.0f}", delta=f"{resumen_mex['ganancia_pct']:.1f}%")
col4.metric("Global", f"${resumen_global['total_valor']:,.0f}", delta=f"{resumen_global['ganancia_pct']:.1f}%")

# --- Gráfico de distribución ---
st.markdown("### 🥧 Distribución del portafolio")
fig = px.pie(
    df,
    values="valor_mercado",
    names="ticker",
    hole=0.4,
    hover_data=["var_pct_dia"],
    color_discrete_sequence=px.colors.sequential.Plasma
)
fig.update_traces(textposition='inside', textinfo='percent+label')
fig.update_layout(hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

# --- Tabla detallada ---
st.header(f"Posiciones detalladas ({len(df_filtered)} de {len(df)})")
df_display = df_filtered[[
    "ticker", "mercado", "titulos", "costo_promedio", "precio_mercado",
    "valor_mercado", "ganancia_dia", "var_pct_dia",
    "ganancia_live", "var_pct_total"
]].copy()

# Formateo monetario
money_cols = ["costo_promedio", "precio_mercado", "valor_mercado", "ganancia_dia", "ganancia_live"]
for col in money_cols:
    df_display[col] = df_display[col].map("${:,.2f}".format)

df_display["var_pct_dia"] = df_display["var_pct_dia"].map("{:+.2f}%".format)
df_display["var_pct_total"] = df_display["var_pct_total"].map("{:+.2f}%".format)

# Ordenar por ganancia del día
df_display = df_display.sort_values("ganancia_dia", ascending=False)

st.dataframe(df_display, use_container_width=True)

# --- Top 5 del día ---
col_g, col_p = st.columns(2)
with col_g:
    st.subheader("🏆 Top 5 Ganadoras Hoy")
    top5_g = df_filtered.nlargest(5, "var_pct_dia")[["ticker", "var_pct_dia", "ganancia_dia"]]
    top5_g["ganancia_dia"] = top5_g["ganancia_dia"].map("${:,.2f}".format)
    top5_g["var_pct_dia"] = top5_g["var_pct_dia"].map("{:+.2f}%".format)
    st.dataframe(top5_g, use_container_width=True)

with col_p:
    st.subheader("📉 Top 5 Perdedoras Hoy")
    top5_p = df_filtered.nsmallest(5, "var_pct_dia")[["ticker", "var_pct_dia", "ganancia_dia"]]
    top5_p["ganancia_dia"] = top5_p["ganancia_dia"].map("${:,.2f}".format)
    top5_p["var_pct_dia"] = top5_p["var_pct_dia"].map("{:+.2f}%".format)
    st.dataframe(top5_p, use_container_width=True)

# --- Oportunidades ---
st.header("🔍 Oportunidades detectadas")
ops = detectar_oportunidades(df_filtered)
for o in ops:
    st.write(o)

# --- Noticias y oportunidades similares ---
st.header("📰 Noticias recientes y sugerencias")

selected_ticker = st.selectbox("Seleccionar ticker para noticias y sugerencias", df_filtered["ticker"].unique())

if selected_ticker:
    row = df_filtered[df_filtered["ticker"] == selected_ticker].iloc[0]
    with st.expander(f"Noticias y sugerencias para {selected_ticker} ({row['mercado']})", expanded=True):
        col_n, col_s = st.columns([2, 1])
        
        with col_n:
            st.subheader("📰 Noticias recientes")
            news_list = fetch_ticker_news(selected_ticker)
            if news_list and news_list[0].get('title') != 'Error cargando noticias':
                for item in news_list:
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['publisher']} • [Ver artículo]({item['link']})")
                    if item.get('snippet'):
                        st.write(item['snippet'])
                    st.divider()
            else:
                st.info("No hay noticias recientes disponibles para este ticker.")
        
        with col_s:
            st.subheader("💡 Oportunidades similares")
            similares = suggest_similar_opportunities(selected_ticker)
            if similares:
                st.write("Activos similares en sector/rendimiento:")
                for sim in similares:
                    st.write(f"- **{sim}**")
                st.caption("Investiga estos para diversificar (no es consejo financiero).")
            else:
                st.info("No hay sugerencias predefinidas aún.")