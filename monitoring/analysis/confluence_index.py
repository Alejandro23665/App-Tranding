"""
Módulo de Índice de Confluencia Multicriterio para Criptomonedas
================================================================

Este módulo calcula un score de 0 a 100 que evalúa la confluencia de tres pilares técnicos:
1. Tendencia del Precio (alineación de EMAs)
2. Aceleración del Volumen Relativo (RVOL)
3. Impulso Técnico (RSI)

El score final pondera cada pilar según su importancia para identificar
oportunidades de compra con alta probabilidad de éxito.

Autor: Crypto Monitor System
Versión: 1.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN DE PESOS Y PARÁMETROS
# =============================================================================

# Pesos de cada pilar en el score final (suman 1.0)
WEIGHTS = {
    'trend': 0.40,      # Tendencia del Precio - 40% (factor principal)
    'volume': 0.35,     # Volumen Relativo - 35% (confirmación de interés)
    'momentum': 0.25,   # Impulso Técnico (RSI) - 25% (timing de entrada)
}

# Parámetros de Medias Móviles
EMA_SHORT = 20      # EMA corta (corto plazo)
EMA_LONG = 50       # EMA larga (mediano plazo)
EMA_TREND = 50      # EMA tendencia (largo plazo - reducido de 200 para requerir menos datos)

# Parámetros de Volumen
VOLUME_LOOKBACK = 20    # Períodos para promedio de volumen
RVOL_THRESHOLD = 1.5    # Umbral mínimo RVOL para considerar "alto volumen"

# Parámetros RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 30       # Zona de sobreventa
RSI_OVERBOUGHT = 70     # Zona de sobrecompra
RSI_OPTIMAL_MIN = 40    # Mínimo zona óptima (rebote saludable)
RSI_OPTIMAL_MAX = 65    # Máximo zona óptima (antes de sobrecompra)


# =============================================================================
# FUNCIONES AUXILIARES DE CÁLCULO TÉCNICO
# =============================================================================

def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """
    Calcula la Media Móvil Exponencial (EMA).
    
    La EMA da más peso a precios recientes, reaccionando más rápido
    que la media móvil simple (SMA).
    
    Args:
        series: Serie de precios (generalmente 'close')
        period: Número de períodos para la EMA
        
    Returns:
        Serie con valores de EMA
    """
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula el Índice de Fuerza Relativa (RSI) usando el método de Wilder.
    
    El RSI mide la velocidad y cambio de movimientos de precios.
    Valores > 70 = sobrecompra, < 30 = sobreventa.
    
    Args:
        series: Serie de precios de cierre
        period: Períodos para cálculo (default 14)
        
    Returns:
        Serie con valores de RSI (0-100)
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    # Promedio móvil suavizado (método Wilder)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_rvol(volume: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Calcula el Volumen Relativo (RVOL).
    
    RVOL = Volumen Actual / Promedio Móvil de Volumen (lookback períodos)
    
    RVOL > 1.5 indica volumen anormalmente alto (interés institucional).
    RVOL < 0.5 indica volumen anormalmente bajo (falta de interés).
    
    Args:
        volume: Serie de volumen
        lookback: Períodos para calcular promedio histórico
        
    Returns:
        Serie con valores de RVOL
    """
    avg_volume = volume.rolling(window=lookback, min_periods=1).mean()
    rvol = volume / avg_volume.replace(0, np.nan)
    return rvol.fillna(1.0)  # Si no hay histórico, asumir RVOL = 1


