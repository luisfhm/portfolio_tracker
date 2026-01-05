def detectar_oportunidades(df):
    """
    Detecta oportunidades refinadas usando datos intradía (precios por minuto).
    Asume que df tiene columnas: ticker, var_pct_dia, var_pct_total, precio_mercado,
    y que fetch_live_prices ya cargó datos intradía (puedes pasarlos como extra si necesitas).
    """
    ops = []

    for _, row in df.iterrows():
        ticker = row['ticker']
        var_dia = row.get('var_pct_dia', 0.0)
        var_total = row.get('var_pct_total', 0.0)
        precio_actual = row.get('precio_mercado', 0.0)
        costo_prom = row.get('costo_promedio', 0.0)

        # 1. Caídas fuertes desde compra (oportunidad de promediar o salir)
        if var_total < -25:
            ops.append(f"🔻 {ticker} -{abs(var_total):.1f}% desde tu compra. Considera promediar o revisar fundamentos.")
        elif var_total < -15:
            ops.append(f"🔻 {ticker} -{abs(var_total):.1f}% desde tu compra. Posible oportunidad de acumulación si sigue tendencia.")

        # 2. Ganancias fuertes (tomar utilidades parciales)
        if var_total > 40:
            ops.append(f"🟢 {ticker} +{var_total:.1f}% desde tu compra. Podrías vender parcial (20-30%) para asegurar ganancias.")
        elif var_total > 25:
            ops.append(f"🟢 {ticker} +{var_total:.1f}% desde tu compra. Buen momento para evaluar salida parcial.")

        # 3. Movimiento intradía fuerte (usando var_pct_dia)
        if var_dia > 5:
            ops.append(f"🚀 {ticker} +{var_dia:.1f}% hoy. Momentum alcista intradía → posible continuación o toma de ganancias.")
        elif var_dia < -5:
            ops.append(f"📉 {ticker} -{abs(var_dia):.1f}% hoy. Movimiento bajista intradía → vigila si es sobreventa o cambio de tendencia.")

        # 4. Rebotando tras caída (señal de posible reversión)
        if var_dia > 2 and var_total < -10:
            ops.append(f"📈 {ticker} rebotando +{var_dia:.1f}% hoy tras caída acumulada. Posible señal de reversión.")

        # 5. Consolidación o lateralidad (poca variación intradía)
        if abs(var_dia) < 1:
            ops.append(f"➡️ {ticker} lateral hoy (±{var_dia:.1f}%). Esperando catalizador o ruptura.")

    # Mensaje por defecto si no hay señales fuertes
    if not ops:
        ops.append("No se detectaron oportunidades o movimientos significativos hoy. Todo en rango normal.")

    # Opcional: ordenar por prioridad (más graves primero)
    ops = sorted(ops, key=lambda x: "🔻" in x, reverse=True)  # Caídas al inicio

    return ops