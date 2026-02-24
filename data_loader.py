"""
Carga posiciones del portafolio desde archivo local o Supabase
"""
import json
import os
import pandas as pd
from supabase import create_client

SUPABASE_URL = "https://daejqnsqdxojntogzxtw.supabase.co"
SUPABASE_KEY = "sb_publishable_vu2kZ157VRVQMuyJeoaH9Q_X9tFfejQ"

def get_supabase():
    """Crea cliente Supabase"""
    return get_supabase_with_session()

def get_supabase_with_session():
    """Crea cliente Supabase con sesión activa desde streamlit"""
    import streamlit as st
    from supabase import create_client
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Obtener token de la sesión de streamlit
    access_token = st.session_state.get('access_token')
    if access_token:
        supabase.auth.set_session(access_token, "")
    
    return supabase

def get_logged_user_id():
    """Obtiene el ID del usuario logueado desde streamlit"""
    try:
        import streamlit as st
        user = st.session_state.get('user')
        print(f"get_logged_user_id: user = {user}, type = {type(user)}")
        
        if user:
            # El objeto user de Supabase tiene atributos, no es dict
            if hasattr(user, 'id'):
                user_id = user.id
                print(f"get_logged_user_id: returning {user_id}")
                return user_id
            # También puede ser dict
            if isinstance(user, dict):
                user_id = user.get('id')
                print(f"get_logged_user_id: returning {user_id}")
                return user_id
    except Exception as e:
        print(f"get_logged_user_id error: {e}")
        import traceback
        traceback.print_exc()
    return None

def load_user_portfolio_from_supabase(user_id):
    """Carga el portafolio del usuario desde Supabase"""
    try:
        supabase = get_supabase()
        response = supabase.table('portfolios').select('data').eq('user_id', user_id).execute()
        
        if response.data and response.data[0].get('data'):
            portfolio = json.loads(response.data[0]['data'])
            # Verificar que tiene estructura válida
            if portfolio and ('global' in portfolio or 'mexico' in portfolio):
                return portfolio
    except Exception as e:
        print(f"Error cargando de Supabase: {e}")
    return None

def get_supabase_with_session():
    """Crea cliente Supabase con sesión activa desde streamlit"""
    import streamlit as st
    from supabase import create_client
    from supabase.lib.client_options import ClientOptions
    
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Obtener token de la sesión de streamlit
    try:
        user = st.session_state.get('user')
        if user and hasattr(user, 'access_token'):
            # Crear cliente con el token de acceso
            supabase = create_client(
                SUPABASE_URL, 
                SUPABASE_KEY,
                options=ClientOptions(
                    auth={
                        "token": user.access_token,
                        "refresh_token": getattr(user, 'refresh_token', None)
                    }
                )
            )
    except Exception as e:
        print(f"Error getting session: {e}")
    
    return supabase

def save_user_portfolio_to_supabase(user_id, data):
    """Guarda el portafolio del usuario en Supabase"""
    if not user_id:
        print("ERROR: No user_id provided to save")
        return False
        
    try:
        # Usar cliente simple sin token (RLS debería permitir)
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        json_data = json.dumps(data)
        
        print(f"Saving portfolio for user: {user_id}")
        
        # Ver si ya existe
        existing = supabase.table('portfolios').select('id').eq('user_id', user_id).execute()
        
        if existing.data:
            print(f"Updating existing portfolio")
            result = supabase.table('portfolios').update({
                'data': json_data,
                'updated_at': 'now()'
            }).eq('user_id', user_id).execute()
        else:
            print(f"Inserting new portfolio")
            result = supabase.table('portfolios').insert({
                'user_id': user_id,
                'data': json_data
            }).execute()
            
        print(f"Save result: {result}")
        return True
    except Exception as e:
        print(f"Error guardando en Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_positions(path=None):
    """
    Carga posiciones como DataFrame:
    1. Si path dado: carga desde archivo (demo.json)
    2. Si usuario logueado: carga desde Supabase
    3. Si no: carga desde positions.json local
    """
    # 1. Si path explícito, usar archivo
    if path is not None:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        # 2. Ver si hay usuario logueado
        user_id = get_logged_user_id()
        
        if user_id:
            # Cargar desde Supabase - NO CAER AL LOCAL
            portfolio = load_user_portfolio_from_supabase(user_id)
            if portfolio:
                data = portfolio
            else:
                # Usuario sin portafolio - empezar vacío
                data = {"global": [], "mexico": [], "ultima_actualizacion": ""}
        else:
            # Solo modo demo sin login
            local_path = "demo.json"
            if os.path.exists(local_path):
                with open(local_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"global": [], "mexico": [], "ultima_actualizacion": ""}
    
    # Convertir a DataFrame para compatibilidad con report.py
    global_df = pd.DataFrame(data.get('global', []))
    mexico_df = pd.DataFrame(data.get('mexico', []))
    
    # Agregar columna de tipo
    global_df['mercado'] = 'Global'
    mexico_df['mercado'] = 'México'
    
    # Combinar
    df = pd.concat([global_df, mexico_df], ignore_index=True)
    
    return df
