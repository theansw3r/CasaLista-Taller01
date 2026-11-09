# Microservicio de pagos (Flask). Se construye aparte del monolito.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY pagos/ pagos/
COPY locale/ locale/
COPY wsgi.py .

EXPOSE 5000

# Primero crea la tabla de pagos (si no existe) y despues arranca gunicorn.
CMD ["sh", "-c", "flask --app wsgi crear-tablas && gunicorn wsgi:app --bind 0.0.0.0:5000 --workers 2 --access-logfile -"]
