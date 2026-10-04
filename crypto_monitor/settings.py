"""
Configuración principal del proyecto Django crypto_monitor.

Este archivo contiene toda la configuración necesaria para el funcionamiento del sistema
de monitoreo de criptomonedas en tiempo real con integración a Binance.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
# Esto debe hacerse antes de acceder a cualquier variable de entorno
load_dotenv()

# =============================================================================
# CONFIGURACIÓN DE RUTAS BASE
# =============================================================================

# BASE_DIR apunta al directorio raíz del proyecto (donde está manage.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# =============================================================================
# CONFIGURACIÓN DE SEGURIDAD
# =============================================================================

# Clave secreta para firmar cookies, tokens CSRF, etc.
# IMPORTANTE: En producción, esta clave DEBE venir de una variable de entorno
# y NUNCA debe estar hardcodeada en el código.
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-clave-temporal-solo-para-desarrollo')

# Modo debug: True para desarrollo, False para producción
# Cuando DEBUG=False, se requiere configurar ALLOWED_HOSTS correctamente
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() in ('true', '1', 'yes')

# Hosts permitidos para acceder a la aplicación
# En producción, agregar el dominio real (ej: 'midominio.com', 'www.midominio.com')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver').split(',')

# =============================================================================
# APLICACIONES INSTALADAS
# =============================================================================

INSTALLED_APPS = [
    # Aplicaciones nativas de Django
    'django.contrib.admin',          # Panel de administración
    'django.contrib.auth',           # Sistema de autenticación
    'django.contrib.contenttypes',   # Framework de tipos de contenido
    'django.contrib.sessions',       # Manejo de sesiones
    'django.contrib.messages',       # Framework de mensajes
    'django.contrib.staticfiles',    # Manejo de archivos estáticos
    'django.contrib.humanize',       # Filtros de template para números (intcomma, etc.)

    # Aplicaciones de terceros
    # (ninguna requerida para este proyecto minimalista)

    # Aplicaciones propias
    'monitoring',                    # App de monitoreo de criptomonedas
]

# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',      # Seguridad básica
    'django.contrib.sessions.middleware.SessionMiddleware',  # Sesiones
    'django.middleware.common.CommonMiddleware',          # Funciones comunes
    'django.middleware.csrf.CsrfViewMiddleware',          # Protección CSRF
    'django.contrib.auth.middleware.AuthenticationMiddleware',  # Autenticación
    'django.contrib.messages.middleware.MessageMiddleware',     # Mensajes
    'django.middleware.clickjacking.XFrameOptionsMiddleware',   # Protección clickjacking
]

# =============================================================================
# CONFIGURACIÓN DE URLs Y PLANTILLAS
# =============================================================================

ROOT_URLCONF = 'crypto_monitor.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Directorio global de plantillas
        'APP_DIRS': True,                   # Buscar plantillas en cada app
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'crypto_monitor.wsgi.application'

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'crypto-monitor-cache',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# =============================================================================
# BASE DE DATOS
# =============================================================================

# Usamos SQLite por simplicidad (archivo local)
# En producción, considerar PostgreSQL o MySQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# =============================================================================
# VALIDACIÓN DE CONTRASEÑAS
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# INTERNACIONALIZACIÓN
# =============================================================================

LANGUAGE_CODE = 'es-es'       # Español (España)
TIME_ZONE = 'UTC'             # Zona horaria UTC para consistencia en datos financieros
USE_I18N = True               # Habilitar internacionalización
USE_TZ = True                 # Usar zonas horarias aware

# =============================================================================
# ARCHIVOS ESTÁTICOS (CSS, JS, IMÁGENES)
# =============================================================================

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Directorio para archivos estáticos del proyecto
]
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Para collectstatic en producción

# =============================================================================
# CONFIGURACIÓN DE AUTO FIELD POR DEFECTO
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# CONFIGURACIÓN ESPECÍFICA DEL PROYECTO - BINANCE
# =============================================================================

# Credenciales de API de Binance (obtenidas desde variables de entorno)
# Para datos públicos (precios, ticker) no son estrictamente necesarias,
# pero se requieren para endpoints privados (cuenta, trading, etc.)
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET', '')

# Pares de trading a monitorear (símbolos en formato Binance)
# Formato: BASEQUOTE (ej: BTCUSDT = Bitcoin / Tether)
SYMBOLS_TO_MONITOR = [
    'BTCUSDT',   # Bitcoin / Tether
    'ETHUSDT',   # Ethereum / Tether
    'BNBUSDT',   # Binance Coin / Tether
    'SOLUSDT',   # Solana / Tether
    'ADAUSDT',   # Cardano / Tether
    'XRPUSDT',   # Ripple / Tether
    'DOGEUSDT',  # Dogecoin / Tether
    'MATICUSDT', # Polygon / Tether
    'DOTUSDT',   # Polkadot / Tether
    'AVAXUSDT',  # Avalanche / Tether
]

# Configuración de la conexión a Binance
BINANCE_REQUEST_TIMEOUT = 10  # Timeout en segundos para peticiones HTTP
BINANCE_RECV_WINDOW = 5000    # Ventana de recepción para firmas (ms)

# =============================================================================
# CONFIGURACIÓN GEMINI AI
# =============================================================================

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = 'gemini-flash-latest'
GEMINI_MAX_TOKENS = 1024
GEMINI_TEMPERATURE = 0.3

# =============================================================================
# LOGGING (Registro de eventos)
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'crypto_monitor.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'monitoring': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Crear directorio de logs si no existe
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)