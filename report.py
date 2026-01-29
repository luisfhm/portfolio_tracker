import streamlit as st
from data_loader import load_positions
from price_fetcher import fetch_live_prices, get_databursatil_token
from portfolio import resumen_portafolio
from opportunities import detectar_oportunidades
from news_fetcher import fetch_ticker_news_rss, suggest_similar_opportunities
import plotly.express as px
import pandas as pd
import hashlib
import os
import requests
from dotenv import load_dotenv
import pytz


load_dotenv()

# === Estilos CSS personalizados ===
st.markdown("""
<style>
    /* === Títulos y texto general === */
    h1 { 
        font-size: 2.2rem; 
        font-weight: 700; 
        margin-bottom: 1rem; 
    }
    h2 { 
        font-size: 1.6rem; 
        font-weight: 600; 
        margin-top: 2rem; 
        margin-bottom: 1rem; 
    }
    h3 { 
        font-size: 1.3rem; 
        font-weight: 600; 
    }

    /* === Watermark DEMO (solo en modo demo) === */
    .demo-watermark {
        position: fixed;
        top: 35%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-30deg);
        font-size: 90px;
        font-weight: bold;
        color: rgba(180, 60, 60, 0.08);
        pointer-events: none;
        z-index: 999;
    }

    /* === Métricas: mejorar legibilidad === */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
        font-weight: 600;
    }

    /* === Espaciado general === */
    .main .block-container {
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# === Funciones de autenticación (sin cambios) ===
def get_real_password():
    try:
        secret_pwd = st.secrets.get("REAL_PORTFOLIO_PASSWORD", None)
        if secret_pwd is not None:
            return secret_pwd
    except Exception:
        pass
    env_pwd = os.getenv("REAL_PORTFOLIO_PASSWORD", None)
    return env_pwd

def check_password():
    real_pwd = get_real_password()
    if real_pwd is None:
        st.error("⚠️ No se encontró REAL_PORTFOLIO_PASSWORD ni en secrets ni en .env")
        st.info("Configura REAL_PORTFOLIO_PASSWORD en Streamlit Secrets o en un archivo .env local.")
        return False

    if "auth_real" not in st.session_state:
        st.session_state.auth_real = False

    if st.session_state.auth_real:
        return True

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

# === Configuración de página ===
st.set_page_config(page_title="Luis – Tracker Pro", layout="wide")
st.title("📈 Portfolio Tracker Pro – Precios en Vivo")

# Definimos la zona horaria de CDMX una sola vez
CDMX_TZ = pytz.timezone('America/Mexico_City')

# Obtenemos la hora actual en CDMX
hoy = pd.Timestamp.now(tz=CDMX_TZ)

# === Verificación del último cierre real vía API (mejorado) ===

days_back = 0

# Ajuste inicial por fin de semana
if hoy.day_name() in ["Saturday", "Sunday"]:
    if hoy.day_name() == "Saturday":
        days_back = 1
    elif hoy.day_name() == "Sunday":
        days_back = 2
token = get_databursatil_token(debug=st.session_state.get("debug", False))

# Luego continúa con fetch_live_prices(df, token=token, ...)
ticker_prueba = "CEMEXCPO"  # Ticker mexicano común para prueba
if token.strip():
    try:
        base_url = "https://api.databursatil.com/v2/historicos"
        final_prueba = hoy.strftime("%Y-%m-%d")
        inicio_prueba = (hoy - pd.Timedelta(days=10)).strftime("%Y-%m-%d")
        
        url_prueba = f"{base_url}?token={token}&inicio={inicio_prueba}&final={final_prueba}&emisora_serie={ticker_prueba}"
        response = requests.get(url_prueba, timeout=8)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, dict) and data:
                # Las fechas vienen como strings → las convertimos y les ponemos la misma zona horaria que 'hoy'
                fechas_aware = []
                for fecha_str in data.keys():
                    try:
                        # Asumimos que las fechas del API son en formato YYYY-MM-DD
                        dt = pd.Timestamp(fecha_str).tz_localize(CDMX_TZ)
                        fechas_aware.append(dt)
                    except Exception as e:
                        st.warning(f"Fecha inválida en API: {fecha_str} → {e}")
                        continue
                
                if fechas_aware:
                    ultima_fecha = max(fechas_aware)
                    
                    # Ahora ambas son timezone-aware → la resta es segura
                    dias_reales = (hoy - ultima_fecha).days
                    
                    # Si han pasado más días de los esperados → ajustamos days_back
                    if dias_reales > days_back:
                        days_back = dias_reales + 1  # +1 para incluir el día del último cierre
                    
                    # Límite de seguridad (evitar retroceder demasiado)
                    days_back = min(days_back, 15)
                    
                else:
                    st.info("No se encontraron fechas válidas en la respuesta del API")
            else:
                st.warning("La respuesta de la API no es un diccionario válido o está vacía")
                
        else:
            st.warning(f"Error en API: status {response.status_code} - {response.reason}")
            
    except requests.Timeout:
        st.warning("Timeout al consultar la API de Databursatil (8s)")
    except Exception as e:
        st.warning(f"No se pudo verificar último cierre real: {str(e)} → usando days_back base")

# === Cálculo de la fecha del último cierre ===
last_close_date = hoy - pd.Timedelta(days=days_back)
market_close_time = last_close_date.replace(hour=15, minute=0, second=0, microsecond=0)

# Formato de hora solo HH:MM (sin segundos si no es necesario)
last_close = market_close_time.strftime('%H:%M')

# --- Formato en español ---
dias_español = {
    'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
    'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
}
meses_español = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

dia_nombre = dias_español.get(hoy.day_name(), hoy.day_name())
mes_nombre = meses_español.get(hoy.month, "Mes desconocido")
fecha_formateada = f"{dia_nombre}, {hoy.day} de {mes_nombre} de {hoy.year}"

# Mostrar información
st.markdown(
    f"<div style='font-size:1.1rem; color:#555; margin-bottom:1.5rem;'>"
    f"**Hoy es** {fecha_formateada} | "
    f"**Último cierre:** {last_close_date.strftime('%Y-%m-%d')} a las {last_close} hrs"
    f"</div>",
    unsafe_allow_html=True
)

# Opcional: mostrar diagnóstico (puedes quitarlo en producción)
if st.session_state.get("debug", False):
    st.caption(f"days_back calculado = {days_back} | tz de hoy = {hoy.tz}")

# === Selector de modo ===
st.sidebar.header("Modo de Visualización")
modo = st.sidebar.radio(
    "Seleccionar portafolio",
    options=["Mi Portafolio Real", "Modo Demo (ficticio)"],
    index=1
)
IS_DEMO = (modo == "Modo Demo (ficticio)")

if IS_DEMO:
    st.markdown('<div class="demo-watermark">DEMO</div>', unsafe_allow_html=True)
    st.sidebar.warning("🔒 Modo DEMO activado – Datos 100% ficticios")
    st.markdown("### Modo DEMO – Portafolio de Ejemplo")
    st.caption("Datos completamente inventados. No representan ninguna posición real.")
    try:
        df = load_positions(path="demo.json")
    except Exception as e:
        st.error(f"No se pudo cargar demo.json: {e}")
        df = pd.DataFrame()
else:
    if check_password():
        st.sidebar.success("Modo REAL activado")
        try:
            df = load_positions()
        except Exception as e:
            st.error(f"Error al cargar portafolio real: {e}")
            df = pd.DataFrame()
        if st.sidebar.button("Cerrar sesión (volver a demo)"):
            st.session_state.auth_real = False
            st.rerun()
    else:
        st.info("🔒 Ingresa la contraseña en la sidebar para ver tu portafolio real.")
        st.markdown("---")
        st.caption("El modo demo está disponible sin contraseña.")
        df = pd.DataFrame()

if df.empty:
    st.error("❌ No se encontraron posiciones en el portafolio. Por favor, añade algunas en el archivo correspondiente.")
else:
    if not token.strip():
        st.error("❌ Token de DataBursatil no configurado.")
        st.info("Las actualizaciones de precios no funcionarán hasta que configures DATABURSATIL_TOKEN.")
    else:
        if st.button("🔄 Actualizar precios ahora"):
            st.rerun()

        with st.status("Actualizando precios en vivo...", expanded=True) as status:
            st.write("Consultando DataBursatil intradía...")
            try:
                df, warnings = fetch_live_prices(df=df, token=token, days_back=days_back)
                status.update(label="✅ Precios actualizados", state="complete")
                if warnings:
                    st.warning("\n".join(warnings))
                else:
                    st.success("Todo actualizado sin problemas")
            except Exception as e:
                status.update(label=f"❌ Error: {e}", state="error")
                st.info("Mostrando datos sin actualización reciente.")

    # === Clasificación por mercado ===
    df["mercado"] = df["ticker"].apply(lambda x: "México" if x.endswith(".MX") else "Global")

    # === Ganancias del día ===
    st.markdown("### 💰 Ganancias y pérdidas del día")
    total_valor = df["valor_mercado"].sum()
    ganancia_dia_total = df["ganancia_dia"].sum()
    pct_dia_total = (ganancia_dia_total / total_valor * 100) if total_valor > 0 else 0
    ganancia_dia_mex = df[df["mercado"] == "México"]["ganancia_dia"].sum()
    ganancia_dia_global = df[df["mercado"] == "Global"]["ganancia_dia"].sum()

    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.metric("Ganancia del día (Total)", f"${ganancia_dia_total:,.0f}", f"{pct_dia_total:+.2f}%")
    with col_d2:
        st.metric("México (día)", f"${ganancia_dia_mex:,.0f}")
    with col_d3:
        st.metric("Global (día)", f"${ganancia_dia_global:,.0f}")
    with col_d4:
        st.metric("Variación promedio hoy", f"{pct_dia_total:+.2f}%")

    # === Sidebar: Filtros y noticias ===
    with st.sidebar:
        st.header("🔍 Filtros y Consultas")
        search = st.text_input("Buscar ticker", placeholder="Ej: AMZN o CEMEXCPO")
        var_min, var_max = st.slider("Rango de variación diaria %", -50.0, 50.0, (-50.0, 50.0), 1.0)
        solo_ganancia = st.checkbox("Solo posiciones en ganancia total")
        mercado_filter = st.multiselect("Mercado", ["Global", "México"], default=["Global", "México"])
        st.divider()
        
        st.header("📰 Noticias del Ticker")
        ticker_options = sorted(df["ticker"].unique())
        selected_ticker = st.selectbox("Seleccionar ticker", ticker_options)
        if selected_ticker:
            st.subheader(f"{selected_ticker}")
            news_list = fetch_ticker_news_rss(selected_ticker, num_news=5)
            if news_list and "Error" not in news_list[0].get("title", ""):
                for item in news_list:
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
                st.info("No hay noticias recientes relevantes.")
            
            similares = suggest_similar_opportunities(selected_ticker)
            if similares:
                st.markdown("**💡 Alternativas similares:**")
                for sim in similares:
                    st.write(f"- `{sim}`")
                st.caption("Ideas para diversificar (no es consejo de inversión)")

    # === Aplicar filtros ===
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

    # === Resumen rápido ===
    st.markdown("### 📊 Resumen rápido del día")
    top_gan = df.loc[df["var_pct_dia"].idxmax()]
    top_perd = df.loc[df["var_pct_dia"].idxmin()]

    col_b1, col_b2, col_b3 = st.columns(3)
    col_b1.metric("🟢 Mayor ganadora", f"{top_gan['ticker']}", f"{top_gan['var_pct_dia']:+.2f}%")
    col_b2.metric("🔴 Mayor perdedora", f"{top_perd['ticker']}", f"{top_perd['var_pct_dia']:+.2f}%")
    col_b3.metric(
        "🌎 Diversificación",
        f"{(df[df['mercado']=='México']['valor_mercado'].sum() / total_valor * 100):.1f}% México"
    )

    # === Resumen general ===
    st.markdown("### 📈 Resumen general del portafolio")
    resumen_total = resumen_portafolio(df)
    resumen_mex = resumen_portafolio(df[df["mercado"] == "México"])
    resumen_global = resumen_portafolio(df[df["mercado"] == "Global"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Inversión total", f"${resumen_total['total_inversion']:,.0f}")
    col2.metric("Valor actual", f"${resumen_total['total_valor']:,.0f}", f"${resumen_total['ganancia_total']:,.0f}")
    col3.metric("México", f"${resumen_mex['total_valor']:,.0f}", f"{resumen_mex['ganancia_pct']:.1f}%")
    col4.metric("Global", f"${resumen_global['total_valor']:,.0f}", f"{resumen_global['ganancia_pct']:.1f}%")

    # === Gráfico ===
    st.markdown("### 🥧 Distribución del portafolio")
    fig = px.pie(df, values="valor_mercado", names="ticker", hole=0.4,
                 hover_data=["var_pct_dia"], color_discrete_sequence=px.colors.sequential.Plasma)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)

    # === Tabla detallada ===
    st.header(f"📋 Posiciones detalladas ({len(df_filtered)} de {len(df)})")
    
    df_display = df_filtered[[
        "ticker", "mercado", "titulos", "costo_promedio", "precio_mercado",
        "valor_mercado", "ganancia_dia", "var_pct_dia",
        "ganancia_live", "var_pct_total"
    ]].copy()

    def color_ganancia(val):
        if pd.isna(val):
            return ""
        return f"color: {'green' if val >= 0 else 'red'}; font-weight: bold;"

    # Ordenar primero
    df_display = df_display.sort_values("ganancia_dia", ascending=False)

    # Crear styler: aplicar estilo y formato en cadena
    styled_df = (
        df_display.style
        .applymap(color_ganancia, subset=["ganancia_dia", "ganancia_live"])
        .format({
            "costo_promedio": "${:,.2f}",
            "precio_mercado": "${:,.2f}",
            "valor_mercado": "${:,.2f}",
            "ganancia_dia": "${:,.2f}",
            "ganancia_live": "${:,.2f}",
            "var_pct_dia": "{:+.2f}%",
            "var_pct_total": "{:+.2f}%"
        })
    )

    st.dataframe(styled_df, use_container_width=True)    # === Top 5 ===
    st.divider()
    col_g, col_p = st.columns(2)
    with col_g:
        st.subheader("🟢 Top 5 Ganadoras Hoy")
        top5_g = df_filtered.nlargest(5, "var_pct_dia")[["ticker", "var_pct_dia", "ganancia_dia"]]
        top5_g["ganancia_dia"] = top5_g["ganancia_dia"].map("${:,.2f}".format)
        top5_g["var_pct_dia"] = top5_g["var_pct_dia"].map("{:+.2f}%".format)
        st.dataframe(top5_g, use_container_width=True)

    with col_p:
        st.subheader("🔴 Top 5 Perdedoras Hoy")
        top5_p = df_filtered.nsmallest(5, "var_pct_dia")[["ticker", "var_pct_dia", "ganancia_dia"]]
        top5_p["ganancia_dia"] = top5_p["ganancia_dia"].map("${:,.2f}".format)
        top5_p["var_pct_dia"] = top5_p["var_pct_dia"].map("{:+.2f}%".format)
        st.dataframe(top5_p, use_container_width=True)

    # === Oportunidades ===
    st.divider()
    st.header("🎯 Oportunidades detectadas")
    ops = detectar_oportunidades(df_filtered)
    for op in ops:
        if "🔻" in op or "📉" in op:
            st.error(f"⚠️ {op}")
        elif "🟢" in op or "🚀" in op:
            st.success(f"✅ {op}")
        elif "📈" in op:
            st.info(f"📊 {op}")
        else:
            st.write(op)