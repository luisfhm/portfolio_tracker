import streamlit as st
from data_loader import load_positions
from price_fetcher import fetch_live_prices
from portfolio import resumen_portafolio
from opportunities import detectar_oportunidades
from news_fetcher import fetch_ticker_news_rss, suggest_similar_opportunities
import plotly.express as px
import pandas as pd
import hashlib
import os
from dotenv import load_dotenv  # Para desarrollo local

# Carga variables de entorno locales (solo en desarrollo)
load_dotenv()  # Busca .env en la carpeta actual

# --- Configuración de autenticación ---
def get_real_password():
    """Obtiene la contraseña de secrets (cloud) o .env (local)"""
    # 1. Cloud: Streamlit Secrets
    try:
        secret_pwd = st.secrets.get("REAL_PORTFOLIO_PASSWORD", None)
        if secret_pwd is not None:
            return secret_pwd
    except Exception:
        # En local, st.secrets tira error → lo ignoramos y pasamos a .env
        pass

    # 2. Local: .env
    env_pwd = os.getenv("REAL_PORTFOLIO_PASSWORD", None)
    if env_pwd is not None:
        return env_pwd

    return None

def check_password():
    """Verifica la contraseña contra el valor seguro (no hardcodeado)"""
    real_pwd = get_real_password()

    if real_pwd is None:
        st.error("⚠️ No se encontró REAL_PORTFOLIO_PASSWORD ni en secrets ni en .env")
        st.info("Configura REAL_PORTFOLIO_PASSWORD en Streamlit Secrets o en un archivo .env local.")
        return False

    # Inicializa sesión si no existe
    if "auth_real" not in st.session_state:
        st.session_state.auth_real = False

    if st.session_state.auth_real:
        return True

    # Interfaz de login
    st.sidebar.markdown("### 🔐 Acceso al Portafolio Real")
    input_pwd = st.sidebar.text_input("Contraseña:", type="password", key="real_pwd_input")

    if st.sidebar.button("Entrar al portafolio real"):
        if hashlib.sha256(input_pwd.encode()).hexdigest() == hashlib.sha256(real_pwd.encode()).hexdigest():
            st.session_state.auth_real = True
            st.sidebar.success("✅ Acceso concedido")
            st.rerun()
        else:
            st.sidebar.error("❌ Contraseña incorrecta")

    return False

# Configuración de página
st.set_page_config(page_title="Luis – Tracker Pro", layout="wide")
st.title("📈 Portfolio Tracker Pro – Precios en Vivo")

# Sidebar: selector de modo
st.sidebar.header("Modo de Visualización")
modo = st.sidebar.radio(
    "Seleccionar portafolio",
    options=["Mi Portafolio Real", "Modo Demo (ficticio)"],
    index=1  # por defecto demo → más seguro
)

IS_DEMO = (modo == "Modo Demo (ficticio)")

# Inicializamos df vacío
df = pd.DataFrame()

