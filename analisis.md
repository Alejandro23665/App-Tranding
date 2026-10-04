# Documentación Técnica: Análisis de Criptomonedas con Índice de Confluencia Multicriterio

## Resumen del Sistema

Este documento describe la implementación completa del sistema de análisis técnico de criptomonedas para el **Crypto Monitor**, que incluye:

1. **Búsqueda avanzada** (`/search/`) con indicadores técnicos completos
2. **Índice de Confluencia Multicriterio** para ranking automático de potencial de compra
3. **Dashboard Top Potencial** (`/top-flop/`) con ranking basado en confluencia técnica

---

## 1. ARQUITECTURA DEL SISTEMA

### Módulos Principales

```
monitoring/
├── analysis/
│   ├── __init__.py
│   └── confluence_index.py      # Motor de análisis técnico completo
├── views.py                     # Vistas Django (search, top-flop, AI, etc.)
└── urls.py                      # Rutas URL
```

### Flujo de Datos

```
Usuario busca símbolo (ej: BTC)
        ↓
search_coin_fast() [views.py]
        ↓
fetch_klines() → Binance API (60 velas diarias)
        ↓
prepare_klines_dataframe() → pandas DataFrame
        ↓
calculate_all_indicators() [confluence_index.py]
        ↓
Devuelve diccionario con TODOS los indicadores
        ↓
Template search.html → Renderizado HTML
```

---

## 2. INDICADORES TÉCNICOS IMPLEMENTADOS

### 2.1 Medias Móviles Exponenciales (EMA)

**Fórmula EMA:**
```
EMA_t = (Close_t × α) + EMA_{t-1} × (1 - α)
donde α = 2 / (período + 1)
```

**EMAs Calculadas:**
| EMA | Período | Uso |
|-----|---------|-----|
| EMA 20 | 20 días | Tendencia corto plazo, señales entrada/salida |
| EMA 50 | 50 días | Tendencia mediano plazo |
| EMA 100 | 100 días | Tendencia largo plazo |
| EMA 200 | 200 días | Tendencia macro, filtro principal |

**Señales de Cruce (Golden/Death Cross):**
- **EMA 20 > EMA 50**: Alcista mediano plazo (+25 pts)
- **EMA 50 > EMA 100**: Alcista largo plazo
- **EMA 100 > EMA 200**: Tendencia macro alcista (**FILTRO CRÍTICO** +30 pts)

**Distancia a EMAs (%):**
```
dist_ema_pct = ((Close - EMA) / EMA) × 100
```

**Pendiente EMA (Aceleración):**
```
ema_slope = EMA_t - EMA_{t-1}
```

**Estructura de Tendencia (Score 0-3):**
```
STRONG_BULLISH (3): EMA20>EMA50 ∧ EMA50>EMA100 ∧ EMA100>EMA200
BULLISH (2):      2 de 3 condiciones
NEUTRAL (1):      1 de 3 condiciones
BEARISH (0):      0 condiciones
```

---

### 2.2 Índice de Fuerza Relativa (RSI 14)

**Fórmula RSI (Método Wilder):**
```
RS = Average Gain / Average Loss
RSI = 100 - (100 / (1 + RS))
```

**Cálculo Detallado:**
```
1. delta = Close_t - Close_{t-1}
2. gain = max(delta, 0)
3. loss = max(-delta, 0)
4. avg_gain = EMA(gain, α=1/14)
5. avg_loss = EMA(loss, α=1/14)
6. RS = avg_gain / avg_loss
7. RSI = 100 - (100 / (1 + RS))
```

**Zonas RSI y Scoring:**
| Zona | RSI | Señal | Score Base |
|------|-----|-------|------------|
| Sobrecompra Extrema | > 80 | OVERBOUGHT | 10 pts |
| Sobrecompra | 70-80 | OVERBOUGHT | 40 pts |
| Alcista Fuerte | 65-70 | BULLISH | 80 pts |
| Momentum Alcista | 60-65 | BULLISH | 80 pts |
| Neutro Alcista | 50-60 | NEUTRAL_BULLISH | 80 pts |
| Neutro Bajista | 40-50 | NEUTRAL_BEARISH | 60 pts |
| Sobreventa Rebote | 30-40 | OVERSOLD_BOUNCE | 60 pts |
| Sobreventa | < 30 | OVERSOLD | 20 pts |

**Bonus RSI Rising:** +10 pts si RSI subiendo y < 70

