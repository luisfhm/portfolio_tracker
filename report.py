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

# --- Cálculo de ganancias/pérdidas del día ---
st.markdown("### 💰 Ganancias y pérdidas del día")

# Ganancia del día = valor_mercado_actual * (var_pct / 100)
df["ganancia_dia"] = df["valor_mercado"] * (df["var_pct"] / 100)

# Resúmenes del día
ganancia_dia_total = df["ganancia_dia"].sum()
ganancia_dia_mex = df[df["mercado"] == "México"]["ganancia_dia"].sum()
ganancia_dia_global = df[df["mercado"] == "Global"]["ganancia_dia"].sum()

# Porcentaje del día sobre el valor total del portafolio
pct_dia_total = (ganancia_dia_total / df["valor_mercado"].sum()) * 100 if df["valor_mercado"].sum() > 0 else 0

# Métricas bonitas en columnas
col_d1, col_d2, col_d3, col_d4 = st.columns(4)

col_d1.metric(
    label="Ganancia del día (Total)",
    value=f"${ganancia_dia_total:,.0f}",
    delta=f"{pct_dia_total:+.2f}%"
)

col_d2.metric(
    label="México (día)",
    value=f"${ganancia_dia_mex:,.0f}",
    delta=None
)

col_d3.metric(
    label="Global (día)",
    value=f"${ganancia_dia_global:,.0f}",
    delta=None
)

# Variación promedio ponderada del portafolio hoy
var_ponderada = pct_dia_total
col_d4.metric(
    label="Variación promedio del portafolio",
    value=f"{var_ponderada:+.2f}%",
    delta=None
)

# --- Clasificar por mercado ---
df["mercado"] = df["ticker"].apply(
    lambda x: "México" if x.endswith(".MX") else "Global"
)

# --- Sidebar con filtros rápidos ---
with st.sidebar:
    st.header("🔧 Filtros y Consultas Rápidas")
    
    search = st.text_input("🔍 Buscar ticker", placeholder="Ej: AMZN o CEMEX")
    
    var_min, var_max = st.slider(
        "Rango de variación %",
        min_value=-100.0,
        max_value=100.0,
        value=(-50.0, 50.0),
        step=5.0
    )
    
    solo_ganancia = st.checkbox("Solo posiciones en ganancia")
    mercado_filter = st.multiselect("Mercado", ["Global", "México"], default=["Global", "México"])

# Aplicar filtros
df_filtered = df.copy()

if search:
    df_filtered = df_filtered[df_filtered["ticker"].str.contains(search.upper(), case=False)]

df_filtered = df_filtered[
    (df_filtered["var_pct"] >= var_min) &
    (df_filtered["var_pct"] <= var_max) &
    (df_filtered["mercado"].isin(mercado_filter))
]

if solo_ganancia:
    df_filtered = df_filtered[df_filtered["ganancia_live"] > 0]

# --- Badges destacados ---
st.markdown("### 🔥 Resumen rápido del día")
col_b1, col_b2, col_b3 = st.columns(3)

top_gan = top_ganadoras(df).iloc[0]
top_perd = top_perdedoras(df).iloc[0]

col_b1.metric("🏆 Mayor ganadora", f"{top_gan['ticker']}", f"{top_gan['var_pct']:.1f}%")
col_b2.metric("📉 Mayor perdedora", f"{top_perd['ticker']}", f"{top_perd['var_pct']:.1f}%")
col_b3.metric("🌍 Diversificación", f"{(df[df['mercado']=='México']['valor_mercado'].sum() / df['valor_mercado'].sum()*100):.1f}% México")

# --- Resumen general + por mercado ---
resumen_total = resumen_portafolio(df)
resumen_mex = resumen_portafolio(df[df["mercado"] == "México"])
resumen_global = resumen_portafolio(df[df["mercado"] == "Global"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Inversión total", f"${resumen_total['total_inversion']:,.0f}")
col2.metric("Valor actual total", f"${resumen_total['total_valor']:,.0f}",
            delta=f"${resumen_total['ganancia_total']:,.0f}")
col3.metric("México", f"${resumen_mex['total_valor']:,.0f}", delta=f"{(resumen_mex['ganancia_pct']):.1f}%")
col4.metric("Global", f"${resumen_global['total_valor']:,.0f}", delta=f"{(resumen_global['ganancia_pct']):.1f}%")

# --- Gráfico de distribución ---
st.markdown("### 🥧 Distribución del portafolio")
fig = px.pie(
    df,
    values="valor_mercado",
    names="ticker",
    hole=0.4,
    hover_data=["var_pct"],
    color_discrete_sequence=px.colors.sequential.Plasma
)
fig.update_traces(textposition='inside', textinfo='percent+label')
st.plotly_chart(fig, use_container_width=True)

# --- Tabla filtrada ---
st.header(f"Posiciones detalladas ({len(df_filtered)} de {len(df)})")
df_display = df_filtered[["ticker", "mercado", "titulos", "costo_promedio", "precio_mercado",
                          "valor_mercado", "costo_total", "ganancia_live", "var_pct"]].copy()

money_cols = ["costo_promedio", "precio_mercado", "valor_mercado", "costo_total", "ganancia_live"]
for col in money_cols:
    df_display[col] = df_display[col].map("${:,.2f}".format)

df_display["var_pct"] = df_display["var_pct"].map("{:.2f}%".format)
st.dataframe(df_display, width="stretch")

# --- Tops ---
col_g, col_p = st.columns(2)
with col_g:
    st.subheader("🏆 Top 5 Ganadoras")
    top5_g = top_ganadoras(df_filtered)[["ticker", "var_pct", "ganancia_live"]]
    top5_g["ganancia_live"] = top5_g["ganancia_live"].map("${:,.2f}".format)
    top5_g["var_pct"] = top5_g["var_pct"].map("{:.1f}%".format)
    st.dataframe(top5_g, use_container_width=True)

with col_p:
    st.subheader("📉 Top 5 Perdedoras")
    top5_p = top_perdedoras(df_filtered)[["ticker", "var_pct", "ganancia_live"]]
    top5_p["ganancia_live"] = top5_p["ganancia_live"].map("${:,.2f}".format)
    top5_p["var_pct"] = top5_p["var_pct"].map("{:.1f}%".format)
    st.dataframe(top5_p, use_container_width=True)

# --- Oportunidades ---
st.header("🔍 Oportunidades detectadas")
ops = detectar_oportunidades(df_filtered)
for o in ops:
    st.write(o)

# --- Noticias y oportunidades similares ---
st.header("📰 Noticias recientes y sugerencias")

# Selector para ver noticias de un ticker específico (para no sobrecargar con todos)
selected_ticker = st.selectbox("Seleccionar ticker para noticias y sugerencias", df_filtered["ticker"].unique())

if selected_ticker:
    row = df_filtered[df_filtered["ticker"] == selected_ticker].iloc[0]
    with st.expander(f"Noticias y sugerencias para {selected_ticker} ({row['mercado']})", expanded=True):
        col_n, col_s = st.columns([2, 1])
        
        with col_n:
            st.subheader("📰 Noticias recientes")
            news_list = fetch_ticker_news(selected_ticker)
            if news_list and news_list[0]['title'] != 'Error cargando noticias':
                for item in news_list:
                    st.markdown(f"**{item['title']}**")
                    st.caption(f"{item['publisher']} • [Ver artículo]({item['link']})")
                    if item['snippet']:
                        st.write(item['snippet'])
                    st.divider()
            else:
                st.info("No hay noticias recientes disponibles para este ticker (común en fines de semana o tickers menores).")
        
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