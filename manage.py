#!/usr/bin/env python
"""
Script de gestión de Django (manage.py).

Punto de entrada para comandos administrativos de Django:
- runserver: Inicia el servidor de desarrollo
- migrate: Aplica migraciones de base de datos
- createsuperuser: Crea usuario administrador
- collectstatic: Recopila archivos estáticos
- shell: Abre shell interactivo de Django
- etc.
"""

import os
import sys


def main():
    """Función principal que configura y ejecuta comandos de Django."""
    # Establecer el módulo de configuración por defecto
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crypto_monitor.settings')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "No se pudo importar Django. ¿Está instalado? "
            "¿Está activado el entorno virtual?"
        ) from exc

    # Ejecutar el comando pasado por línea de comandos
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()