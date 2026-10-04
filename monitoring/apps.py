"""
Configuración de la aplicación monitoring.

Define metadatos y comportamientos de la app de monitoreo de criptomonedas.
"""

from django.apps import AppConfig


class MonitoringConfig(AppConfig):
    """Configuración de la app monitoring."""

    # Nombre por defecto del campo auto-incremental para modelos
    default_auto_field = 'django.db.models.BigAutoField'

    # Nombre completo de la aplicación (ruta Python)
    name = 'monitoring'

    # Nombre legible para humanos (usado en admin, etc.)
    verbose_name = 'Monitoreo de Criptomonedas'

    def ready(self):
        """
        Método llamado cuando la app está completamente cargada.
        Útil para registrar señales, programar tareas, etc.
        """
        # Importar señales si las hubiera (comentado por simplicidad)
        # import monitoring.signals  # noqa
        pass