def calculate_bollinger_bands(series: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Calcula las Bandas de Bollinger.
    
    Las Bandas de Bollinger consisten en:
    - Middle Band: SMA(period) - Media móvil simple
    - Upper Band: Middle Band + (std_dev * Desviación Estándar)
    - Lower Band: Middle Band - (std_dev * Desviación Estándar)
    - Bandwidth: (Upper - Lower) / Middle - Medida de volatilidad
    - %B: (Close - Lower) / (Upper - Lower) - Posición relativa del precio
    
    Fórmulas:
    - Middle = SMA(close, period)
    - Std = std(close, period)
    - Upper = Middle + (std_dev * Std)
    - Lower = Middle - (std_dev * Std)
    - Bandwidth = (Upper - Lower) / Middle
    - %B = (Close - Lower) / (Upper - Lower)
    
    Args:
        series: Serie de precios (generalmente 'close')
        period: Períodos para la media móvil (default 20)
        std_dev: Número de desviaciones estándar (default 2.0)
        
    Returns:
        Tupla con (middle, upper, lower, bandwidth, percent_b)
    """
    middle = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std()
    
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    # Bandwidth: medida de volatilidad relativa
    bandwidth = (upper - lower) / middle.replace(0, np.nan)
    
    # %B: posición del precio dentro de las bandas (0 = en lower, 1 = en upper, >1 = arriba, <0 = abajo)
    percent_b = (series - lower) / (upper - lower).replace(0, np.nan)
    
    return middle, upper, lower, bandwidth.fillna(0), percent_b.fillna(0.5)


def calculate_volume_profile(volume: pd.Series, close: pd.Series, lookback: int = 20) -> Dict:
    """
    Calcula métricas avanzadas de volumen.
    
    Métricas calculadas:
    - volume_sma: Media móvil simple de volumen
    - volume_ema: Media móvil exponencial de volumen
    - rvol: Volumen relativo (volumen actual / SMA volumen)
    - volume_trend: Pendiente de la EMA de volumen
    - up_volume: Volumen en días alcistas (close > open)
    - down_volume: Volumen en días bajistas (close < open)
    - volume_ratio: up_volume / down_volume (presión compradora vs vendedora)
    - vwap_approx: VWAP aproximado (suma(close*volume) / suma(volume)) últimos N períodos
    
    Args:
        volume: Serie de volumen
        close: Serie de precios de cierre
        lookback: Períodos para cálculos
        
    Returns:
        Diccionario con métricas de volumen
    """
    volume_sma = volume.rolling(window=lookback, min_periods=1).mean()
    volume_ema = volume.ewm(span=lookback, adjust=False).mean()
    rvol = volume / volume_sma.replace(0, np.nan)
    
    # Tendencia del volumen (pendiente EMA)
    volume_trend = volume_ema.diff()
    
    # Volumen en días verdes vs rojos (requiere open price, aproximamos con close vs close.prev)
    # Para análisis más preciso se necesitaría open price, aquí aproximamos
    price_change = close.diff()
    up_volume = volume.where(price_change > 0, 0).rolling(window=lookback, min_periods=1).sum()
    down_volume = volume.where(price_change < 0, 0).rolling(window=lookback, min_periods=1).sum()
    volume_ratio = up_volume / down_volume.replace(0, np.nan)
    
    # VWAP aproximado últimos lookback períodos
    vwap_numerator = (close * volume).rolling(window=lookback, min_periods=1).sum()
    vwap_denominator = volume.rolling(window=lookback, min_periods=1).sum()
    vwap_approx = vwap_numerator / vwap_denominator.replace(0, np.nan)
    
    return {
        'volume_sma': volume_sma.fillna(0),
        'volume_ema': volume_ema.fillna(0),
        'rvol': rvol.fillna(1.0),
        'volume_trend': volume_trend.fillna(0),
        'up_volume': up_volume.fillna(0),
        'down_volume': down_volume.fillna(0),
        'volume_ratio': volume_ratio.fillna(1.0),
        'vwap_approx': vwap_approx.fillna(close.iloc[-1] if len(close) > 0 else 0),
    }


def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula TODOS los indicadores técnicos en un DataFrame.
    
    Indicadores añadidos:
    - EMA: 20, 50, 100, 200
    - RSI: 14
    - Bollinger Bands: 20 período, 2 std dev (middle, upper, lower, bandwidth, %B)
    - Volume Profile: SMA, EMA, RVOL, trend, up/down volume, ratio, VWAP approx
    - MACD: 12, 26, 9 (opcional)
    
    Args:
        df: DataFrame con columnas 'open', 'high', 'low', 'close', 'volume'
        
    Returns:
        DataFrame con todas las columnas de indicadores añadidas
    """
    df = df.copy()
    
    # EMAs
    df['ema_20'] = calculate_ema(df['close'], 20)
    df['ema_50'] = calculate_ema(df['close'], 50)
    df['ema_100'] = calculate_ema(df['close'], 100)
    df['ema_200'] = calculate_ema(df['close'], 200)
    
    # RSI
    df['rsi_14'] = calculate_rsi(df['close'], 14)
    
    # Bollinger Bands
    bb_middle, bb_upper, bb_lower, bb_bandwidth, bb_percent_b = calculate_bollinger_bands(df['close'], 20, 2.0)
    df['bb_middle'] = bb_middle
    df['bb_upper'] = bb_upper
    df['bb_lower'] = bb_lower
    df['bb_bandwidth'] = bb_bandwidth
    df['bb_percent_b'] = bb_percent_b
    
    # Volume Profile
    vol_profile = calculate_volume_profile(df['volume'], df['close'], 20)
    df['volume_sma_20'] = vol_profile['volume_sma']
    df['volume_ema_20'] = vol_profile['volume_ema']
    df['rvol_20'] = vol_profile['rvol']
    df['volume_trend'] = vol_profile['volume_trend']
    df['up_volume_20'] = vol_profile['up_volume']
    df['down_volume_20'] = vol_profile['down_volume']
    df['volume_ratio_20'] = vol_profile['volume_ratio']
    df['vwap_20'] = vol_profile['vwap_approx']
    
    return df


# =============================================================================
# FUNCIONES DE SCORING POR PILAR
# =============================================================================

def score_trend(df: pd.DataFrame) -> Tuple[float, Dict]:
    """
    Evalúa la Tendencia del Precio (Pilar 1) - Peso 40%.
    
    Criterios de evaluación:
    1. EMA20 > EMA50 (tendencia alcista mediano plazo)
    2. Precio > EMA20 (precio respeta media corta)
    3. EMA50 > EMA200 (tendencia macro alcista) - FILTRO CRÍTICO
    4. Pendiente de EMA20 positiva (aceleración alcista)
    5. Separación entre EMAs (fuerza de tendencia)
    
    Args:
        df: DataFrame con columnas 'close', 'ema_20', 'ema_50', 'ema_200'
        
    Returns:
        Tupla (score 0-100, diccionario con detalles)
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    details = {}
    score = 0.0
    
    # 1. EMA20 > EMA50 (Tendencia alcista mediano plazo) - 25 puntos
    ema20_gt_ema50 = last['ema_20'] > last['ema_50']
    details['ema20_gt_ema50'] = bool(ema20_gt_ema50)
    if ema20_gt_ema50:
        score += 25
    
    # 2. Precio > EMA20 (Precio por encima de media corta) - 20 puntos
    price_gt_ema20 = last['close'] > last['ema_20']
    details['price_gt_ema20'] = bool(price_gt_ema20)
    if price_gt_ema20:
        score += 20
    
    # 3. EMA50 > EMA200 (Tendencia macro alcista) - 30 puntos [FILTRO CRÍTICO]
    ema50_gt_ema200 = last['ema_50'] > last['ema_200']
    details['ema50_gt_ema200'] = bool(ema50_gt_ema200)
    if ema50_gt_ema200:
        score += 30
    else:
        # Si no cumple tendencia macro, penalizar fuertemente
        score = max(0, score - 20)
    
    # 4. Pendiente EMA20 positiva (Aceleración) - 15 puntos
    ema20_slope = last['ema_20'] - prev['ema_20']
    ema20_rising = ema20_slope > 0
    details['ema20_rising'] = bool(ema20_rising)
    if ema20_rising:
        score += 15
    
    # 5. Separación EMAs (Fuerza de tendencia) - 10 puntos
    # Separación normalizada: (EMA20 - EMA50) / EMA50
    ema_separation = (last['ema_20'] - last['ema_50']) / last['ema_50']
    details['ema_separation_pct'] = round(ema_separation * 100, 2)
    if ema_separation > 0.02:  # > 2% separación
        score += 10
    elif ema_separation > 0:
        score += 5
    
    details['raw_score'] = round(score, 1)
    return min(100, max(0, score)), details


def score_volume(df: pd.DataFrame) -> Tuple[float, Dict]:
    """
    Evalúa Aceleración del Volumen Relativo (Pilar 2) - Peso 35%.
    
    Criterios:
    1. RVOL actual > 1.5 (volumen 50% arriba del promedio) - 40 pts
    2. RVOL en expansión (RVOL actual > RVOL anterior) - 20 pts
    3. Volumen en día alcista (close > open) - 20 pts
    4. RVOL sostenido > 1.0 en últimos 3 días - 20 pts
    
    Args:
        df: DataFrame con 'close', 'open', 'volume', 'rvol'
        
    Returns:
        Tupla (score 0-100, diccionario con detalles)
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    details = {}
    score = 0.0
    
    # 1. RVOL actual alto - 40 puntos
    current_rvol = last.get('rvol', 1.0)
    details['current_rvol'] = round(current_rvol, 2)
    
    if current_rvol >= 2.0:
        score += 40
    elif current_rvol >= 1.5:
        score += 30
    elif current_rvol >= 1.2:
        score += 20
    elif current_rvol >= 1.0:
        score += 10
    
    # 2. RVOL en expansión - 20 puntos
    prev_rvol = prev.get('rvol', 1.0)
    rvol_expanding = current_rvol > prev_rvol
    details['rvol_expanding'] = bool(rvol_expanding)
    if rvol_expanding:
        score += 20
    
    # 3. Volumen en día alcista (confirmación) - 20 puntos
    green_day = last['close'] > last['open']
    details['green_volume_day'] = bool(green_day)
    if green_day and current_rvol > 1.0:
        score += 20
    elif green_day:
        score += 10
    
    # 4. RVOL sostenido últimos 3 días - 20 puntos
    recent_rvol = df['rvol'].tail(3).mean() if 'rvol' in df.columns else 1.0
    details['avg_rvol_3d'] = round(recent_rvol, 2)
    if recent_rvol >= 1.5:
        score += 20
    elif recent_rvol >= 1.2:
        score += 15
    elif recent_rvol >= 1.0:
        score += 10
    
    details['raw_score'] = round(score, 1)
    return min(100, max(0, score)), details


def score_momentum(df: pd.DataFrame) -> Tuple[float, Dict]:
    """
    Evalúa Impulso Técnico RSI (Pilar 3) - Peso 25%.
    
    Zonas óptimas para entrada (evitando extremos):
    - RSI 40-50: Zona de acumulación / rebote saludable (MEJOR) - 100 pts
    - RSI 50-65: Momentum alcista moderado (BUENO) - 80 pts
    - RSI 30-40: Sobreventa, posible rebote (RIESGOSO) - 60 pts
    - RSI 65-75: Cerca de sobrecompra (PRECAUCIÓN) - 40 pts
    - RSI > 75: Sobrecompra extrema (EVITAR) - 10 pts
    - RSI < 30: Sobreventa extrema (MUY RIESGOSO) - 20 pts
    
    Bonus: RSI rising (momentum mejorando) +10 pts
    
    Args:
        df: DataFrame con columna 'rsi'
        
    Returns:
        Tupla (score 0-100, diccionario con detalles)
    """
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    
    details = {}
    current_rsi = last.get('rsi', 50)
    details['current_rsi'] = round(current_rsi, 1)
    
    # Score base según zona RSI
    if 40 <= current_rsi <= 50:
        score = 100      # Zona óptima: acumulación / pullback saludable
        zone = 'optimal_accumulation'
    elif 50 < current_rsi <= 65:
        score = 80       # Momentum alcista controlado
        zone = 'bullish_momentum'
    elif 30 <= current_rsi < 40:
        score = 60       # Rebotando desde sobreventa
        zone = 'oversold_bounce'
    elif 65 < current_rsi <= 75:
        score = 40       # Acercándose a sobrecompra
        zone = 'approaching_overbought'
    elif current_rsi > 75:
        score = 10       # Sobrecompra extrema - evitar
        zone = 'extreme_overbought'
    else:  # current_rsi < 30
        score = 20       # Sobreventa extrema - muy riesgoso
        zone = 'extreme_oversold'
    
    details['rsi_zone'] = zone
    
    # Bonus: RSI en ascenso (momentum mejorando)
    prev_rsi = prev.get('rsi', 50)
    rsi_rising = current_rsi > prev_rsi
    details['rsi_rising'] = bool(rsi_rising)
    if rsi_rising and current_rsi < 70:
        score = min(100, score + 10)
    
    # Penalización adicional si RSI > 80 (extremo)
    if current_rsi > 80:
        score = max(0, score - 20)
    
    details['raw_score'] = round(score, 1)
    return min(100, max(0, score)), details


# =============================================================================
# FUNCIÓN PRINCIPAL: ÍNDICE DE CONFLUENCIA
# =============================================================================

def calculate_confluence_index(df: pd.DataFrame) -> Dict:
    """
    Calcula el Índice de Confluencia Multicriterio completo.
    
    Combina tres pilares técnicos con pesos configurables:
    - Trend (40%): Alineación de EMAs y dirección de tendencia
    - Volume (35%): RVOL y confirmación de interés
    - Momentum (25%): RSI y timing de entrada
    
    Args:
        df: DataFrame con datos OHLCV (requiere: open, high, low, close, volume)
        
    Returns:
        Diccionario con:
        - confluence_score: Score final 0-100
        - pillar_scores: Scores individuales por pilar
        - pillar_details: Detalles de cada cálculo
        - signal: Clasificación textual (STRONG_BUY, BUY, WATCH, AVOID)
        - recommendation: Texto descriptivo
    """
    # Validar datos mínimos
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Columna requerida faltante: {col}")
    
    if len(df) < max(EMA_LONG, EMA_TREND, RSI_PERIOD, VOLUME_LOOKBACK) + 5:
        raise ValueError(f"Datos insuficientes. Mínimo {max(EMA_LONG, EMA_TREND, RSI_PERIOD, VOLUME_LOOKBACK) + 5} velas requeridas.")
    
    # Copia para no modificar original
    df = df.copy()
    
    # Calcular indicadores técnicos
    df['ema_20'] = calculate_ema(df['close'], EMA_SHORT)
    df['ema_50'] = calculate_ema(df['close'], EMA_LONG)
    df['ema_200'] = calculate_ema(df['close'], EMA_TREND)
    df['rsi'] = calculate_rsi(df['close'], RSI_PERIOD)
    df['rvol'] = calculate_rvol(df['volume'], VOLUME_LOOKBACK)
    
    # Calcular scores por pilar
    trend_score, trend_details = score_trend(df)
    volume_score, volume_details = score_volume(df)
    momentum_score, momentum_details = score_momentum(df)
    
    # Score final ponderado
    confluence_score = (
        trend_score * WEIGHTS['trend'] +
        volume_score * WEIGHTS['volume'] +
        momentum_score * WEIGHTS['momentum']
    )
    
    # Clasificación de señal
    if confluence_score >= 80:
        signal = 'STRONG_BUY'
        recommendation = 'Alta confluencia - Señal de compra fuerte'
    elif confluence_score >= 65:
        signal = 'BUY'
        recommendation = 'Buena confluencia - Señal de compra favorable'
    elif confluence_score >= 50:
        signal = 'WATCH'
        recommendation = 'Confluencia moderada - Vigilar para entrada'
    elif confluence_score >= 35:
        signal = 'WEAK'
        recommendation = 'Confluencia baja - No recomendado'
    else:
        signal = 'AVOID'
        recommendation = 'Confluencia negativa - Evitar'
    
    return {
        'confluence_score': round(confluence_score, 1),
        'signal': signal,
        'recommendation': recommendation,
        'pillar_scores': {
            'trend': round(trend_score, 1),
            'volume': round(volume_score, 1),
            'momentum': round(momentum_score, 1),
        },
        'pillar_weights': WEIGHTS,
        'pillar_details': {
            'trend': trend_details,
            'volume': volume_details,
            'momentum': momentum_details,
        },
        'indicators': {
            'ema_20': round(df['ema_20'].iloc[-1], 4),
            'ema_50': round(df['ema_50'].iloc[-1], 4),
            'ema_200': round(df['ema_200'].iloc[-1], 4),
            'rsi': round(df['rsi'].iloc[-1], 1),
            'rvol': round(df['rvol'].iloc[-1], 2),
        }
    }


def rank_cryptos_by_confluence(
    crypto_data: List[Dict],
    top_n: int = 10
) -> List[Dict]:
    """
    Rankea criptomonedas por su índice de confluencia y retorna el Top N.
    
    Args:
        crypto_data: Lista de dicts con datos OHLCV por símbolo.
                     Cada dict debe tener: 'symbol', 'df' (DataFrame OHLCV),
                     y opcionalmente 'base_data' con datos del ticker original
        top_n: Número de mejores resultados a retornar
        
    Returns:
        Lista ordenada (mayor a menor) de top_n criptomonedas con su análisis
    """
    results = []
    
    for item in crypto_data:
        symbol = item.get('symbol', 'UNKNOWN')
        df = item.get('df')
        base_data = item.get('base_data', {})
        
        if df is None or len(df) == 0:
            logger.warning(f"Sin datos para {symbol}, saltando...")
            continue
        
        try:
            result = calculate_confluence_index(df)
            result['symbol'] = symbol
            result['base_asset'] = symbol.replace('USDT', '')
            result['base_data'] = base_data  # Preservar datos base
            results.append(result)
        except Exception as e:
            logger.error(f"Error calculando confluencia para {symbol}: {e}")
            continue
    
    # Ordenar por score descendente
    results.sort(key=lambda x: x['confluence_score'], reverse=True)
    
    # Retornar top N
    return results[:top_n]


def prepare_klines_dataframe(klines: List[Dict]) -> pd.DataFrame:
    """
    Convierte datos de klines de Binance a DataFrame pandas optimizado.
    
    Args:
        klines: Lista de dicts con keys: time, open, high, low, close, volume
        
    Returns:
        DataFrame con columnas: open, high, low, close, volume
        Index: DatetimeIndex (UTC)
    """
    df = pd.DataFrame(klines)
    
    # Convertir timestamp a datetime
    df['timestamp'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df.set_index('timestamp', inplace=True)
    
    # Asegurar tipos numéricos
    numeric_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Eliminar filas con NaN
    df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
    
    # Ordenar por tiempo ascendente
    df = df.sort_index()
    
    return df[numeric_cols]


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == '__main__':
    # Ejemplo de uso con datos sintéticos
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=300, freq='1h')
    
    # Generar datos de prueba con tendencia alcista
    base_price = 50000
    trend = np.linspace(0, 0.15, 300)  # 15% subida en 300 períodos
    noise = np.random.normal(0, 0.02, 300)
    closes = base_price * (1 + trend + noise).cumprod()
    
    df = pd.DataFrame({
        'open': closes * (1 + np.random.normal(0, 0.001, 300)),
        'high': closes * (1 + np.abs(np.random.normal(0, 0.005, 300))),
        'low': closes * (1 - np.abs(np.random.normal(0, 0.005, 300))),
        'close': closes,
        'volume': np.random.lognormal(15, 0.5, 300)
    }, index=dates)
    
    # Asegurar high >= close >= low
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # Calcular índice
    result = calculate_confluence_index(df)
    
    print("=" * 60)
    print("ÍNDICE DE CONFLUENCIA MULTICRITERIO - RESULTADO")
    print("=" * 60)
    print(f"Símbolo: BTCUSDT (datos sintéticos)")
    print(f"Score Final: {result['confluence_score']}/100")
    print(f"Señal: {result['signal']}")
    print(f"Recomendación: {result['recommendation']}")
    print()
    print("Scores por Pilar:")
    for pillar, score in result['pillar_scores'].items():
        weight = result['pillar_weights'][pillar]
        print(f"  {pillar.capitalize():10} ({weight*100:.0f}%): {score}/100")
    print()
    print("Indicadores:")
    for k, v in result['indicators'].items():
        print(f"  {k}: {v}")
    print()
    print("Detalles Trend:", result['pillar_details']['trend'])
    print("Detalles Volume:", result['pillar_details']['volume'])
    print("Detalles Momentum:", result['pillar_details']['momentum'])