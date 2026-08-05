"""
Configuracion del proyecto CasaLista.

Todo lo que puede cambiar entre entornos se lee de variables de entorno.
Las claves NOTIFICADOR_TYPE y TARIFA_TYPE son las que alimentan a las
Factories de `reservas/infra/factories.py` (ver docs/wiki).
"""

import os
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-inseguro-solo-para-el-taller")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "reservas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/admin/login/"

# ---------------------------------------------------------------------------
# Configuracion conmutable por entorno (entradas de las Factories)
# ---------------------------------------------------------------------------
# MOCK  -> imprime la notificacion en consola (desarrollo / pruebas)
# REAL  -> envia el correo con el backend de email de Django
NOTIFICADOR_TYPE = os.getenv("NOTIFICADOR_TYPE", "MOCK")

# BASE      -> total = suma de subtotales congelados
# DINAMICA  -> aplica recargos por horario nocturno y fin de semana
TARIFA_TYPE = os.getenv("TARIFA_TYPE", "BASE")

# Comision de plataforma (modelo de ingresos, seccion 1.6 del Business Case)
COMISION_PLATAFORMA = Decimal(os.getenv("COMISION_PLATAFORMA", "0.12"))

EMAIL_BACKEND = os.getenv(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@casalista.co")
