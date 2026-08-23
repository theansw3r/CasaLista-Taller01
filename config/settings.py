"""
Configuracion del proyecto CasaLista.

Regla que se sigue en todo el archivo: cualquier valor que pueda cambiar entre
entornos (desarrollo, sustentacion, produccion) se lee de una variable de
entorno con un valor por defecto seguro para desarrollo. El codigo no se edita
para cambiar de entorno.

Las variables NOTIFICADOR_TYPE, TARIFA_TYPE y PASARELA_PAGO_TYPE son las
entradas de las Factories (ver docs/wiki/03-Patrones-Creacionales.md).
"""

import os
import sys
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def variable(nombre: str, por_defecto: str = "") -> str:
    return os.getenv(nombre, por_defecto)


def lista(nombre: str, por_defecto: str = "") -> list[str]:
    crudo = variable(nombre, por_defecto)
    return [item.strip() for item in crudo.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
SECRET_KEY = variable("DJANGO_SECRET_KEY", "dev-inseguro-solo-para-desarrollo")
DEBUG = variable("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# En produccion la aplicacion vive detras del API Gateway, que es quien termina
# TLS. Django tiene que confiar en las cabeceras que el Gateway le reenvia,
# porque de lo contrario construye mal las URLs absolutas.
DETRAS_DE_GATEWAY = variable("DJANGO_TRAS_GATEWAY", "0") == "1"
if DETRAS_DE_GATEWAY:
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
APPS_DE_DJANGO = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

APPS_DE_TERCEROS = [
    "rest_framework",
    "drf_spectacular",
    "corsheaders",
]

# Una app por modulo del modelo de dominio (seccion 3 del Business Case).
# El orden refleja la direccion de las dependencias: cuentas no conoce a nadie,
# catalogo conoce a cuentas, reservas conoce a los dos, pagos conoce a reservas.
# Nunca al reves.
APPS_DEL_PROYECTO = [
    "apps.cuentas",
    "apps.catalogo",
    "apps.reservas",
    "apps.pagos",
]

INSTALLED_APPS = APPS_DE_DJANGO + APPS_DE_TERCEROS + APPS_DEL_PROYECTO

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Propaga el identificador de correlacion que inyecta el Gateway.
    "apps.comun.api.middleware.IdentificadorDePeticionMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Base de datos
# ---------------------------------------------------------------------------
# SQLite por defecto para que el proyecto se levante sin instalar nada mas.
# Con DB_ENGINE=postgres la aplicacion cambia de motor sin tocar codigo. Es
# importante para el Builder: SELECT ... FOR UPDATE solo bloquea de verdad en
# PostgreSQL (ver 02-Arquitectura-por-Capas, seccion de concurrencia).
if variable("DB_ENGINE", "sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": variable("DB_NAME", "casalista"),
            "USER": variable("DB_USER", "casalista"),
            "PASSWORD": variable("DB_PASSWORD", ""),
            "HOST": variable("DB_HOST", "localhost"),
            "PORT": variable("DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internacionalizacion
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # JWT primero: es el mecanismo sin estado que el Gateway puede validar por
    # su cuenta. La sesion queda solo como comodidad para el navegador.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # Un unico punto traduce las excepciones de dominio a codigos HTTP. Gracias
    # a el las vistas no necesitan un solo try/except.
    "EXCEPTION_HANDLER": "apps.comun.api.manejador_errores.manejar_excepcion",
    "DEFAULT_PAGINATION_CLASS": "apps.comun.api.paginacion.PaginacionEstandar",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Limite de tasa provisional: en produccion lo asume el Gateway.
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": variable("THROTTLE_ANON", "60/min"),
        "user": variable("THROTTLE_USER", "300/min"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "CasaLista API",
    "DESCRIPTION": (
        "Marketplace de reserva de servicios profesionales para el hogar. "
        "Este esquema OpenAPI es el contrato que consume el API Gateway."
    ),
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1",
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# El Gateway se encarga de CORS en produccion; en desarrollo lo abrimos para
# poder probar el front end de la sustentacion desde otro puerto.
CORS_ALLOWED_ORIGINS = lista(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5500"
)
CORS_ALLOW_ALL_ORIGINS = DEBUG

# ---------------------------------------------------------------------------
# Entradas de las Factories
# ---------------------------------------------------------------------------
# MOCK -> imprime la notificacion en consola | REAL -> envia correo
NOTIFICADOR_TYPE = variable("NOTIFICADOR_TYPE", "MOCK")

# BASE -> suma de subtotales | DINAMICA -> recargo nocturno y de fin de semana
TARIFA_TYPE = variable("TARIFA_TYPE", "BASE")

# SIMULADA -> aprueba siempre (desarrollo) | TARJETA / PSE -> adaptadores reales
PASARELA_PAGO_TYPE = variable("PASARELA_PAGO_TYPE", "SIMULADA")

# ---------------------------------------------------------------------------
# Reglas de negocio parametrizables (Business Case 1.6 y RN-04)
# ---------------------------------------------------------------------------
COMISION_PLATAFORMA = Decimal(variable("COMISION_PLATAFORMA", "0.12"))

# RN-04: ventanas de cancelacion y porcentaje retenido en cada una.
HORAS_CANCELACION_SIN_PENALIZACION = int(variable("HORAS_CANCELACION_LIBRE", "24"))
HORAS_CANCELACION_PENALIZACION_PARCIAL = int(variable("HORAS_CANCELACION_PARCIAL", "2"))
PENALIZACION_PARCIAL = Decimal(variable("PENALIZACION_PARCIAL", "0.30"))

EMAIL_BACKEND = variable(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = variable("DEFAULT_FROM_EMAIL", "no-reply@casalista.co")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "casalista": {"format": "[{levelname}] {name}: {message}", "style": "{"},
    },
    "handlers": {
        "consola": {"class": "logging.StreamHandler", "formatter": "casalista"},
    },
    "root": {"handlers": ["consola"], "level": variable("LOG_LEVEL", "INFO")},
}

# ---------------------------------------------------------------------------
# Ajustes que solo aplican mientras corre la suite de pruebas
# ---------------------------------------------------------------------------
if "test" in sys.argv:
    # El hash por defecto (PBKDF2) es lento a proposito. Las pruebas crean
    # decenas de usuarios, y una suite que tarda medio minuto deja de
    # correrse. La seguridad real no depende de este ajuste.
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    # Sin esto, una prueba que hace 60 peticiones seguidas empieza a recibir
    # 429 y falla por una razon que no tiene que ver con lo que comprueba.
    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

    # Las pruebas provocan errores a proposito. Sus logs no son informacion,
    # son ruido que tapa el resultado real de la suite.
    LOGGING["root"]["level"] = "CRITICAL"
    LOGGING["loggers"] = {"django.request": {"level": "CRITICAL"}}
