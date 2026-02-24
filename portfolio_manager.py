"""
Gestión de portafolio para el usuario
"""
import streamlit as st
import json
import os
from data_loader import save_user_portfolio_to_supabase, get_logged_user_id

def load_portfolio_dict():
    """Carga el portafolio como dict (para el gestor)"""
    from data_loader import get_logged_user_id, load_user_portfolio_from_supabase
    import json
    import os
    
    user_id = get_logged_user_id()
    print(f"load_portfolio_dict: user_id = {user_id}")
    
    if user_id:
        # Cargar desde Supabase - NO caer al local
        portfolio = load_user_portfolio_from_supabase(user_id)
        print(f"load_portfolio_dict: portfolio from Supabase = {portfolio}")
        if portfolio:
            return portfolio
        # Usuario sin portafolio - empezar vacío
        return {"global": [], "mexico": [], "ultima_actualizacion": ""}
    
    # Solo para modo demo sin login
    local_path = "demo.json"
    if os.path.exists(local_path):
        with open(local_path, 'r') as f:
            return json.load(f)
    
    return {"global": [], "mexico": [], "ultima_actualizacion": ""}

def show_portfolio_manager():
    """Muestra el gestor de portafolio"""
    st.markdown("---")
    st.subheader("💼 Gestionar Portafolio")
    
    # Cargar portafolio como dict
    portfolio = load_portfolio_dict()
    
    # Opción importar
    with st.expander("📤 Importar portafolio desde JSON"):
        uploaded_file = st.file_uploader("Selecciona archivo JSON", type=['json'], key="import_file")
        if uploaded_file:
            if st.button("📥 Importar", key="btn_import"):
                try:
                    imported_data = json.load(uploaded_file)
                    print(f"Import: loaded data = {imported_data}")
                    # Verificar estructura
                    if 'global' in imported_data or 'mexico' in imported_data:
                        portfolio = imported_data
                        # Guardar en Supabase
                        user_id = get_logged_user_id()
                        print(f"Import: user_id = {user_id}")
                        if user_id:
                            success = save_user_portfolio_to_supabase(user_id, portfolio)
                            print(f"Import: save success = {success}")
                            if success:
                                st.success(f"✅ Importado y guardado! ({len(portfolio.get('global', []))} global, {len(portfolio.get('mexico', []))} México)")
                                st.rerun()
                            else:
                                st.error("❌ Error al guardar en Supabase")
                        else:
                            st.error("❌ No hay usuario logueado")
                    else:
                        st.error("❌ Formato inválido. Debe tener 'global' y/o 'mexico'")
                except Exception as e:
                    st.error(f"Error: {e}")
                    print(f"Import error: {e}")
    
    # Tabs para cada tipo
    tab_global, tab_mexico = st.tabs(["🌎 Global", "🇲🇽 México"])
    
    with tab_global:
        st.markdown("**ETF's y acciones globales (USD)**")
        show_asset_list(portfolio.get('global', []), 'global', portfolio)
    
    with tab_mexico:
        st.markdown("**Acciones BMV (MXN)**")
        show_asset_list(portfolio.get('mexico', []), 'mexico', portfolio)
    
    # Botón guardar
    if st.button("💾 Guardar cambios"):
        user_id = get_logged_user_id()
        print(f"Save button clicked, user_id = {user_id}")
        if user_id:
            success = save_user_portfolio_to_supabase(user_id, portfolio)
            if success:
                st.success("✅ Portafolio guardado en la nube!")
            else:
                st.error("❌ Error al guardar")
        else:
            st.error("❌ No se detectó usuario, guardando local...")
            with open('positions.json', 'w') as f:
                json.dump(portfolio, f, indent=2)
            st.warning("⚠️ Guardado localmente (no en la nube)")

def show_asset_list(assets, tipo, portfolio):
    """Muestra lista de activos con opciones de editar"""
    
    # Mostrar activos actuales
    if assets:
        st.write("**Actuales:**")
    else:
        st.info("No hay activos. Agrega uno abajo.")
        
    for i, asset in enumerate(assets):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
            with col1:
                st.write(f"📌 {asset.get('ticker', '')}")
            with col2:
                new_titulos = st.number_input(f"Títulos {i}", value=asset.get('titulos', 0), key=f"tit_{tipo}_{i}")
                asset['titulos'] = new_titulos
            with col3:
                new_costo = st.number_input(f"Costo prom {i}", value=asset.get('costo_promedio', 0), key=f"cost_{tipo}_{i}")
                asset['costo_promedio'] = new_costo
            with col4:
                new_precio = st.number_input(f"Precio {i}", value=asset.get('precio_mercado', 0), key=f"prec_{tipo}_{i}")
                asset['precio_mercado'] = new_precio
            with col5:
                if st.button("🗑️", key=f"del_{tipo}_{i}"):
                    assets.pop(i)
                    st.rerun()
    
    # Agregar nuevo
    st.write("**➕ Agregar nuevo:**")
    col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
    with col1:
        new_ticker = st.text_input("Ticker", placeholder="AMZN", key=f"new_ticker_{tipo}")
    with col2:
        new_titulos = st.number_input("Títulos", min_value=0, value=0, key=f"new_tit_{tipo}")
    with col3:
        new_costo = st.number_input("Costo promedio", min_value=0.0, value=0.0, key=f"new_cost_{tipo}")
    with col4:
        new_precio = st.number_input("Precio actual", min_value=0.0, value=0.0, key=f"new_prec_{tipo}")
    
    if new_ticker and new_titulos > 0:
        if st.button(f"➕ Agregar {new_ticker}", key=f"add_{tipo}"):
            assets.append({
                "ticker": new_ticker,
                "titulos": new_titulos,
                "costo_promedio": new_costo,
                "precio_mercado": new_precio,
                "valor_mercado": new_titulos * new_precio
            })
            portfolio[tipo] = assets
            st.success(f"✅ {new_ticker} agregado!")
            st.rerun()
    
    # Actualizar portfolio
    portfolio[tipo] = assets