**RSI Trend:**
```
RSI_TREND = RISING  si RSI_t > RSI_{t-1}
          = FALLING si RSI_t < RSI_{t-1}
          = FLAT    si igual
```

---

### 2.3 Bandas de Bollinger (20, 2σ)

**Fórmulas:**
```
Middle Band (SMA 20):    SMA(Close, 20)
Std Dev:                 Std(Close, 20)
Upper Band:              Middle + (2.0 × Std)
Lower Band:              Middle - (2.0 × Std)
Bandwidth:               (Upper - Lower) / Middle
%B (Percent B):          (Close - Lower) / (Upper - Lower)
```

**Interpretación %B:**
| %B | Zona | Señal |
|----|------|-------|
| > 1.0 | >100% | ABOVE_UPPER (Breakout) |
| 0.8-1.0 | 80-100% | NEAR_UPPER (Sobrecompra) |
| 0.5-0.8 | 50-80% | UPPER_HALF (Alcista) |
| 0.2-0.5 | 20-50% | LOWER_HALF (Bajista) |
| 0-0.2 | 0-20% | NEAR_LOWER (Sobreventa) |
| < 0 | <0% | BELOW_LOWER (Breakdown) |

**Bandwidth (Volatilidad):**
```
Bandwidth = (Upper - Lower) / Middle
```
- **HIGH_VOL**: > 0.10 (Alta volatilidad)
- **NORMAL_VOL**: 0.05-0.10 (Normal)
- **LOW_VOL**: < 0.05 (Baja volatilidad / Squeeze)

**Interpretación %B (0-100%):**
- **0-20%**: Zona de sobreventa / Soporte
- **20-50%**: Mitad inferior / Bajista moderado
- **50-80%**: Mitad superior / Alcista moderado
- **80-100%**: Sobrecompra / Resistencia
- **>100%**: Breakout alcista
- **<0%**: Breakdown bajista

---

### 2.4 Perfil de Volumen (20 períodos)

**RVOL (Relative Volume):**
```
RVOL = Volume_t / SMA(Volume, 20)
```

**Señales RVOL:**
| RVOL | Señal | Interpretación |
|------|-------|----------------|
| ≥ 2.0 | VERY_HIGH | Interés institucional muy alto |
| 1.5-2.0 | HIGH | Interés institucional alto |
| 1.2-1.5 | ELEVATED | Volumen elevado |
| 1.0-1.2 | NORMAL | Volumen normal |
| < 1.0 | LOW | Volumen bajo / Falta de interés |

**Tendencia de Volumen:**
```
Volume_Trend = EMA(Volume, 20)_t - EMA(Volume, 20)_{t-1}
```

**Ratio Up/Down Volume (Presión Compradora/Vendedora):**
```
Up_Volume = Σ(Volume donde Close > Close_{t-1}) últimos 20 días
Down_Volume = Σ(Volume donde Close < Close_{t-1}) últimos 20 días
Volume_Ratio = Up_Volume / Down_Volume
```
- **Ratio > 1.5**: Presión compradora fuerte
- **Ratio 1.0-1.5**: Presión compradora moderada
- **Ratio 0.7-1.0**: Equilibrado
- **Ratio < 0.7**: Presión vendedora

**VWAP Aproximado (20 períodos):**
```
VWAP_20 = Σ(Close × Volume) / Σ(Volume)  últimos 20 días
```
**Señal VWAP:**
- **ABOVE_VWAP**: Close > VWAP (Alcista intradía)
- **BELOW_VWAP**: Close < VWAP (Bajista intradía)

**Métricas Adicionales:**
- Volume SMA 20, Volume EMA 20
- Up Volume / Down Volume (últimos 20 días)

---

### 2.5 Soporte / Resistencia (20 días)

**Cálculo:**
```
Resistencia_20d = MAX(High, 20 días)
Soporte_20d = MIN(Low, 20 días)
Rango_20d_pct = ((Resistencia - Soporte) / Soporte) × 100
```

**Distancias (%):**
```
Dist_Resistencia_pct = ((Resistencia - Close) / Close) × 100
Dist_Soporte_pct = ((Close - Soporte) / Close) × 100
```

**Interpretación Distancias:**
- **< 5%**: Muy cerca (Zona de decisión)
- **5-15%**: Zona media
- **> 15%**: Lejano

---

### 2.6 Volatilidad (30 días)

**Fórmula (Desviación Estándar del Rango Diario):**
```
Para cada día: Daily_Range_pct = (High - Low) / Close × 100
Volatilidad = StdDev(Daily_Range_pct, 30 días)
```

