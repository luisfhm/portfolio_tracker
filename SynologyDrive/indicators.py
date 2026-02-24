import pandas as pd

def detect_opportunities(price_data):

    opportunities = []
    today = price_data.iloc[-1]
    prev = price_data.iloc[-2]
    ma20 = price_data.tail(20).mean()

    returns = (today / prev - 1) * 100

    for ticker in price_data.columns:

        # Caída fuerte
        if returns[ticker] < -3:
            opportunities.append(f"{ticker}: caída fuerte ({returns[ticker]:.2f}%)")

        # Precio bajo relativo
        if today[ticker] < ma20[ticker]:
            opportunities.append(f"{ticker}: debajo de MA20")

    return opportunities
