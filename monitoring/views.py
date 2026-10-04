"""
Vistas de la aplicación monitoring.

Contiene la lógica para obtener datos de mercado de Binance
y renderizar el dashboard principal.
"""

import json
import logging
import statistics
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional

import google.generativeai as genai
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

# Configurar logger para esta app
logger = logging.getLogger(__name__)


def get_binance_client() -> Client:
    """
    Crea y retorna una instancia del cliente de Binance.

    Usa las credenciales configuradas en settings.py (variables de entorno).
    Para endpoints públicos (ticker, klines), las credenciales son opcionales.

    Returns:
        Client: Instancia configurada de python-binance

    Raises:
        ValueError: Si las credenciales son requeridas pero no están configuradas
    """
    api_key = getattr(settings, 'BINANCE_API_KEY', '')
    api_secret = getattr(settings, 'BINANCE_API_SECRET', '')

    # Crear cliente (credenciales vacías funcionan para datos públicos)
    client = Client(
        api_key=api_key,
        api_secret=api_secret,
        requests_params={
            'timeout': getattr(settings, 'BINANCE_REQUEST_TIMEOUT', 10),
        }
    )

    return client


def fetch_ticker_data(client: Client, symbols: List[str]) -> List[Dict[str, Any]]:
    """
    Obtiene datos de ticker 24h para una lista de símbolos.

    Args:
        client: Cliente de Binance ya inicializado
        symbols: Lista de símbolos a consultar (ej: ['BTCUSDT', 'ETHUSDT'])

    Returns:
        Lista de diccionarios con datos de mercado formateados

    Raises:
        BinanceAPIException: Error en la API de Binance
        BinanceRequestException: Error de red/conexión
    """
    results = []

    for symbol in symbols:
        try:
            # Obtener ticker 24h para el símbolo
            # Devuelve datos como: priceChange, priceChangePercent, lastPrice, volume, etc.
            ticker = client.get_ticker(symbol=symbol)

            # Formatear datos para la plantilla
            formatted_data = {
                'symbol': symbol,
                'base_asset': symbol.replace('USDT', ''),
                'quote_asset': 'USDT',
                'last_price': float(ticker.get('lastPrice', 0)),
                'price_change': float(ticker.get('priceChange', 0)),
                'price_change_percent': float(ticker.get('priceChangePercent', 0)),
                'volume': float(ticker.get('volume', 0)),
                'quote_volume': float(ticker.get('quoteVolume', 0)),
                'high_price': float(ticker.get('highPrice', 0)),
                'low_price': float(ticker.get('lowPrice', 0)),
                'open_price': float(ticker.get('openPrice', 0)),
                'count': int(ticker.get('count', 0)),
                'bid_price': float(ticker.get('bidPrice', 0)),
                'ask_price': float(ticker.get('askPrice', 0)),
            }
            results.append(formatted_data)

        except BinanceAPIException as e:
            logger.error(f"Error API Binance para {symbol}: {e.message} (code: {e.code})")
            # Agregar entrada de error para mostrar en UI
            results.append({
                'symbol': symbol,
                'error': f"Error API: {e.message}",
            })
        except BinanceRequestException as e:
            logger.error(f"Error de red para {symbol}: {str(e)}")
            results.append({
                'symbol': symbol,
                'error': f"Error de conexión: {str(e)}",
            })
        except Exception as e:
            logger.exception(f"Error inesperado para {symbol}")
            results.append({
                'symbol': symbol,
                'error': f"Error inesperado: {str(e)}",
            })

    return results


