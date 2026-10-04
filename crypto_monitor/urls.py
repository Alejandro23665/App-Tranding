"""
Configuración de URLs principal del proyecto crypto_monitor.

Define las rutas de alto nivel y delega a las apps correspondientes.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Panel de administración de Django (accesible en /admin/)
    path('admin/', admin.site.urls),

    # Rutas de la aplicación de monitoreo (dashboard principal en /)
    path('', include('monitoring.urls')),

    # Rutas para archivos estáticos en desarrollo (solo si DEBUG=True)
    # En producción, el servidor web (nginx, Apache) sirve estos archivos
]