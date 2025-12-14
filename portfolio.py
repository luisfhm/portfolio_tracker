import pandas as pd

def resumen_portafolio(df):
    """Regresa un resumen general del portafolio."""
    total_inversion = df["costo_total"].sum()
    total_valor = df["valor_mercado"].sum()
    ganancia_total = total_valor - total_inversion
    ganancia_pct = (ganancia_total / total_inversion) * 100

    return {
        "total_inversion": total_inversion,
        "total_valor": total_valor,
        "ganancia_total": ganancia_total,
        "ganancia_pct": ganancia_pct
    }

def top_ganadoras(df):
    return df.sort_values("ganancia_live", ascending=False).head(5)

def top_perdedoras(df):
    return df.sort_values("ganancia_live").head(5)