def fetch_all_usdt_tickers(client: Client) -> List[Dict[str, Any]]:
    """
    Obtiene datos de ticker 24h para TODOS los pares USDT disponibles en Binance.
    Usa el endpoint get_ticker() sin símbolo para obtener todos los tickers de una vez.

    Args:
        client: Cliente de Binance ya inicializado

    Returns:
        Lista de diccionarios con datos de mercado formateados solo para pares USDT
    """
    try:
        # Obtener todos los tickers de una sola llamada (mucho más eficiente)
        all_tickers = client.get_ticker()

        results = []
        for ticker in all_tickers:
            symbol = ticker.get('symbol', '')
            # Filtrar solo pares USDT (spot trading)
            if not symbol.endswith('USDT'):
                continue
            # Excluir tokens apalancados (UP/DOWN/BULL/BEAR)
            base = symbol[:-4]  # quitar 'USDT'
            if any(base.endswith(suffix) for suffix in ['UP', 'DOWN', 'BULL', 'BEAR']):
                continue
            # Excluir stablecoins vs USDT (poco interés)
            if base in ['USDC', 'BUSD', 'TUSD', 'USDP', 'FDUSD', 'DAI', 'EUR', 'AEUR']:
                continue

            try:
                last_price = float(ticker.get('lastPrice', 0))
                if last_price <= 0:
                    continue

                volume = float(ticker.get('volume', 0))
                quote_volume = float(ticker.get('quoteVolume', 0))
                if quote_volume < 100000:  # Filtrar volumen muy bajo (< $100k)
                    continue

                formatted_data = {
                    'symbol': symbol,
                    'base_asset': base,
                    'quote_asset': 'USDT',
                    'last_price': last_price,
                    'price_change': float(ticker.get('priceChange', 0)),
                    'price_change_percent': float(ticker.get('priceChangePercent', 0)),
                    'volume': volume,
                    'quote_volume': quote_volume,
                    'high_price': float(ticker.get('highPrice', 0)),
                    'low_price': float(ticker.get('lowPrice', 0)),
                    'open_price': float(ticker.get('openPrice', 0)),
                    'count': int(ticker.get('count', 0)),
                    'bid_price': float(ticker.get('bidPrice', 0)),
                    'ask_price': float(ticker.get('askPrice', 0)),
                }
                results.append(formatted_data)
            except (ValueError, TypeError):
                continue

        logger.info(f"Fetched {len(results)} USDT pairs from Binance")
        return results

    except BinanceAPIException as e:
        logger.error(f"Error API Binance fetching all tickers: {e.message} (code: {e.code})")
        raise
    except BinanceRequestException as e:
        logger.error(f"Error de red fetching all tickers: {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"Error inesperado fetching all tickers")
        raise


def fetch_klines(client: Client, symbol: str, interval: str = '1h', limit: int = 200) -> List[Dict[str, Any]]:
    """
    Obtiene datos de velas (klines/candlesticks) para un símbolo.

    Args:
        client: Cliente de Binance ya inicializado
        symbol: Símbolo a consultar (ej: 'BTCUSDT')
        interval: Intervalo de tiempo (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
        limit: Número máximo de velas a obtener (máx 1000)

    Returns:
        Lista de diccionarios con datos OHLCV formateados

    Raises:
        BinanceAPIException: Error en la API de Binance
        BinanceRequestException: Error de red/conexión
    """
    try:
        # Obtener klines de Binance
        # Retorna lista de: [open_time, open, high, low, close, volume, close_time, quote_asset_volume, trades, ...]
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)

        formatted_klines = []
        for k in klines:
            formatted_klines.append({
                'time': int(k[0] / 1000),  # Convertir a segundos para Lightweight Charts
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5]),
            })
        return formatted_klines

    except BinanceAPIException as e:
        logger.error(f"Error API Binance klines para {symbol}: {e.message} (code: {e.code})")
        raise
    except BinanceRequestException as e:
        logger.error(f"Error de red klines para {symbol}: {str(e)}")
        raise
    except Exception as e:
        logger.exception(f"Error inesperado klines para {symbol}")
        raise


def calculate_volatility(klines: List[Dict[str, Any]]) -> float:
    """
    Calcula la volatilidad basada en el rango de precios (high-low) / close promedio.
    Retorna un porcentaje de volatilidad.
    """
    if not klines or len(klines) < 2:
        return 0.0

    ranges = []
    for k in klines:
        if k['close'] > 0:
            daily_range = (k['high'] - k['low']) / k['close'] * 100
            ranges.append(daily_range)

    if not ranges:
        return 0.0

    # Usar la desviación estándar de los rangos diarios como medida de volatilidad
    try:
        return statistics.stdev(ranges) if len(ranges) > 1 else ranges[0]
    except statistics.StatisticsError:
        return ranges[0] if ranges else 0.0


