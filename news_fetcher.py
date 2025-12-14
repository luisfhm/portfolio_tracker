import yfinance as yf
import streamlit as st

def fetch_ticker_news(ticker, num_news=3):
    """Obtiene noticias seguras para un ticker, manejando cambios en yfinance."""
    try:
        yf_ticker = yf.Ticker(ticker)
        raw_news = yf_ticker.news
        news_list = []
        
        for item in raw_news[:num_news]:
            # Estructura común actual: dict con 'title', 'publisher', 'link', 'published' o similar
            title = item.get('title', 'Sin título')
            publisher = item.get('publisher', 'Fuente desconocida')
            link = item.get('link', '#')
            # Algunos tienen 'content' o no summary
            snippet = item.get('summary', item.get('content', ''))[:200]
            if snippet:
                snippet += "..."
            
            news_list.append({
                'title': title,
                'publisher': publisher,
                'link': link,
                'snippet': snippet
            })
        
        return news_list
    except Exception as e:
        return [{'title': 'Error cargando noticias', 'publisher': str(e), 'link': '#', 'snippet': ''}]

def suggest_similar_opportunities(ticker):
    """Mapa simple de alternativas similares (expándelo con tus preferencias)."""
    base_ticker = ticker.split('.')[0]  # Quita .MX o .HK
    similares = {
        "AMZN": ["MSFT", "GOOGL", "AAPL"],
        "NIO": ["TSLA", "LI", "XPEV"],
        "1211": ["TSLA", "NIO", "LI"],  # BYD similares EVs
        "CEMEXCPO": ["GCC.MX", "GMEXICOB.MX"],
        "FUNO11": ["FIBRAMQ.MX", "TERRA13.MX", "FMTY14.MX"],
        "KOFUBL": ["KO", "PEP", "FMX.MX"],
        "NAFTRACISHRS": ["MEXTRACISHRS.MX", "SPY"],  # Benchmarks
        # Agrega más según tu portafolio
    }
    return similares.get(base_ticker, [])