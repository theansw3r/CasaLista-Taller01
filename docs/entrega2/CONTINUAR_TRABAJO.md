# Continuar la Entrega 2 de CasaLista

Repositorio: https://github.com/theansw3r/CasaLista-Taller01
Rama de avance: `entrega2/auditoria-integraciones`.
Base de implementación auditada: `d359099b0f7894215c7dfda4f10534088083a624`.
Destino final de entrega: `main`, después de completar y verificar lo pendiente.

## Obtener la versión de trabajo

En una carpeta nueva:

```bash
git clone --branch entrega2/auditoria-integraciones https://github.com/theansw3r/CasaLista-Taller01.git
cd CasaLista-Taller01
git log -1 --format=fuller
git status
```

Si ya tiene una copia, guardar primero cualquier trabajo propio y luego hacer
`git fetch origin`. Cambiar a la rama de avance solo con el directorio de trabajo
limpio; no usar reset forzado ni sobrescribir cambios. Registrar cada contribución
con la identidad real de su autor; no reutilizar la identidad de Lucas.

## Revisar y ejecutar

Leer en este orden:

1. `ESTADO_Y_EVIDENCIAS.md`: qué se verificó y qué falta.
2. `ARQUITECTURA.md`: servicios, Strangler, Adapter/DIP y eventos.
3. `CONTRATOS_API.md`: APIs propias, tercero y bloqueo del aliado.
4. `DESPLIEGUE_AWS.md`: crear y verificar la infraestructura pendiente.

Para una instalación nueva con Docker, desde la raíz del repositorio:

```bash
python3 scripts/preparar_entorno.py
docker compose config --quiet
docker compose up -d --build --wait --wait-timeout 180
```

Abrir http://localhost:8080/. El generador crea .env con secretos locales y
no sobrescribe uno existente. Los secretos, bases de prueba y entornos Python
no se publican en Git. Para demostración con datos ficticios, consultar README.

## Prioridades de cierre

1. Identificar equipo aliado y acordar URL, contrato JSON, autenticación y
   disponibilidad; implementar su consumo y mostrar resultados reales.
2. Crear EC2 en el Learner Lab de AWS Academy autorizado, asociar IP elástica,
   desplegar y verificar desde fuera de la instancia.
3. Recoger evidencia real de EC2 encendida, EIP asociada, SHA desplegado,
   APIs, idiomas y procesamiento asíncrono.
4. Confirmar las contribuciones auténticas de todos los integrantes.
5. Ejecutar las pruebas, revisar el cambio e integrar a main. Entregar el enlace
   de main y la IP elástica real. No reclamar el bono >70% sin demostrarlo.

## Validaciones y límites del avance

El avance se verificó localmente con 167 pruebas Django y 30 Flask, además de
pruebas HTTP y navegador y fallos de Redis/Flask. Las evidencias guardan su fecha;
no prueban que AWS o el aliado estén listos. El flujo de pagos usa SIMULADA,
y el correo se procesó mediante consola, sin acreditar recepción SMTP externa.
La automatización de GitHub valida pruebas y construcción de imágenes al subir
la rama; consultar su resultado en Actions, no asumir éxito por existir el archivo.

La lista de comandos de pruebas y de catálogos gettext está en README.
Preservar los volúmenes y las credenciales de cualquier instalación existente;
no ejecutar `docker compose down -v` ni reiniciar datos para actualizarla.
