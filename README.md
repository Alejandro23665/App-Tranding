# 📊 Sistema de Monitoreo de Criptomonedas en Tiempo Real

> **Dashboard web minimalista** desarrollado con **Django** y **python-binance** para visualizar precios, volúmenes y estadísticas de mercado de las principales criptomonedas en tiempo real desde Binance.

---

## 🎯 Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Datos en Tiempo Real** | Conexión directa a Binance API usando `python-binance` (librería oficial) |
| **Interfaz Minimalista** | Django Templates + Tailwind CSS (via CDN) - Sin frameworks JS complejos |
| **Auto-actualización** | Refresh automático cada 30s + botón manual + soporte AJAX |
| **Indicadores Visuales** | Colores verde/rojo para cambios positivos/negativos, animaciones suaves |
| **Tarjetas Resumen** | Top 5 pares por volumen USDT con info clave a simple vista |
| **Configuración Segura** | Variables de entorno con `python-dotenv` (credenciales fuera del código) |
| **Health Check** | Endpoint `/health/` para monitoreo de infraestructura |
| **API JSON** | Endpoint `/api/ticker/` para integraciones externas |

---

## 🏗️ Arquitectura del Proyecto

```
trading/
├── crypto_monitor/          # Configuración principal de Django
│   ├── __init__.py
│   ├── settings.py          # Configuración completa (comentada línea a línea)
│   ├── urls.py              # Rutas principales
│   └── wsgi.py              # Entrada WSGI para producción
├── monitoring/              # App de monitoreo
│   ├── __init__.py
│   ├── apps.py              # Configuración de la app
│   ├── urls.py              # Rutas de la app (dashboard, API, health)
│   └── views.py             # Lógica de negocio + integración Binance
├── templates/
│   └── index.html           # Dashboard principal (Tailwind + JS vanilla)
├── static/                  # Archivos estáticos (vacío, usa CDN)
├── logs/                    # Logs de la aplicación (se crea automáticamente)
├── manage.py                # Script de gestión Django
├── requirements.txt         # Dependencias de producción
├── requirements-dev.txt     # Dependencias de desarrollo
├── .env.example             # Plantilla de variables de entorno
├── .env                     # Variables locales (NO versionar)
└── .gitignore               # Archivos ignorados por Git
```

---

## 📋 Requisitos Previos

- **Python 3.10+** (recomendado 3.11 o 3.12)
- **pip** (gestor de paquetes de Python)
- **Git** (para clonar el repositorio)
- **Cuenta en Binance** (opcional, solo para API keys con rate limits más altos)

---

## ⚙️ Instalación Paso a Paso

### 1. Clonar el repositorio

```bash
git clone <url-del-repositorio>
cd trading
```

### 2. Crear y activar entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Actualizar pip e instalar dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Para desarrollo:** `pip install -r requirements-dev.txt`

