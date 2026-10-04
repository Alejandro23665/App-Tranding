"""
Configuración de URLs de la aplicación monitoring.

Define las rutas específicas para el dashboard y API de monitoreo.
"""

from django.urls import path

from .views import (
    AIAnalysisView, ApiAIAnalysisView, ApiKlinesView, 
    ApiSearchView, ApiTickerView, ApiTopFlopView, 
    DashboardView, SearchView, TopFlopView, health_check
)

app_name = 'monitoring'  # Namespace para URLs (ej: 'monitoring:dashboard')

urlpatterns = [
    # Dashboard principal (vista HTML)
    path('', DashboardView.as_view(), name='dashboard'),

    # Análisis IA
    path('ai/', AIAnalysisView.as_view(), name='ai_analysis'),
    path('api/ai/', ApiAIAnalysisView.as_view(), name='api_ai_analysis'),

    # Búsqueda de criptomonedas
    path('search/', SearchView.as_view(), name='search'),
    path('api/search/', ApiSearchView.as_view(), name='api_search'),

    # Top/Flop página
    path('top-flop/', TopFlopView.as_view(), name='top_flop'),

    # API endpoint para datos de ticker (JSON)
    path('api/ticker/', ApiTickerView.as_view(), name='api_ticker'),

    # API endpoint para datos de velas/klines (JSON)
    path('api/klines/', ApiKlinesView.as_view(), name='api_klines'),

    # API endpoint para top/flop (JSON)
    path('api/top-flop/', ApiTopFlopView.as_view(), name='api_top_flop'),

    # Health check endpoint
    path('health/', health_check, name='health_check'),
]