def analyze_market_performance(client: Client, symbols: List[str]) -> Dict[str, Any]:
    """
    Analiza el rendimiento de mercado para identificar top/flop 10.
    Combina cambio de precio 24h y volatilidad para ranking.
    """
    # Obtener datos de ticker
    ticker_data = fetch_ticker_data(client, symbols)

    # Filtrar solo datos válidos
    valid_data = [d for d in ticker_data if not d.get('error') and d['last_price'] > 0]

    # Obtener klines para calcular volatilidad (usar 1d interval, 30 días)
    for item in valid_data:
        try:
            klines = fetch_klines(client, item['symbol'], '1d', 30)
            item['volatility'] = calculate_volatility(klines)
        except Exception:
            item['volatility'] = 0.0

    # Ranking combinado: score = price_change_percent * (1 + volatility_factor)
    # Esto premia tanto ganancias como volatilidad (oportunidades de trading)
    for item in valid_data:
        volatility_factor = min(item['volatility'] / 10, 1.0)  # Cap at 1.0
        item['performance_score'] = item['price_change_percent'] * (1 + volatility_factor * 0.5)
        item['volatility_score'] = item['volatility']

    # Top 10 por performance score (mejores)
    top_performers = sorted(valid_data, key=lambda x: x['performance_score'], reverse=True)[:10]

    # Flop 10 por performance score (peores)
    flop_performers = sorted(valid_data, key=lambda x: x['performance_score'])[:10]

    # Top 10 por volatilidad pura
    top_volatile = sorted(valid_data, key=lambda x: x['volatility_score'], reverse=True)[:10]

    return {
        'top_performers': top_performers,
        'flop_performers': flop_performers,
        'top_volatile': top_volatile,
        'total_analyzed': len(valid_data),
    }


def analyze_all_usdt_performance(client: Client) -> Dict[str, Any]:
    """
    Analiza el rendimiento de TODOS los pares USDT en Binance.
    Obtiene todos los tickers de una vez, filtra y rankea.
    """
    # Obtener datos de ticker de todos los pares USDT
    all_ticker_data = fetch_all_usdt_tickers(client)

    # Filtrar solo datos válidos con volumen significativo
    valid_data = [d for d in all_ticker_data if not d.get('error') and d['last_price'] > 0 and d['quote_volume'] > 100000]

    # Obtener klines para calcular volatilidad (usar 1d interval, 30 días)
    # Limitamos a top 50 por volumen para no hacer demasiadas llamadas API
    top_by_volume = sorted(valid_data, key=lambda x: x['quote_volume'], reverse=True)[:50]

    for item in top_by_volume:
        try:
            klines = fetch_klines(client, item['symbol'], '1d', 30)
            item['volatility'] = calculate_volatility(klines)
        except Exception:
            item['volatility'] = 0.0

    # Para el resto, asignar volatilidad 0 (se ordenarán al final en volatilidad)
    for item in valid_data:
        if 'volatility' not in item:
            item['volatility'] = 0.0

    # Ranking combinado: score = price_change_percent * (1 + volatility_factor)
    for item in valid_data:
        volatility_factor = min(item['volatility'] / 10, 1.0)  # Cap at 1.0
        item['performance_score'] = item['price_change_percent'] * (1 + volatility_factor * 0.5)
        item['volatility_score'] = item['volatility']

    # Top 10 por performance score (mejores)
    top_performers = sorted(valid_data, key=lambda x: x['performance_score'], reverse=True)[:10]

    # Flop 10 por performance score (peores)
    flop_performers = sorted(valid_data, key=lambda x: x['performance_score'])[:10]

    # Top 10 por volatilidad pura
    top_volatile = sorted(valid_data, key=lambda x: x['volatility_score'], reverse=True)[:10]

    return {
        'top_performers': top_performers,
        'flop_performers': flop_performers,
        'top_volatile': top_volatile,
        'total_analyzed': len(valid_data),
    }