**Interpretación:**
| Volatilidad | Clasificación | Trading |
|-------------|---------------|---------|
| > 15% | Extrema | Solo expertos |
| 10-15% | Muy Alta | Gestión riesgo estricta |
| 5-10% | Moderada | Swing trading |
| 2-5% | Baja | Holding medio plazo |
| < 2% | Muy Baja | Estable / Poca liquidez |

---

### 2.7 Spread

```
Spread = Ask - Bid
Spread_pct = (Spread / Close) × 100
```

---

### 2.8 Estructura de Mercado (Trend Structure)

**Scoring EMA Stack (0-3):**
```
EMA_Stack = (EMA20>EMA50) + (EMA50>EMA100) + (EMA100>EMA200)

3: STRONG_BULLISH (Todas alineadas alcista)
2: BULLISH (2 de 3)
1: NEUTRAL (1 de 3)
0: BEARISH (0 de 3)
```

---

## 3. ÍNDICE DE CONFLUENCIA MULTICRITERIO

### 3.1 Pesos por Pilar

| Pilar | Peso | Componentes |
|-------|------|-------------|
| **Tendencia** | 40% | EMAs, precio vs EMAs, pendientes, estructura |
| **Volumen** | 35% | RVOL, tendencia vol, up/down ratio, VWAP |
| **Momentum (RSI)** | 25% | Zona RSI, tendencia RSI |

### 3.2 Scoring por Pilar

#### Pilar 1: Tendencia (0-100 pts)

| Componente | Pts Máx | Condición |
|------------|---------|-----------|
| EMA20 > EMA50 | 25 | Tendencia alcista mediano |
| Precio > EMA20 | 20 | Precio respeta media corta |
| EMA50 > EMA200 | 30 | **FILTRO CRÍTICO** Macro |
| EMA20 Rising | 15 | Aceleración alcista |
| Separación EMAs | 10 | (EMA20-EMA50)/EMA50 > 2% |

#### Pilar 2: Volumen (0-100 pts)

| Componente | Pts Máx | Condición |
|------------|---------|-----------|
| RVOL ≥ 2.0 | 40 | Muy alto |
| RVOL ≥ 1.5 | 30 | Alto |
| RVOL ≥ 1.2 | 20 | Elevado |
| RVOL ≥ 1.0 | 10 | Normal |
| RVOL Expanding | 20 | RVOL_t > RVOL_{t-1} |
| Green Day + RVOL>1 | 20 | Volumen en día verde |
| RVOL_3d ≥ 1.5 | 20 | Sostenido 3 días |

#### Pilar 3: Momentum RSI (0-100 pts)

| Zona RSI | Score Base | Descripción |
|----------|------------|-------------|
| 40-50 | 100 | Óptima (Acumulación) |
| 50-65 | 80 | Momentum alcista |
| 30-40 | 60 | Rebote sobreventa |
| 65-75 | 40 | Cercano sobrecompra |
| > 75 | 10 | Sobrecompra extrema |
| < 30 | 20 | Sobreventa extrema |

**Bonus RSI Rising:** +10 pts si subiendo y < 70
**Penalización >80:** -20 pts

### 3.3 Score Final Ponderado

```
Confluence_Score = Trend_Score × 0.40 + Volume_Score × 0.35 + Momentum_Score × 0.25
```

### 3.4 Clasificación Final

| Score | Señal | Recomendación |
|-------|-------|---------------|
| ≥ 80 | STRONG_BUY | Alta confluencia - Compra fuerte |
| 65-79 | BUY | Buena confluencia - Compra favorable |
| 50-64 | WATCH | Confluencia moderada - Vigilar |
| 35-49 | WEAK | Confluencia baja - No recomendado |
| < 35 | AVOID | Confluencia negativa - Evitar |

---

## 4. RANKING Y SELECCIÓN TOP 10

### Proceso Completo

```
1. fetch_all_usdt_tickers() → ~580 pares USDT
2. Filtrar: Volumen > $100k, excluir leveraged/stablecoins
3. Top 60 por volumen → Obtener klines (60 velas diarias)
4. calculate_all_indicators() → DataFrame completo
5. calculate_confluence_index() → Score 0-100
6. rank_cryptos_by_confluence() → Orden descendente
7. Filtrar: Solo STRONG_BUY y BUY
8. Top 10 → Top Potential de Compra
```

