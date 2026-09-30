-- Base de datos del microservicio de pagos.
-- Corre en el mismo Postgres que Django, pero es OTRA base: Flask no puede
-- ver ni tocar las tablas del monolito, y el monolito no ve la de pagos.
-- Postgres solo ejecuta este script la primera vez que crea el volumen.
CREATE DATABASE casalista_pagos OWNER casalista;