def fetch_ticker_single(client: Client, symbol: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene datos de ticker 24h para UN símbolo específico.
    Mucho más rápido que fetch_all_usdt_tickers.
    """
    try:
        ticker = client.get_ticker(symbol=symbol)
        
        last_price = float(ticker.get('lastPrice', 0))
        if last_price <= 0:
            return None
            
        volume = float(ticker.get('volume', 0))
        quote_volume = float(ticker.get('quoteVolume', 0))
        
        base = symbol[:-4]  # quitar 'USDT'
        
        return {
            'symbol': symbol,
            'base_asset': base,
            'quote_asset': 'USDT',
            'last_price': last_price,
            'price_change': float(ticker.get('priceChange', 0)),
            'price_change_percent': float(ticker.get('priceChangePercent', 0)),
            'volume': volume,
            'quote_volume': quote_volume,
            'high_price': float(ticker.get('highPrice', 0)),
            'low_price': float(ticker.get('lowPrice', 0)),
            'open_price': float(ticker.get('openPrice', 0)),
            'count': int(ticker.get('count', 0)),
            'bid_price': float(ticker.get('bidPrice', 0)),
            'ask_price': float(ticker.get('askPrice', 0)),
        }
    except Exception:
        return None


def search_coin_fast(client: Client, query: str) -> Optional[Dict[str, Any]]:
    """
    Busca una criptomoneda de forma optimizada (solo 1 llamada API).
    Retorna datos esenciales para análisis IA.
    """
    query = query.strip().upper()
    if not query:
        return None

    # Normalizar símbolo
    symbol = query if query.endswith('USDT') else query + 'USDT'
    
    # Cache key para ticker (30 segundos)
    cache_key = f'ticker_{symbol}'
    coin_data = cache.get(cache_key)
    
    if not coin_data:
        coin_data = fetch_ticker_single(client, symbol)
        if coin_data:
            cache.set(cache_key, coin_data, 30)
    
    if not coin_data:
        return None
    
    # Calcular volatilidad con cache (60 segundos)
    vol_cache_key = f'vol_{symbol}'
    volatility = cache.get(vol_cache_key)
    
    if volatility is None:
        try:
            klines = fetch_klines(client, symbol, '1d', 20)  # Reducido a 20
            volatility = calculate_volatility(klines)
            cache.set(vol_cache_key, volatility, 60)
        except Exception:
            volatility = 0.0
    
    coin_data['volatility'] = volatility
    
    # Calcular indicadores técnicos básicos desde klines
    try:
        klines = fetch_klines(client, symbol, '1d', 20)
        if klines:
            closes = [k['close'] for k in klines]
            highs = [k['high'] for k in klines]
            lows = [k['low'] for k in klines]
            
            # RSI (14)
            if len(closes) >= 15:
                rsi = _calculate_rsi_simple(closes)
                coin_data['rsi'] = round(rsi, 1)
            
            # Tendencia (últimos 10 vs primeros 10)
            if len(closes) >= 10:
                trend = 'Bullish' if closes[-1] > closes[0] else 'Bearish'
                coin_data['trend'] = trend
            
            # Soporte/Resistencia (20 días)
            if highs and lows:
                coin_data['resistance'] = max(highs)
                coin_data['support'] = min(lows)
    except Exception:
        pass
    
    # Calcular spread
    if coin_data.get('ask_price') and coin_data.get('bid_price'):
        coin_data['spread'] = coin_data['ask_price'] - coin_data['bid_price']
    
    return coin_data


def _calculate_rsi_simple(closes: List[float], period: int = 14) -> float:
    """Calcula RSI simple."""
    if len(closes) < period + 1:
        return 50.0
    
    gains = []
    losses = []
    
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def search_coin(client: Client, query: str) -> Optional[Dict[str, Any]]:
    """
    Busca una criptomoneda por símbolo o nombre base.
    Retorna datos completos incluyendo rankings.
    """
    query = query.strip().upper()
    if not query:
        return None

    # Normalizar: si no termina en USDT, agregarlo
    symbol = query if query.endswith('USDT') else query + 'USDT'

    # Obtener datos de todos los pares USDT para rankings
    all_ticker_data = fetch_all_usdt_tickers(client)

    # Filtrar válidos
    valid_data = [d for d in all_ticker_data if not d.get('error') and d['last_price'] > 0 and d['quote_volume'] > 100000]

    # Buscar el símbolo exacto
    coin_data = None
    for item in valid_data:
        if item['symbol'] == symbol or item['base_asset'].upper() == query.replace('USDT', ''):
            coin_data = item
            break

    if not coin_data:
        return None

    # Calcular volatilidad para esta moneda
    try:
        klines = fetch_klines(client, coin_data['symbol'], '1d', 30)
        coin_data['volatility'] = calculate_volatility(klines)
    except Exception:
        coin_data['volatility'] = 0.0

    # Calcular rankings en el contexto de todos los datos válidos
    # Primero calcular volatilidad para top 50 por volumen (para ranking preciso)
    top_by_volume = sorted(valid_data, key=lambda x: x['quote_volume'], reverse=True)[:50]
    for item in top_by_volume:
        if 'volatility' not in item:
            try:
                klines = fetch_klines(client, item['symbol'], '1d', 30)
                item['volatility'] = calculate_volatility(klines)
            except Exception:
                item['volatility'] = 0.0

    for item in valid_data:
        if 'volatility' not in item:
            item['volatility'] = 0.0

    # Calcular performance score para todos
    for item in valid_data:
        volatility_factor = min(item['volatility'] / 10, 1.0)
        item['performance_score'] = item['price_change_percent'] * (1 + volatility_factor * 0.5)
        item['volatility_score'] = item['volatility']

    # Rankings
    by_performance = sorted(valid_data, key=lambda x: x['performance_score'], reverse=True)
    by_volatility = sorted(valid_data, key=lambda x: x['volatility_score'], reverse=True)
    by_price_change = sorted(valid_data, key=lambda x: x['price_change_percent'], reverse=True)
    by_volume = sorted(valid_data, key=lambda x: x['quote_volume'], reverse=True)

    # Encontrar posición en cada ranking (1-indexed)
    performance_rank = next((i + 1 for i, item in enumerate(by_performance) if item['symbol'] == coin_data['symbol']), None)
    volatility_rank = next((i + 1 for i, item in enumerate(by_volatility) if item['symbol'] == coin_data['symbol']), None)
    price_change_rank = next((i + 1 for i, item in enumerate(by_price_change) if item['symbol'] == coin_data['symbol']), None)
    volume_rank = next((i + 1 for i, item in enumerate(by_volume) if item['symbol'] == coin_data['symbol']), None)

    # Determinar calificación de rendimiento
    pct = coin_data['price_change_percent']
    vol = coin_data['volatility']
    perf_score = coin_data['performance_score']

    if pct > 20:
        performance_rating = 'Excellent'
        rating_class = 'text-brand-400'
        rating_icon = 'fa-star'
    elif pct > 10:
        performance_rating = 'Strong'
        rating_class = 'text-brand-400'
        rating_icon = 'fa-arrow-trend-up'
    elif pct > 5:
        performance_rating = 'Good'
        rating_class = 'text-brand-400'
        rating_icon = 'fa-arrow-up'
    elif pct > 0:
        performance_rating = 'Positive'
        rating_class = 'text-brand-400'
        rating_icon = 'fa-arrow-up-right'
    elif pct > -5:
        performance_rating = 'Slightly Negative'
        rating_class = 'text-warning-400'
        rating_icon = 'fa-arrow-down-right'
    elif pct > -10:
        performance_rating = 'Weak'
        rating_class = 'text-warning-400'
        rating_icon = 'fa-arrow-down'
    elif pct > -20:
        performance_rating = 'Poor'
        rating_class = 'text-danger-400'
        rating_icon = 'fa-arrow-trend-down'
    else:
        performance_rating = 'Critical'
        rating_class = 'text-danger-400'
        rating_icon = 'fa-triangle-exclamation'

    # Determinar calificación de volatilidad
    if vol > 15:
        volatility_rating = 'Extreme'
        vol_rating_class = 'text-danger-400'
    elif vol > 10:
        volatility_rating = 'High'
        vol_rating_class = 'text-warning-400'
    elif vol > 5:
        volatility_rating = 'Moderate'
        vol_rating_class = 'text-brand-400'
    elif vol > 2:
        volatility_rating = 'Low'
        vol_rating_class = 'text-brand-400'
    else:
        volatility_rating = 'Very Low'
        vol_rating_class = 'text-muted-400'

    # Calcular percentiles para barras de progreso
    total = len(valid_data)
    percentile_performance = round((1 - (performance_rank - 1) / total) * 100, 1) if performance_rank else 0
    percentile_volatility = round((1 - (volatility_rank - 1) / total) * 100, 1) if volatility_rank else 0
    percentile_price_change = round((1 - (price_change_rank - 1) / total) * 100, 1) if price_change_rank else 0
    percentile_volume = round((1 - (volume_rank - 1) / total) * 100, 1) if volume_rank else 0

    # Calcular spread
    spread = coin_data['ask_price'] - coin_data['bid_price']

    coin_data.update({
        'performance_rank': performance_rank,
        'volatility_rank': volatility_rank,
        'price_change_rank': price_change_rank,
        'volume_rank': volume_rank,
        'total_analyzed': total,
        'performance_rating': performance_rating,
        'performance_rating_class': rating_class,
        'performance_rating_icon': rating_icon,
        'volatility_rating': volatility_rating,
        'volatility_rating_class': vol_rating_class,
        'percentile_performance': percentile_performance,
        'percentile_volatility': percentile_volatility,
        'percentile_price_change': percentile_price_change,
        'percentile_volume': percentile_volume,
        'spread': spread,
    })

    return coin_data


class SearchView(View):
    """
    Vista para buscar una criptomoneda y mostrar su información detallada.
    """

    template_name = 'search.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        query = request.GET.get('q', '').strip()
        client = get_binance_client()

        context = {
            'page_title': 'Buscar Criptomoneda',
            'query': query,
            'coin': None,
            'error': None,
        }

        if query:
            coin = search_coin(client, query)
            if coin:
                context['coin'] = coin
            else:
                context['error'] = f'No se encontró la criptomoneda "{query}". Verifica el símbolo (ej: BTC, ETH, SOL) o nombre.'

        return render(request, self.template_name, context)


class DashboardView(View):
    """
    Vista principal del dashboard de monitoreo.

    Maneja tanto peticiones GET normales (renderizado HTML completo)
    como peticiones AJAX (retorno JSON para actualización parcial).
    """

    template_name = 'index.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        """
        Maneja peticiones GET al dashboard.

        Si la petición es AJAX (fetch/XMLHttpRequest), retorna JSON.
        Si es petición normal, renderiza la plantilla HTML completa.
        """
        # Obtener símbolos a monitorear desde settings
        symbols = getattr(settings, 'SYMBOLS_TO_MONITOR', ['BTCUSDT', 'ETHUSDT'])

        # Crear cliente de Binance
        client = get_binance_client()

        # Obtener datos de mercado
        market_data = fetch_ticker_data(client, symbols)

        # Verificar si es petición AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        is_fetch = request.headers.get('Accept', '').find('application/json') != -1

        if is_ajax or is_fetch:
            # Retornar JSON para actualizaciones dinámicas
            return JsonResponse({
                'success': True,
                'data': market_data,
                'timestamp': self._get_current_timestamp(),
            })

        # Renderizar plantilla completa
        context = {
            'market_data': market_data,
            'page_title': 'Monitor de Criptomonedas - Binance',
            'symbols_count': len(symbols),
        }
        return render(request, self.template_name, context)

    def _get_current_timestamp(self) -> str:
        """Retorna timestamp actual en formato ISO 8601."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


class TopFlopView(View):
    """
    Vista para mostrar las 10 mejores y 10 peores criptomonedas
    basadas en performance y volatilidad de TODOS los pares USDT.
    """

    template_name = 'top_flop.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        client = get_binance_client()

        analysis = analyze_all_usdt_performance(client)

        context = {
            'page_title': 'Top & Flop - Rendimiento de Mercado',
            'top_performers': analysis['top_performers'],
            'flop_performers': analysis['flop_performers'],
            'top_volatile': analysis['top_volatile'],
            'total_analyzed': analysis['total_analyzed'],
            'timestamp': self._get_current_timestamp(),
        }
        return render(request, self.template_name, context)

    def _get_current_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


@method_decorator(csrf_exempt, name='dispatch')
class ApiTickerView(View):
    """
    Endpoint API para obtener datos de ticker en formato JSON.

    Permite consultar precios actuales sin renderizar HTML.
    Útil para integraciones externas o frontends separados.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Retorna datos de ticker para todos los símbolos configurados."""
        symbols = getattr(settings, 'SYMBOLS_TO_MONITOR', ['BTCUSDT', 'ETHUSDT'])
        client = get_binance_client()
        market_data = fetch_ticker_data(client, symbols)

        return JsonResponse({
            'success': True,
            'data': market_data,
            'timestamp': self._get_current_timestamp(),
        })

    def _get_current_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


@method_decorator(csrf_exempt, name='dispatch')
class ApiKlinesView(View):
    """
    Endpoint API para obtener datos de velas (klines) para gráficos.
    Permite cualquier par USDT válido de Binance.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Retorna datos OHLCV para un símbolo específico."""
        symbol = request.GET.get('symbol', '').upper()
        interval = request.GET.get('interval', '1h')
        limit = int(request.GET.get('limit', 200))

        # Validar formato básico del símbolo (debe terminar en USDT)
        if not symbol.endswith('USDT') or len(symbol) < 5:
            return JsonResponse({
                'success': False,
                'error': f'Formato de símbolo inválido: {symbol}. Debe ser par USDT (ej: BTCUSDT)',
            }, status=400)

        # Validar intervalo
        valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        if interval not in valid_intervals:
            interval = '1h'

        # Limitar límite
        limit = max(1, min(limit, 1000))

        try:
            client = get_binance_client()
            klines = fetch_klines(client, symbol, interval, limit)

            if not klines:
                return JsonResponse({
                    'success': False,
                    'error': f'No hay datos disponibles para {symbol}',
                }, status=404)

            return JsonResponse({
                'success': True,
                'symbol': symbol,
                'interval': interval,
                'data': klines,
            })
        except Exception as e:
            logger.error(f"Error fetching klines for {symbol}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ApiTopFlopView(View):
    """
    Endpoint API para obtener datos de top/flop en formato JSON.
    Analiza TODOS los pares USDT disponibles en Binance.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        client = get_binance_client()

        try:
            analysis = analyze_all_usdt_performance(client)
            return JsonResponse({
                'success': True,
                'top_performers': analysis['top_performers'],
                'flop_performers': analysis['flop_performers'],
                'top_volatile': analysis['top_volatile'],
                'total_analyzed': analysis['total_analyzed'],
                'timestamp': self._get_current_timestamp(),
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)

    def _get_current_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


@method_decorator(csrf_exempt, name='dispatch')
class ApiSearchView(View):
    """
    Endpoint API para buscar una criptomoneda por símbolo/nombre.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Parámetro "q" requerido',
            }, status=400)

        client = get_binance_client()

        try:
            coin = search_coin(client, query)
            if coin:
                return JsonResponse({
                    'success': True,
                    'coin': coin,
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'No se encontró la criptomoneda "{query}"',
                }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)