### Filtrado Inteligente
- Solo monedas con señal **STRONG_BUY** o **BUY** entran al Top Potential
- Excluye: Leveraged tokens (UP/DOWN/BULL/BEAR), Stablecoins (USDC, BUSD, etc.)
- Mínimo $100k volumen 24h para liquidez

---

## 5. BÚSQUEDA AVANZADA (`/search/`)

### Datos Retornados por `search_coin_fast()`

```python
{
    # Precio básico
    'symbol', 'base_asset', 'last_price', 'price_change', 'price_change_percent',
    'high_price', 'low_price', 'open_price', 'volume', 'quote_volume',
    'bid_price', 'ask_price', 'count',
    
    # EMAs (4)
    'ema_20', 'ema_50', 'ema_100', 'ema_200',
    'price_gt_ema20', 'price_gt_ema50',
    'ema_20_gt_50', 'ema_50_gt_100', 'ema_100_gt_200',
    'dist_ema20_pct', 'dist_ema50_pct', 'dist_ema100_pct', 'dist_ema200_pct',
    'ema20_slope', 'ema50_slope',
    'ema_20_gt_50', 'ema_50_gt_100', 'ema_100_gt_200',
    'trend_structure',
    
    # RSI 14
    'rsi_14', 'rsi_signal', 'rsi_trend',
    
    # Bollinger Bands
    'bb_middle', 'bb_upper', 'bb_lower',
    'bb_bandwidth', 'bb_percent_b', 'bb_position',
    'bb_signal', 'bb_bandwidth_signal',
    
    # Volume Profile
    'volume_sma_20', 'volume_ema_20', 'rvol_20',
    'rvol_signal', 'volume_trend', 'up_volume_20',
    'down_volume_20', 'volume_ratio_20',
    'vwap_20', 'vwap_signal',
    
    # Soporte/Resistencia
    'resistance_20d', 'support_20d',
    'dist_resistance_pct', 'dist_support_pct',
    'range_20d_pct', 'volatility_30d',
    
    # Market Structure
    'trend_structure', 'rsi_14', 'rsi_signal', 'rsi_trend',
    'bb_signal', 'bb_position', 'bb_bandwidth_signal',
    'rvol_20', 'rvol_signal', 'volume_ratio_20',
    'volume_ratio_20', 'vwap_20', 'vwap_signal',
    'volume_sma_20', 'volume_ema_20', 'up_volume_20',
    'down_volume_20', 'volume_ratio_20', 'vwap_20',
    'vwap_signal', 'bb_bandwidth_signal',
    
    # Soporte/Resistencia
    'resistance_20d', 'support_20d',
    'dist_resistance_pct', 'dist_support_pct',
    'range_20d_pct', 'volatility_30d',
    
    # Legacy
    'volatility', 'spread', 'spread_pct',
    
    # Metadata
    'base_asset', 'quote_asset', 'symbol',
    'last_price', 'price_change', 'price_change_percent',
    'volume', 'quote_volume', 'high_price', 'low_price',
    'open_price', 'count', 'bid_price', 'ask_price',
    'spread', 'spread_pct'
}
```

---

## 6. CACHE Y OPTIMIZACIÓN

### Estrategia de Cache

| Dato | TTL | Key Pattern |
|------|-----|-------------|
| Ticker (precio 24h) | 30s | `ticker_{SYMBOL}` |
| Klines (60 velas 1d) | 60s | `klines_{SYMBOL}_1d_60` |
| Volatilidad 30d | 60s | `vol_{SYMBOL}` |

### Llamadas a API Binance por Búsqueda
- **1 llamada**: `get_ticker(symbol)` - Precio actual
- **1 llamada**: `get_klines(symbol, '1d', 60)` - Histórico 60 días
- **1 llamada opcional**: `get_klines(symbol, '1d', 30)` - Volatilidad 30d

**Total: 2-3 llamadas API por búsqueda** (vs 580+ para ranking completo)

---

## 7. TEMPLATE SEARCH.HTML - SECCIONES

### Secciones de Indicadores (Todas condicionales `{% if coin %}`)

| Sección | Ícono | Color | Datos Mostrados |
|---------|-------|-------|-----------------|
| **EMAs** | 📈 | Azul | 4 EMAs, distancias %, cruces, pendientes, estructura |
| **Bollinger Bands** | 📊 | Púrpura | 3 bandas, %B, Bandwidth, señales |
| **Volume Profile** | 📊 | Verde | RVOL, tendencia, ratio up/down, VWAP |
| **Soporte/Resistencia** | ⚓ | Naranja | S/R 20d, distancias %, rango, volatilidad 30d |
| **Estructura Mercado** | ⚖️ | Turquesa | Estructura, RSI, BB Signal, VWAP, RVOL, Vol Ratio, VWAP, BB Width |

