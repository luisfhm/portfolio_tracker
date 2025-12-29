import pandas as pd

def resumen_portafolio(df):
    """Resumen general usando precios live actualizados."""
    total_inversion = df["costo_total"].sum()
    total_valor = df["valor_mercado"].sum()  # Actualizado en price_fetcher
    ganancia_total = df["ganancia_live"].sum()
    ganancia_pct = (ganancia_total / total_inversion) * 100 if total_inversion > 0 else 0.0

    return {
        "total_inversion": total_inversion,
        "total_valor": total_valor,
        "ganancia_total": ganancia_total,
        "ganancia_pct": ganancia_pct
    }

def top_ganadoras(df):
    """Top 5 por mayor rendimiento %."""
    return df.sort_values("var_pct_total", ascending=False).head(5)

def top_perdedoras(df):
    """Top 5 por mayor pérdida %."""
    return df.sort_values("var_pct_total", ascending=True).head(5)