import yfinance as yf
import pandas as pd

def fetch_live_prices(df):
    """Descarga precios actuales usando Yahoo Finance y actualiza el DataFrame."""
    precios_actualizados = []

    for _, row in df.iterrows():
        ticker = row["ticker"]

        data = yf.Ticker(ticker).history(period="1d")

    # Re-cálculos
    df["ganancia_live"] = df["valor_mercado"] - df["costo_total"]
    df["var_pct"] = (df["ganancia_live"] / df["costo_total"]) * 100

    return df
