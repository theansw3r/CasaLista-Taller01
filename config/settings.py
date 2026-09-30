import os
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def variable(nombre: str, por_defecto: str = "") -> str:
    return os.getenv(nombre, por_defecto)


def lista(nombre: str, por_defecto: str = "") -> list[str]:
    crudo = variable(nombre, por_defecto)
    return [item.strip() for item in crudo.split(",") if item.strip()]


SECRET_KEY = variable("DJANGO_SECRET_KEY", "dev-inseguro-solo-para-desarrollo")
DEBUG = variable("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

DETRAS_DE_GATEWAY = variable("DJANGO_TRAS_GATEWAY", "0") == "1"
if DETRAS_DE_GATEWAY:
    USE_X_FORWARDED_HOST = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

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
    "corsheaders",
]

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
    "apps.comun.api.middleware.IdentificadorDePeticionMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "EXCEPTION_HANDLER": "apps.comun.api.manejador_errores.manejar_excepcion",
    "DEFAULT_PAGINATION_CLASS": "apps.comun.api.paginacion.PaginacionEstandar",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": variable("THROTTLE_ANON", "60/min"),
        "user": variable("THROTTLE_USER", "300/min"),
    },
}

SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer",),
    # Por defecto SimpleJWT vence el token a los 5 minutos, lo que obliga a
    # volver a entrar a mitad de una demostracion. Se alarga y se deja
    # configurable por entorno.
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=int(variable("JWT_HORAS", "8"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

CORS_ALLOWED_ORIGINS = lista(
    "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5500"
)
CORS_ALLOW_ALL_ORIGINS = DEBUG

NOTIFICADOR_TYPE = variable("NOTIFICADOR_TYPE", "MOCK")

TARIFA_TYPE = variable("TARIFA_TYPE", "BASE")

PASARELA_PAGO_TYPE = variable("PASARELA_PAGO_TYPE", "SIMULADA")

# Strangler de pagos. El microservicio (Flask) manda este token para
# confirmar reservas por /interno/. Vacio = nadie puede usar esa ruta.
TOKEN_SERVICIO_PAGOS = variable("TOKEN_SERVICIO_PAGOS", "")

# A donde paga el front. Con runserver sigue siendo el monolito (v1); en
# docker-compose se cambia a /api/v2/pagos/, que Nginx manda a Flask.
URL_PAGOS = variable("URL_PAGOS", "/api/v1/pagos/")

COMISION_PLATAFORMA = Decimal(variable("COMISION_PLATAFORMA", "0.12"))

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

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

    LOGGING["root"]["level"] = "CRITICAL"
    LOGGING["loggers"] = {"django.request": {"level": "CRITICAL"}}