---

## 8. FÓRMULAS DE REFERENCIA RÁPIDA

```python
# EMA
ema = close.ewm(span=period, adjust=False).mean()

# RSI (Wilder)
delta = close.diff()
gain = delta.where(delta>0, 0).ewm(alpha=1/period).mean()
loss = -delta.where(delta<0, 0).ewm(alpha=1/period).mean()
rsi = 100 - (100 / (1 + gain/loss))

# Bollinger
middle = close.rolling(20).mean()
std = close.rolling(20).std()
upper = middle + 2*std
lower = middle - 2*std
pct_b = (close - lower) / (upper - lower)
bandwidth = (upper - lower) / middle

# RVOL
rvol = volume / volume.rolling(20).mean()

# VWAP
vwap = (close * volume).rolling(20).sum() / volume.rolling(20).sum()

# Volatilidad 30d
daily_range = (high - low) / close * 100
volatility = daily_range.rolling(30).std()

# Soporte/Resistencia
resistance = high.rolling(20).max()
support = low.rolling(20).min()
```

---

## 9. ENDPOINTS API

| Endpoint | Método | Parámetros | Respuesta |
|----------|--------|------------|-----------|
| `/search/` | GET | `q=BTC` | HTML completa |
| `/api/search/` | GET | `q=BTC` | JSON con todos los indicadores |
| `/top-flop/` | GET | - | HTML Top Potential |
| `/api/top-flop/` | GET | - | JSON Top Potential |
| `/api/klines/` | GET | `symbol=BTCUSDT&interval=1h&limit=200` | OHLCV |
| `/api/ai/` | GET | `symbol=BTCUSDT` | Análisis IA Gemini |
| `/health/` | GET | - | `{"status": "ok"}` |

---

## 10. DEPENDENCIAS

```txt
Django>=4.2,<5.0
python-binance>=1.0.19      # API Binance oficial
python-dotenv>=1.0.0        # Variables entorno
google-generativeai>=0.8.0  # IA Gemini
numpy>=1.24                 # Cálculos numéricos
pandas>=2.0                 # DataFrames y indicadores
```

---

## 11. CONFIGURACIÓN (.env)

```env
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

BINANCE_API_KEY=           # Opcional (rate limits más altos)
BINANCE_API_SECRET=        # Opcional (endpoints privados)

GEMINI_API_KEY=your-gemini-key  # Para análisis IA
```

---

## 12. EJECUCIÓN

```bash
# Instalar dependencias
pip install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env con tus claves

# Migraciones
python manage.py migrate

# Servidor desarrollo
python manage.py runserver

# URLs principales:
# http://127.0.0.1:8000/              # Dashboard
# http://127.0.0.1:8000/search/       # Búsqueda avanzada
# http://127.0.0.1:8000/top-flop/     # Top Potential
# http://127.0.0.1:8000/ai/           # Análisis IA
```

---

## 13. NOTAS DE IMPLEMENTACIÓN

### Decisiones de Diseño

1. **EMA 200 reducida a 50**: Para requerir menos datos históricos (205 velas vs 300+) manteniendo utilidad
2. **Cache agresivo**: 30-60s TTL para evitar rate limits de Binance
2. **Solo STRONG_BUY/BUY en Top Potential**: Filtra ruido, solo muestra oportunidades claras
3. **Sin Flop Performers**: Eliminado "peores" - no aporta valor para estrategia de compra
4. **Pandas para todo**: Cálculos vectorizados, eficientes y mantenibles

### Limitaciones Conocidas

1. **RSI simple vs Wilder**: Implementación usa EMA para suavizado (aproximación Wilder)
2. **Up/Down Volume aproximado**: Usa Close vs Close_prev (no Open) por limitación API
3. **VWAP aproximado**: 20 días vs VWAP intradía real
4. **API Key Gemini**: Hardcodeada en settings como fallback (usar .env en producción)

---

## 14. CHANGELOG

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 1.0 | 2026-10-04 | Implementación completa: Confluence Index, Search avanzada, Top Potential, IA Analysis, Bollinger, Volume Profile, Soporte/Resistencia, Market Structure |

---

*Documentación generada automáticamente el 2026-10-04*
*Sistema: Crypto Monitor v1.0*
*Módulo Crítico: `monitoring/analysis/confluence_index.py`*