### 4. Configurar variables de entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar .env con tus valores
# (ver sección "Configuración de .env" abajo)
```

### 5. Aplicar migraciones de base de datos

```bash
python manage.py migrate
```

### 6. (Opcional) Crear superusuario para admin

```bash
python manage.py createsuperuser
```

### 7. Iniciar servidor de desarrollo

```bash
python manage.py runserver
```

### 8. Abrir en navegador

```
http://127.0.0.1:8000/
```

---

## 🔧 Configuración del Archivo `.env`

El archivo `.env` contiene **todas** las configuraciones sensibles y de entorno. **Nunca lo subas a Git.**

| Variable | Requerida | Descripción | Ejemplo |
|----------|-----------|-------------|---------|
| `DJANGO_SECRET_KEY` | ✅ Sí | Clave secreta de Django (generar nueva en producción) | `django-insecure-xyz123...` |
| `DJANGO_DEBUG` | No | Modo debug (`True`/`False`) | `True` |
| `ALLOWED_HOSTS` | No | Hosts permitidos (coma-separados) | `localhost,127.0.0.1,midominio.com` |
| `BINANCE_API_KEY` | No* | API Key de Binance (para rate limits altos) | `abc123...` |
| `BINANCE_API_SECRET` | No* | API Secret de Binance (endpoints privados) | `xyz789...` |

> **\* Nota:** Para datos públicos (precios, ticker 24h) **no son obligatorias**. La librería `python-binance` funciona sin credenciales para endpoints públicos. Se recomiendan para evitar límites de tasa (1200 req/min sin auth vs 6000+ con auth).

### Generar `DJANGO_SECRET_KEY` segura

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### Obtener credenciales de Binance

1. Inicia sesión en [Binance](https://www.binance.com)
2. Ve a **Perfil → API Management**
3. Crea nueva API Key
4. **Para solo lectura:** Deja "Enable Reading" activado, desactiva "Enable Spot & Margin Trading" y "Enable Futures"
5. Copia **API Key** y **Secret Key** a tu `.env`

---

## 🚀 Uso del Sistema

### Dashboard Principal (`/`)

- Tabla con **10 pares principales** (BTC, ETH, BNB, SOL, ADA, XRP, DOGE, MATIC, DOT, AVAX contra USDT)
- Columnas: Par, Precio, Cambio 24h (%), Máx/Mín 24h, Volumen, Volumen USDT, Trades
- **Verde** = subida, **Rojo** = bajada
- Tarjetas resumen (top 5 por volumen) arriba de la tabla
- Auto-refresh cada 30s (configurable via checkbox)

### Endpoints API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Dashboard HTML completo |
| `/api/ticker/` | GET | JSON con todos los tickers |
| `/health/` | GET | Health check (`{"status": "ok"}`) |

**Ejemplo respuesta `/api/ticker/`:**
```json
{
  "success": true,
  "data": [
    {
      "symbol": "BTCUSDT",
      "base_asset": "BTC",
      "quote_asset": "USDT",
      "last_price": 67432.15,
      "price_change": 1234.56,
      "price_change_percent": 1.86,
      "volume": 45231.12,
      "quote_volume": 3045678901.23,
      "high_price": 68100.00,
      "low_price": 65800.00,
      "open_price": 66197.59,
      "count": 1254321
    }
  ],
  "timestamp": "2026-10-03T15:30:45Z"
}
```

### Panel de Administración (`/admin/`)

Accede con el superusuario creado en el paso 6 para gestionar la base de datos Django.

---

## 🛠️ Desarrollo y Personalización

### Agregar/Modificar Pares Monitoreados

Edita `crypto_monitor/settings.py`:

```python
SYMBOLS_TO_MONITOR = [
    'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
    'XRPUSDT', 'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'AVAXUSDT',
    # Agrega más símbolos aquí (formato: BASEQUOTE)
]
```

### Cambiar Intervalo de Auto-refresh

En `templates/index.html`, busca:
```javascript
AUTO_REFRESH_MS: 30000,  // 30 segundos en milisegundos
```

### Personalizar Estilos (Tailwind)

El proyecto usa Tailwind via CDN con configuración extendida en `<script>` dentro de `index.html`. Para producción, compila Tailwind localmente:

```bash
npm init -y
npm install -D tailwindcss
npx tailwindcss init
# Configurar tailwind.config.js y compilar
```

### Agregar Logs a Archivo

Los logs se guardan en `logs/crypto_monitor.log` automáticamente (configurado en `settings.py`).

---

## 🧪 Testing

```bash
# Ejecutar tests (requiere requirements-dev.txt)
pytest

# Con cobertura
pytest --cov=monitoring --cov-report=html
```

---

## 📦 Despliegue en Producción

### Checklist de Seguridad

- [ ] `DJANGO_DEBUG=False` en `.env`
- [ ] `DJANGO_SECRET_KEY` única y segura
- [ ] `ALLOWED_HOSTS` configurado con tu dominio real
- [ ] `BINANCE_API_KEY/SECRET` configuradas (si usas endpoints privados)
- [ ] HTTPS habilitado (nginx + Certbot/Let's Encrypt)
- [ ] `SECURE_SSL_REDIRECT=True`, `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True` en settings
- [ ] Base de datos PostgreSQL/MySQL en lugar de SQLite
- [ ] `collectstatic` ejecutado y servido por nginx
- [ ] Gunicorn/uWSGI + systemd/Docker para proceso

### Ejemplo con Gunicorn + Nginx

```bash
# Instalar gunicorn
pip install gunicorn

# Ejecutar
gunicorn crypto_monitor.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

---

## 🔍 Solución de Problemas Comunes

| Problema | Solución |
|----------|----------|
| `ModuleNotFoundError: django` | Activa el entorno virtual y `pip install -r requirements.txt` |
| `ConnectionError` al cargar datos | Verifica internet, firewall, o si Binance bloquea tu IP |
| `403 Forbidden` en API Binance | Rate limit excedido. Agrega `BINANCE_API_KEY` al `.env` |
| `TemplateDoesNotExist` | Verifica que `templates/index.html` existe y `DIRS` en settings apunta a `BASE_DIR / 'templates'` |
| `CSRF verification failed` | Asegúrate de `{% csrf_token %}` en forms, o usa `@csrf_exempt` en APIs |
| Puerto 8000 ocupado | `python manage.py runserver 8001` o mata proceso en puerto 8000 |

---

## 📄 Licencia

Este proyecto es de código abierto bajo licencia **MIT**. Úsalo libremente para aprendizaje, proyectos personales o comerciales.

---

## 🤝 Contribuciones

1. Fork el repositorio
2. Crea rama: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Agrega nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre Pull Request

---

## 📞 Soporte

- **Issues**: Reporta bugs en el tracker de GitHub
- **Documentación Django**: https://docs.djangoproject.com/
- **Documentación python-binance**: https://python-binance.readthedocs.io/
- **API Binance**: https://binance-docs.github.io/apidocs/spot/en/

---

> **Desarrollado con ❤️ usando Django + python-binance + Tailwind CSS**