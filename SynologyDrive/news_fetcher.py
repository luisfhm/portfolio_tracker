import feedparser
from datetime import datetime
import urllib.parse  # ← ¡importa esto!
import streamlit as st

def fetch_ticker_news_rss(ticker, num_news=5):
    """
    Obtiene noticias vía RSS de Google News usando nombre real de la empresa.
    """
    # Mapeo de tickers → nombre empresa (extiéndelo con tus tickers reales)
    company_map = {
        "AMZN*": "Amazon",
        "AMZN": "Amazon",
        "1211N": "BYD Company",
        "NION": "NIO Inc",
        "NUN": "Nu Holdings",
        "BKCH*": "Global X Blockchain ETF",
        "BOTZ*": "Global X Robotics & Artificial Intelligence ETF",
        "GSG*": "iShares S&P GSCI Commodity Indexed Trust",
        "HERO*": "Global X Video Games & Esports ETF",
        "ICLN*": "iShares Global Clean Energy ETF",
        "SOCL*": "Global X Social Media ETF",
        "CEMEXCPO": "Cemex",
        "ALSEA*": "Alsea",
        "FUNO11": "Fibra Uno",
        "KOFUBL": "Coca-Cola Femsa",
        # Agrega más según tu positions.json
    }

    # Limpieza del ticker
    cleaned_ticker = ticker.replace("*", "").replace(".MX", "").upper()
    
    # Nombre de empresa (fallback al ticker limpio)
    company = company_map.get(cleaned_ticker, cleaned_ticker)

    # Términos de búsqueda
    search_terms = f"{company} acciones OR bolsa OR stock OR news OR earnings"

    # Codificación correcta de la query
    encoded_query = urllib.parse.quote(search_terms)

    # URL final segura
    url = (
        f"https://news.google.com/rss/search?"
        f"q={encoded_query}&"
        f"hl=es-419&"
        f"gl=MX&"
        f"ceid=MX:es-419"
    )

    try:
        feed = feedparser.parse(url)
        entries = feed.entries[:num_news]

        news_list = []
        for entry in entries:
            published = entry.get("published", "")
            if published:
                try:
                    dt = datetime.strptime(published, "%a, %d %b %Y %H:%M:%S %Z")
                    published = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    published = published[:16]

            news_list.append({
                "title": entry.title,
                "publisher": entry.source.title if hasattr(entry, "source") else "Google News",
                "link": entry.link,
                "snippet": entry.summary[:250] + "..." if entry.get("summary") else "",
                "published": published
            })

        if not news_list:
            return [{"title": f"No se encontraron noticias para {company}", 
                     "publisher": "", "link": "#", "snippet": ""}]
        
        return news_list

    except Exception as e:
        st.warning(f"Error cargando noticias para {ticker}: {str(e)}")
        return [{"title": "Error al cargar noticias", 
                 "publisher": str(e), "link": "#", "snippet": ""}]


def suggest_similar_opportunities(ticker):
    """
    Sugerencias similares adaptadas a tickers de positions.json (BMV/originales).
    """
    # Limpieza para matching
    cleaned_ticker = ticker.replace("*", "").replace(".MX", "").upper()

    # Mapeo de sugerencias (basado en tu JSON - extiéndelo)
    similares = {
        "1211N": ["NION", "TSLA", "LI", "XPEV"],  # BYD EV
        "AMZN*": ["MSFT", "GOOGL", "AAPL*", "META"],  # Tech giants
        "BKCH*": ["BITO", "WGMI", "MARA", "RIOT"],  # Blockchain/crypto ETFs
        "BOTZ*": ["ROBO", "IRBO", "ARKQ"],  # Robotics/AI
        "GSG*": ["DBC", "USCI", "CMDY"],  # Commodities
        "HERO*": ["ESPO", "NERD", "GAMR"],  # Gaming/esports
        "ICLN*": ["TAN", "QCLN", "FAN"],  # Clean energy
        "NION": ["TSLA", "LI", "XPEV"],  # EV companies
        "NUN": ["SOFI", "HOOD", "XP"],  # Fintech/neobanks
        "SOCL*": ["BUZZ", "METV", "ONLN"],  # Social media/online
        "SPYM*": ["VWO", "EEM", "IEMG"],  # Emerging markets
        "VEA*": ["EFA", "IEFA", "SCHF"],  # Developed markets
        "VWO*": ["IEMG", "EEM", "SPEM"],  # Emerging markets

        # Mexicanos
        "AGUA*": ["ROTPLAS", "AGUA.MX", "AQUA"],  # Agua/Rotoplas
        "ALSEA*": ["ASUR", "GAPB", "OMA"],  # Restaurantes/operadores
        "CEMEXCPO": ["GCC", "CMOCTEZ", "GMEXICOB"],  # Construcción/minería
        "FMTY14": ["FIBRAMQ", "TERRA13", "FUNO11"],  # FIBRAs
        "FUNO11": ["FIBRAMQ", "TERRA13", "FMTY14"],  # FIBRAs
        "GMXT*": ["GMEXICOB", "RAILMEX", "TFII"],  # Transporte
        "KOFUBL": ["KO", "PEP", "FMX"],  # Bebidas
        "NAFTRACISHRS": ["MEXTRAC", "SPY", "VOO"],  # ETFs México/USA
    }

    return similares.get(cleaned_ticker, [])