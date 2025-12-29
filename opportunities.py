def detectar_oportunidades(df):
    """Regresa oportunidades simples basadas en variaciones."""

    ops = []

    for _, row in df.iterrows():
        if row["var_pct_total"] < -20:
            ops.append(f"🔻 {row['ticker']} cae más de 20% desde tu compra. Considera aumentar posición.")
        if row["var_pct_total"] > 30:
            ops.append(f"🟢 {row['ticker']} sube más de 30%. Podrías tomar utilidades parciales.")

    if len(ops) == 0:
        ops.append("No se detectaron señales importantes hoy.")

    return ops
