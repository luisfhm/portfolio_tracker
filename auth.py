"""
Autenticación con Supabase para el tracker
"""
import streamlit as st
from supabase import create_client

# Configuración Supabase
SUPABASE_URL = "https://daejqnsqdxojntogzxtw.supabase.co"
SUPABASE_KEY = "sb_publishable_vu2kZ157VRVQMuyJeoaH9Q_X9tFfejQ"

@st.cache_resource
def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def init_session_state():
    """Inicializa el estado de sesión"""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'portfolio_data' not in st.session_state:
        st.session_state.portfolio_data = None

def login_form():
    """Muestra el formulario de login"""
    st.title("🔐 Portfolio Tracker")
    
    # Opción de Demo
    st.info("👀 **¿Quieres probar primero?**")
    if st.button("Ver Modo Demo", key="btn_demo"):
        # Guardar estado demo y continuar sin login
        st.session_state.demo_mode = True
        st.rerun()
    
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Iniciar sesión", "Registrarse"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_password")
        
        if st.button("Entrar", key="btn_login"):
            try:
                supabase = get_supabase()
                response = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password
                })
                st.session_state.logged_in = True
                st.session_state.user = response.user
                st.session_state.access_token = response.session.access_token  # Guardar token
                st.session_state.demo_mode = False  # Clear demo mode
                # Cargar portfolio del usuario
                load_user_portfolio()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    
    with tab2:
        email = st.text_input("Email", key="signup_email")
        password = st.text_input("Contraseña", type="password", key="signup_password")
        confirm = st.text_input("Confirmar contraseña", type="password")
        
        if st.button("Registrarse", key="btn_signup"):
            if password != confirm:
                st.error("Las contraseñas no coinciden")
            else:
                try:
                    supabase = get_supabase()
                    response = supabase.auth.sign_up({
                        "email": email,
                        "password": password
                    })
                    st.success("¡Registrado! Revisa tu email para confirmar.")
                except Exception as e:
                    st.error(f"Error: {e}")

def logout():
    """Cierra sesión"""
    supabase = get_supabase()
    supabase.auth.sign_out()
    st.session_state.logged_in = False
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.portfolio_data = None
    st.rerun()

def load_user_portfolio():
    """Carga el portfolio del usuario desde Supabase"""
    try:
        supabase = get_supabase()
        user_id = st.session_state.user.id
        
        # Buscar portfolio del usuario
        response = supabase.table('portfolios').select('*').eq('user_id', user_id).execute()
        
        if response.data:
            st.session_state.portfolio_data = response.data[0]
        else:
            # Crear portfolio vacío para nuevo usuario
            st.session_state.portfolio_data = None
    except Exception as e:
        print(f"Error cargando portfolio: {e}")
        st.session_state.portfolio_data = None

def save_user_portfolio(portfolio_json):
    """Guarda el portfolio del usuario en Supabase"""
    try:
        supabase = get_supabase()
        user_id = st.session_state.user.id
        
        # Actualizar o insertar
        existing = supabase.table('portfolios').select('id').eq('user_id', user_id).execute()
        
        if existing.data:
            # Update
            supabase.table('portfolios').update({
                'data': portfolio_json,
                'updated_at': 'now()'
            }).eq('user_id', user_id).execute()
        else:
            # Insert
            supabase.table('portfolios').insert({
                'user_id': user_id,
                'data': portfolio_json
            }).execute()
    except Exception as e:
        print(f"Error guardando portfolio: {e}")

def show_demo_banner():
    """Muestra banner de modo demo"""
    st.info("👀 **Modo Demo** - Regístrate para ver tu portafolio real")

def require_auth():
    """Muestra demo si no hay login, o portfolio si hay login"""
    init_session_state()
    
    # Banner según estado
    if not st.session_state.logged_in:
        show_demo_banner()
    
    # Mostrar usuario y logout si está logueado
    if st.session_state.logged_in:
        col1, col2 = st.columns([6, 1])
        with col1:
            st.write(f"👤 {st.session_state.user.email}")
        with col2:
            st.button("Salir", on_click=logout)
    
    return st.session_state.logged_in

def is_logged_in():
    """Retorna True si hay usuario logueado"""
    init_session_state()
    return st.session_state.logged_in

def get_user_id():
    """Retorna el ID del usuario actual"""
    if st.session_state.logged_in:
        return st.session_state.user.id
    return None
