"""
Configuración WSGI para el proyecto crypto_monitor.

Este archivo permite desplegar la aplicación en servidores WSGI como Gunicorn, uWSGI, etc.
"""

import os
from django.core.wsgi import get_wsgi_application

# Establecer el módulo de configuración de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_monitor.settings')

# Obtener la aplicación WSGI
application = get_wsgi_application()