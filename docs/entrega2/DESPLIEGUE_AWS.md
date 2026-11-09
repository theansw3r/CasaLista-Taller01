# Despliegue en AWS Academy: procedimiento pendiente de ejecución

El usuario confirma que **todavía no existe una instancia CasaLista**.
No hay IP elástica, ID de EC2 ni evidencia de despliegue. Este procedimiento no
sustituye la ejecución y las capturas reales en el laboratorio.

## Acceso y creación

1. Abrir el Learner Lab de AWS Academy y comprobar sesión, presupuesto, región,
   cuotas y tipos de instancia permitidos. No usar una cuenta AWS personal.
2. Inventariar recursos existentes del laboratorio para no alterar otras tareas.
   Elegir la imagen Linux y capacidad después de esa inspección, documentando
   la elección. El sistema probado usa imágenes Docker oficiales; la arquitectura
   de CPU debe ser compatible con todas ellas.
3. Crear la instancia CasaLista con disco persistente y acceso administrable;
   mantener la clave privada fuera del repositorio. Permitir el gateway por el
   puerto acordado y acceso administrativo restringido. PostgreSQL, Redis,
   Django y Flask no necesitan puertos publicados en EC2.
4. Asignar una IP elástica de la región del laboratorio y asociarla a la instancia.
   Registrar la asociación real; una IP pública temporal no prueba este requisito.
   Consultar [Elastic IP de EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/elastic-ip-addresses-eip.html).
5. Instalar Docker Engine y Compose según el sistema operativo elegido, desde
   la [documentación oficial de Docker](https://docs.docker.com/engine/install/).
   Para Ubuntu, usar [el repositorio oficial](https://docs.docker.com/engine/install/ubuntu/).

## Arranque de una instalación nueva

Una vez integrada y publicada la versión probada en main:

```bash
git clone --branch main https://github.com/theansw3r/CasaLista-Taller01.git
cd CasaLista-Taller01
python3 scripts/preparar_entorno.py
```

El generador crea secretos sin imprimirlos y no sobrescribe un .env existente.
Editar localmente .env: DJANGO_ALLOWED_HOSTS debe contener la IP elástica real
(sin esquema ni puerto); CSRF_TRUSTED_ORIGINS debe contener el origen real
completo. Compose añade siempre el host interno `django`.
Para publicar Nginx por HTTP en el laboratorio: GATEWAY_BIND=0.0.0.0 y
GATEWAY_PORT=80. El puerto local por defecto es 127.0.0.1:8080.
No copiar secretos a la Wiki ni a capturas. DB_PASSWORD generado es hexadecimal
para poder usarse en la URL de conexión de Flask.

```bash
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
docker compose exec nginx nginx -t
docker compose exec django python manage.py check
docker compose exec django python manage.py createsuperuser
```

Usar `sembrar_demo` solo en la instalación académica destinada a datos ficticios;
crea cuentas con contraseña pública y datos de demostración. No ejecutarlo sobre
una instalación con usuarios reales. No usar `--reiniciar`.
El backend de correo predeterminado es consola: prueba la tarea, no la recepción
real. Para probar SMTP configurar DJANGO_EMAIL_BACKEND, EMAIL_HOST/PORT,
EMAIL_HOST_USER/PASSWORD, EMAIL_USE_TLS y DEFAULT_FROM_EMAIL en .env.
No se configura TLS público sin conocer dominio/certificado: antes de utilizar
credenciales o datos reales, habilitar HTTPS en el gateway y ajustar los orígenes.

## Verificación y evidencia real

Desde fuera de EC2: abrir la IP elástica, cambiar ES/EN, iniciar sesión de demo,
reservar y pagar por v2. Verificar respuesta propia JSON y tercero; cuando esté
identificado, comprobar también el aliado. Guardar capturas fechadas de EC2
Running, asociación de IP elástica, gateway y tareas. Ocultar identificadores de
cuenta y credenciales que no sean necesarios para la entrega.

Con AWS CLI autorizado en la sesión del laboratorio, `scripts/registrar_aws.py`
solo lee estado/asociación y falla si no hay instancia Running con EIP. Usar
sus argumentos reales; no se incluyen valores de ejemplo que parezcan evidencia.
Ejecutar luego `scripts/verificar_http.py --base <origen-real> --salida <archivo>`
sin `--datos-demo-locales` para lecturas públicas. El script de fallos es solo
local: no detiene servicios de la sustentación.

Para cerrar: registrar SHA de main desplegado, fecha, región, ID de instancia,
EIP y asociación; URLs verificadas, estados HTTP, tareas y commits por integrante.
Mantener la instancia encendida durante la sustentación, según la rúbrica.

## Datos y actualizaciones

Antes de modificar una instalación existente, preservar .env y usar las mismas
credenciales y el mismo nombre del proyecto Compose. Cambiar POSTGRES_PASSWORD
en .env **no cambia** la contraseña de un volumen ya inicializado.
Respaldar ambas bases con permisos privados, sin subir respaldos al repositorio:

```bash
umask 077
mkdir -p respaldos
docker compose exec -T db pg_dump -U casalista -Fc casalista > respaldos/casalista.dump
docker compose exec -T db pg_dump -U casalista -Fc casalista_pagos > respaldos/pagos.dump
```

Validar los dumps con `pg_restore --list` antes de una migración. La migración
nueva solo agrega el outbox: no transforma ni borra reservas/pagos antiguos.
No ejecutar `docker compose down -v`, borrar volúmenes ni cambiar roles sin
inventario, respaldo y plan de recuperación. La semilla de bases PostgreSQL
se ejecuta solo cuando el volumen es nuevo.

Rollback: conservar ambos dumps y el commit anterior; volver a su imagen/código
sin borrar el volumen. Revisar pagos v2 antes de devolver tráfico a v1 para no
perder visibilidad del histórico. Una sola instancia EC2/servidor PostgreSQL es
un punto único de fallo; este diseño no reclama alta disponibilidad multiinstancia.
