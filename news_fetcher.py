import streamlit as st
import feedparser
from datetime import datetime

def fetch_ticker_news_rss(ticker, num_news=5):
    """
    Obtiene noticias vía RSS de Google News (gratuito, sin API key).
    """
    # Mapeo ticker → nombre empresa para búsquedas más precisas
    company_names = {
        "AMZN": "Amazon",
        "AAPL": "Apple",
        "MSFT": "Microsoft",
        "TSLA": "Tesla",
        "NIO": "NIO",
        "1211.HK": "BYD",
        "CEMEXCPO.MX": "Cemex",
        "FUNO11.MX": "Fibra Uno",
        "KOFUBL.MX": "Coca-Cola Femsa",
        # Añade más...
    }
    
    query = company_names.get(ticker, ticker)
    url = f"https://news.google.com/rss/search?q={query}+acciones+OR+bolsa&hl=es&gl=ES&ceid=ES:es"
    
    try:
        feed = feedparser.parse(url)
        entries = feed.entries[:num_news]
        
        news_list = []
        for entry in entries:
            # Fecha aproximada
            published = entry.get("published", "")
            if published:
                try:
                    published = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z").strftime("%d/%m/%Y")
                except:
                    published = ""
            
            news_list.append({
                "title": entry.title,
                "publisher": entry.source.title if hasattr(entry, "source") else "Google News",
                "link": entry.link,
                "snippet": entry.summary[:200] + "..." if entry.get("summary") else "",
                "published": published
            })
        
        if not news_list:
            return [{"title": "No se encontraron noticias recientes", "publisher": "", "link": "#", "snippet": ""}]
        
        return news_list
        
    except Exception as e:
        return [{"title": "Error al cargar noticias", "publisher": str(e), "link": "#", "snippet": ""}]
    
def suggest_similar_opportunities(ticker):
    """Tu función original de sugerencias (mantenla o amplíala)"""
    base_ticker = ticker.split('.')[0]
    similares = {
        "AMZN": ["MSFT", "GOOGL", "AAPL"],
        "NIO": ["TSLA", "LI", "XPEV"],
        "1211": ["TSLA", "NIO", "LI"],
        "CEMEXCPO": ["GCC.MX", "GMEXICOB.MX"],
        "FUNO11": ["FIBRAMQ.MX", "TERRA13.MX", "FMTY14.MX"],
        "KOFUBL": ["KO", "PEP", "FMX.MX"],
        "NAFTRACISHRS": ["MEXTRACISHRS.MX", "SPY"],
        # Agrega más...
    }
    return similares.get(base_ticker, [])