def health_check(request: HttpRequest) -> JsonResponse:
    """
    Endpoint de health check para verificar estado del servicio.

    Útil para balanceadores de carga, Docker, Kubernetes, etc.
    """
    return JsonResponse({
        'status': 'ok',
        'service': 'crypto-monitor',
        'version': '1.0.0',
    })


class AIAnalysisView(View):
    """
    Vista para análisis de criptomonedas con IA (Gemini).
    Optimizada para velocidad usando búsqueda directa y cache.
    """

    template_name = 'ai_analysis.html'

    def get(self, request: HttpRequest) -> HttpResponse:
        symbol = request.GET.get('symbol', '').strip().upper()
        
        context = {
            'page_title': 'Análisis IA - Crypto Monitor',
            'symbol': symbol,
            'analysis': None,
            'error': None,
        }
        
        if symbol:
            # Normalizar símbolo
            if not symbol.endswith('USDT'):
                symbol = symbol + 'USDT'
            
            client = get_binance_client()
            
            try:
                # Obtener datos de mercado (optimizado con cache)
                coin_data = search_coin_fast(client, symbol)
                
                if not coin_data:
                    context['error'] = f'No se encontró la criptomoneda "{symbol}".'
                else:
                    # Obtener klines reducidos para análisis técnico (20 en lugar de 60)
                    klines = fetch_klines(client, symbol, '1d', 20)
                    
                    # Generar análisis con Gemini
                    analysis = self._generate_ai_analysis(coin_data, klines)
                    context['analysis'] = analysis
                    context['coin'] = coin_data
                    
            except Exception as e:
                logger.exception(f"Error en análisis IA para {symbol}")
                context['error'] = f'Error al generar análisis: {str(e)}'
        
        return render(request, self.template_name, context)
    
    def post(self, request: HttpRequest) -> HttpResponse:
        """Maneja el envío del formulario de análisis."""
        symbol = request.POST.get('symbol', '').strip().upper()
        if symbol:
            # Redirigir a GET con el símbolo para evitar reenvío
            from django.shortcuts import redirect
            return redirect(f'{request.path}?symbol={symbol}')
        return self.get(request)
    
    def _generate_ai_analysis(self, coin_data: Dict[str, Any], klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Genera análisis técnico usando Gemini AI.
        """
        # Configurar Gemini
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key:
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'summary': 'API Key de Gemini no configurada',
                'details': [],
                'risk_level': 'Unknown',
            }
        
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=getattr(settings, 'GEMINI_MODEL', 'gemini-1.5-flash'),
                generation_config={
                    'temperature': getattr(settings, 'GEMINI_TEMPERATURE', 0.3),
                }
            )
            
            # Preparar datos para el prompt
            market_summary = self._prepare_market_data(coin_data, klines)
            
            prompt = self._build_analysis_prompt(market_summary)
            
            response = model.generate_content(prompt)
            
            # Parsear respuesta
            return self._parse_ai_response(response.text)
            
        except Exception as e:
            logger.exception("Error generando análisis con Gemini")
            return {
                'signal': 'ERROR',
                'confidence': 0,
                'summary': f'Error en IA: {str(e)}',
                'details': [],
                'risk_level': 'Unknown',
            }
    
    def _prepare_market_data(self, coin_data: Dict[str, Any], klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepara datos de mercado para el prompt."""
        if not klines:
            return {
                'symbol': coin_data.get('symbol', ''),
                'current_price': coin_data.get('last_price', 0),
                'change_24h': coin_data.get('price_change_percent', 0),
                'volume_24h': coin_data.get('quote_volume', 0),
                'high_24h': coin_data.get('high_price', 0),
                'low_24h': coin_data.get('low_price', 0),
                'volatility': coin_data.get('volatility', 0),
                'rsi': None,
                'trend': 'Unknown',
            }
        
        # Calcular RSI simple (14 períodos)
        closes = [k['close'] for k in klines[-15:]]
        rsi = self._calculate_rsi(closes) if len(closes) >= 15 else None
        
        # Determinar tendencia
        recent_closes = [k['close'] for k in klines[-10:]]
        trend = 'Bullish' if recent_closes[-1] > recent_closes[0] else 'Bearish'
        
        # Soportes y resistencias simples
        highs = [k['high'] for k in klines[-20:]]
        lows = [k['low'] for k in klines[-20:]]
        resistance = max(highs) if highs else 0
        support = min(lows) if lows else 0
        
        return {
            'symbol': coin_data.get('symbol', ''),
            'current_price': coin_data.get('last_price', 0),
            'change_24h': coin_data.get('price_change_percent', 0),
            'volume_24h': coin_data.get('quote_volume', 0),
            'high_24h': coin_data.get('high_price', 0),
            'low_24h': coin_data.get('low_price', 0),
            'volatility': coin_data.get('volatility', 0),
            'rsi': round(rsi, 1) if rsi else None,
            'trend': trend,
            'resistance': resistance,
            'support': support,
            'klines_count': len(klines),
        }
    
    def _calculate_rsi(self, closes: List[float], period: int = 14) -> Optional[float]:
        """Calcula RSI simple."""
        if len(closes) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _build_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Construye el prompt optimizado para Gemini (menos tokens)."""
        return f"""Analiza {data['symbol']} y genera señal de trading JSON:

Precio: ${data['current_price']:,.4f} | 24h: {data['change_24h']:+.2f}% | Vol: ${data['volume_24h']:,.0f}
RSI: {data['rsi'] or 'N/A'} | Tendencia: {data['trend']} | Volatilidad: {data['volatility']:.1f}%
Soporte: ${data['support']:,.4f} | Resistencia: ${data['resistance']:,.4f}

Responde SOLO JSON:
{{"signal":"BUY/HOLD/SELL","confidence":0-100,"summary":"...","details":["...","..."],"risk_level":"LOW/MEDIUM/HIGH","entry_zone":"...","stop_loss":"...","take_profit":"..."}}"""
    
    def _parse_ai_response(self, text: str) -> Dict[str, Any]:
        """Parsea la respuesta de Gemini."""
        try:
            # Intentar extraer JSON de la respuesta
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = text[start:end]
                parsed = json.loads(json_str)
                
                # Validar campos requeridos
                return {
                    'signal': parsed.get('signal', 'HOLD'),
                    'confidence': max(0, min(100, parsed.get('confidence', 50))),
                    'summary': parsed.get('summary', 'Análisis completado'),
                    'details': parsed.get('details', [])[:5],
                    'risk_level': parsed.get('risk_level', 'MEDIUM'),
                    'entry_zone': parsed.get('entry_zone', 'N/A'),
                    'stop_loss': parsed.get('stop_loss', 'N/A'),
                    'take_profit': parsed.get('take_profit', 'N/A'),
                }
        except Exception as e:
            logger.warning(f"Error parseando respuesta IA: {e}")
        
        # Fallback si no se puede parsear
        return {
            'signal': 'HOLD',
            'confidence': 50,
            'summary': text[:500] if text else 'Análisis no disponible',
            'details': ['Error al parsear respuesta de IA'],
            'risk_level': 'MEDIUM',
            'entry_zone': 'N/A',
            'stop_loss': 'N/A',
            'take_profit': 'N/A',
        }


@method_decorator(csrf_exempt, name='dispatch')
class ApiAIAnalysisView(View):
    """
    Endpoint API para análisis IA (optimizado).
    """
    
    def get(self, request: HttpRequest) -> JsonResponse:
        symbol = request.GET.get('symbol', '').strip().upper()
        if not symbol:
            return JsonResponse({
                'success': False,
                'error': 'Parámetro "symbol" requerido',
            }, status=400)
        
        if not symbol.endswith('USDT'):
            symbol = symbol + 'USDT'
        
        client = get_binance_client()
        
        try:
            coin_data = search_coin_fast(client, symbol)
            if not coin_data:
                return JsonResponse({
                    'success': False,
                    'error': f'No se encontró la criptomoneda "{symbol}"',
                }, status=404)
            
            klines = fetch_klines(client, symbol, '1d', 20)
            view_instance = AIAnalysisView()
            analysis = view_instance._generate_ai_analysis(coin_data, klines)
            
            return JsonResponse({
                'success': True,
                'symbol': symbol,
                'analysis': analysis,
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e),
            }, status=500)