if IS_DEMO:
    # Watermark visual
    st.markdown(
        """
        <div style="
            position: fixed;
            top: 35%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-30deg);
            font-size: 90px;
            font-weight: bold;
            color: rgba(180, 60, 60, 0.12);
            pointer-events: none;
            z-index: 999;
        ">
            DEMO
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.warning("🔒 Modo DEMO activado – Datos 100% ficticios")
    st.markdown("### Modo DEMO – Portafolio de Ejemplo")
    st.caption("Datos completamente inventados. No representan ninguna posición real.")

    # Carga demo (ajusta el path si es necesario)
    try:
        df = load_positions(path="demo.json")  # o el nombre que uses
    except Exception as e:
        st.error(f"No se pudo cargar demo.json: {e}")
        st.info("Asegúrate de que demo.json exista en la carpeta del proyecto.")

else:
    # Modo REAL
    if check_password():
        st.sidebar.success("✅ Modo REAL activado")

        try:
            df = load_positions()  # carga real (sin path)
            # Aquí puedes agregar fetch_live_prices, etc.
            df, warnings = fetch_live_prices(df)
            # Muestra warnings si existen
            for w in warnings:
                st.warning(w)
        except Exception as e:
            st.error(f"Error al cargar portafolio real: {e}")

        # Botón de logout
        if st.sidebar.button("Cerrar sesión (volver a demo)"):
            st.session_state.auth_real = False
            st.rerun()

    else:
        st.info("🔒 Ingresa la contraseña en la sidebar para ver tu portafolio real.")
        # Opcional: placeholder o mensaje bonito
        st.markdown("---")
        st.caption("El modo demo está disponible sin contraseña.")
    
if df.empty:
    st.error("❌ No se encontraron posiciones en el portafolio. Por favor, añade algunas en 'positions.json'.")
else:
    # --- Fetch precios en vivo ---    
    df, warnings = fetch_live_prices(df)

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
    col_d1.metric("Ganancia del día (Total)", f"${ganancia_dia_total:,.0f}", f"{pct_dia_total:+.2f}%")
    col_d2.metric("México (día)", f"${ganancia_dia_mex:,.0f}")
    col_d3.metric("Global (día)", f"${ganancia_dia_global:,.0f}")
    col_d4.metric("Variación promedio hoy", f"{pct_dia_total:+.2f}%")

    # --- Sidebar: Filtros + Noticias ---
    with st.sidebar:
        st.header("🔧 Filtros y Consultas Rápidas")
        
        search = st.text_input("🔍 Buscar ticker", placeholder="Ej: AMZN o CEMEXCPO")
        
        var_min, var_max = st.slider(
            "Rango de variación diaria %",
            min_value=-50.0,
            max_value=50.0,
            value=(-50.0, 50.0),
            step=1.0
        )
        
        solo_ganancia = st.checkbox("Solo posiciones en ganancia total")
        mercado_filter = st.multiselect("Mercado", ["Global", "México"], default=["Global", "México"])
        
        st.divider()
        
        # --- Sección de Noticias en la sidebar ---
        st.header("📰 Noticias del Ticker")
        
        # Selectbox para elegir ticker (ordenado alfabéticamente)
        ticker_options = sorted(df["ticker"].unique())
        selected_ticker = st.selectbox("Seleccionar ticker para ver noticias", ticker_options)
        
        if selected_ticker:
            st.subheader(f"{selected_ticker}")
            
            # Noticias
            news_list = fetch_ticker_news_rss(selected_ticker, num_news=5)
            
            if news_list and "Error" not in news_list[0].get("title", "") and "No se encontraron" not in news_list[0].get("title", ""):
                for item in news_list:
                    with st.container():
                        st.markdown(f"**{item['title']}**")
                        caption_parts = [item['publisher']]
                        if item.get('published'):
                            caption_parts.append(item['published'])
                        caption_parts.append(f"[Leer →]({item['link']})")
                        st.caption(" • ".join(caption_parts))
                        if item.get('snippet'):
                            st.write(item['snippet'])
                        st.divider()
            else:
                st.info("No hay noticias recientes relevantes para este ticker.")
            
            # Sugerencias similares
            similares = suggest_similar_opportunities(selected_ticker)
            if similares:
                st.markdown("**💡 Alternativas similares:**")
                for sim in similares:
                    st.write(f"- `{sim}`")
                st.caption("Ideas para diversificar (no es consejo de inversión)")
            else:
                st.caption("No hay sugerencias predefinidas para este ticker.")

    # --- Aplicar filtros ---
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

    # --- Resumen rápido del día ---
    st.markdown("### 🔥 Resumen rápido del día")

    top_gan = df.loc[df["var_pct_dia"].idxmax()]
    top_perd = df.loc[df["var_pct_dia"].idxmin()]

    col_b1, col_b2, col_b3 = st.columns(3)
    col_b1.metric("🏆 Mayor ganadora hoy", f"{top_gan['ticker']}", f"{top_gan['var_pct_dia']:+.2f}%")
    col_b2.metric("📉 Mayor perdedora hoy", f"{top_perd['ticker']}", f"{top_perd['var_pct_dia']:+.2f}%")
    col_b3.metric(
        "🌍 Diversificación",
        f"{(df[df['mercado']=='México']['valor_mercado'].sum() / total_valor * 100):.1f}% México"
    )

    # --- Resumen general ---
    resumen_total = resumen_portafolio(df)
    resumen_mex = resumen_portafolio(df[df["mercado"] == "México"])
    resumen_global = resumen_portafolio(df[df["mercado"] == "Global"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Inversión total", f"${resumen_total['total_inversion']:,.0f}")
    col2.metric("Valor actual total", f"${resumen_total['total_valor']:,.0f}", delta=f"${resumen_total['ganancia_total']:,.0f}")
    col3.metric("México", f"${resumen_mex['total_valor']:,.0f}", delta=f"{resumen_mex['ganancia_pct']:.1f}%")
    col4.metric("Global", f"${resumen_global['total_valor']:,.0f}", delta=f"{resumen_global['ganancia_pct']:.1f}%")

    # --- Gráfico de distribución ---
    st.markdown("### Distribución del portafolio")
    fig = px.pie(df, values="valor_mercado", names="ticker", hole=0.4,
                hover_data=["var_pct_dia"], color_discrete_sequence=px.colors.sequential.Plasma)
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

    money_cols = ["costo_promedio", "precio_mercado", "valor_mercado", "ganancia_dia", "ganancia_live"]
    for col in money_cols:
        df_display[col] = df_display[col].map("${:,.2f}".format)

    df_display["var_pct_dia"] = df_display["var_pct_dia"].map("{:+.2f}%".format)
    df_display["var_pct_total"] = df_display["var_pct_total"].map("{:+.2f}%".format)

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