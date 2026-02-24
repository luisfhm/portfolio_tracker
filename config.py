# Configuración - NO SUBIR A GIT
# Crea un archivo .env con tus credenciales
# Ejemplo:
# SUPABASE_URL=https://tu-proyecto.supabase.co
# SUPABASE_KEY=tu-api-key

import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
