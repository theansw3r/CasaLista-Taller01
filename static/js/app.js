const API = "/api/v1";
// Pagos se saco del monolito a un servicio en Flask (/api/v2/pagos/). Django
// dice en el HTML a cual version pagar: v1 si se corre solo con runserver,
// v2 cuando esta Nginx adelante.
const URL_PAGOS = document.body.dataset.urlPagos || API + "/pagos/";

const estado = {
  token: localStorage.getItem("token") || null,
  correo: localStorage.getItem("correo") || null,
  perfil: null,
  profesional: null,
  servicios: [],
  bloque: null,
};

// ---------------------------------------------------------------- utilidades
function $(id) {
  return document.getElementById(id);
}

function mostrar(id, visible) {
  $(id).classList.toggle("oculto", !visible);
}

function pesos(valor) {
  return "$ " + Number(valor).toLocaleString("es-CO");
}

function fecha(iso) {
  return new Date(iso).toLocaleDateString("es-CO", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function avisar(mensaje, tipo = "ok", codigo = null) {
  const div = document.createElement("div");
  div.className = "aviso " + tipo;
  div.innerHTML =
    (codigo ? `<span class="codigo">${codigo}</span>` : "") + mensaje;
  $("avisos").appendChild(div);
  setTimeout(() => div.remove(), 5000);
}

// ---------------------------------------------------------------- peticiones
async function pedir(ruta, opciones = {}) {
  const cabeceras = { "Content-Type": "application/json" };
  if (estado.token) cabeceras["Authorization"] = "Bearer " + estado.token;

  const url = ruta.startsWith("/api/") ? ruta : API + ruta;
  const respuesta = await fetch(url, { ...opciones, headers: cabeceras });

  if (respuesta.status === 204) return null;

  const cuerpo = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    // Un 401 con token guardado significa que la sesion vencio. Se cierra
    // para que el usuario vuelva a entrar, en vez de quedar reintentando.
    if (respuesta.status === 401 && estado.token) {
      cerrarSesion();
      const vencida = new Error("Tu sesion expiro. Vuelve a iniciar sesion.");
      vencida.codigo = "SESION";
      throw vencida;
    }

    // La API siempre responde errores con la misma forma:
    // {"error": {"codigo": "RN-01", "mensaje": "..."}}
    const error = cuerpo.error || {};
    const problema = new Error(error.mensaje || "Ocurrio un error inesperado.");
    problema.codigo = error.codigo || "HTTP-" + respuesta.status;
    problema.contexto = error.contexto;
    throw problema;
  }
  return cuerpo;
}

async function intentar(accion) {
  try {
    await accion();
  } catch (error) {
    avisar(error.message, "error", error.codigo);
  }
}

// ---------------------------------------------------------------- sesion
function cerrarSesion() {
  estado.token = null;
  estado.correo = null;
  estado.perfil = null;
  localStorage.clear();
  mostrar("pantalla-acceso", true);
  mostrar("pantalla-app", false);
  $("sesion").innerHTML = "";
}

async function iniciarSesion(correo, clave) {
  const datos = await pedir("/cuentas/token/", {
    method: "POST",
    body: JSON.stringify({ username: correo, password: clave }),
  });
  estado.token = datos.access;
  estado.correo = correo;
  localStorage.setItem("token", datos.access);
  localStorage.setItem("correo", correo);
  await entrarAlaApp();
  avisar("Bienvenido a CasaLista");
}

async function entrarAlaApp() {
  // El perfil dice que roles tiene la cuenta. Segun eso se arma el menu:
  // no tiene sentido mostrarle "Mi agenda" a alguien que solo es cliente.
  estado.perfil = await pedir("/cuentas/perfil/");

  mostrar("pantalla-acceso", false);
  mostrar("pantalla-app", true);

  $("sesion").innerHTML = `<span>${estado.correo}</span>
    <button class="boton pequeno" id="btn-salir">Salir</button>`;
  $("btn-salir").onclick = cerrarSesion;

  armarMenu();
}

function armarMenu() {
  const opciones = [];
  if (estado.perfil.cliente) {
    opciones.push({ vista: "vista-buscar", texto: "Buscar servicio" });
    opciones.push({ vista: "vista-reservas", texto: "Mis reservas" });
  }
  if (estado.perfil.profesional) {
    opciones.push({ vista: "vista-mi-agenda", texto: "Mi agenda" });
    opciones.push({ vista: "vista-mis-servicios", texto: "Mis servicios" });
  }

  $("menu").innerHTML = "";
  opciones.forEach((opcion, indice) => {
    const boton = document.createElement("button");
    boton.className = "opcion" + (indice === 0 ? " activa" : "");
    boton.textContent = opcion.texto;
    boton.dataset.vista = opcion.vista;
    boton.onclick = () => cambiarVista(opcion.vista);
    $("menu").appendChild(boton);
  });

  if (opciones.length) cambiarVista(opciones[0].vista);
}

function cambiarVista(vista) {
  document.querySelectorAll(".vista").forEach((v) => v.classList.add("oculto"));
  $(vista).classList.remove("oculto");

  document
    .querySelectorAll(".opcion")
    .forEach((o) => o.classList.toggle("activa", o.dataset.vista === vista));

  if (vista === "vista-buscar") intentar(buscarProfesionales);
  if (vista === "vista-reservas") intentar(cargarReservas);
  if (vista === "vista-mi-agenda") intentar(cargarMiAgenda);
  if (vista === "vista-mis-servicios") intentar(cargarMisServicios);
}

// ================================================================ CLIENTE
async function buscarProfesionales() {
  const filtros = new URLSearchParams();
  if ($("buscar-zona").value) filtros.set("zona", $("buscar-zona").value);
  if ($("buscar-oficio").value) filtros.set("categoria", $("buscar-oficio").value);

  const consulta = filtros.toString();
  const datos = await pedir(
    "/catalogo/profesionales/" + (consulta ? "?" + consulta : "")
  );

  const contenedor = $("lista-profesionales");
  contenedor.innerHTML = "";
  mostrar("bloque-servicios", false);
  mostrar("bloque-agenda", false);
  mostrar("bloque-confirmar", false);

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      '<p class="vacio">No hay profesionales verificados para esa busqueda.</p>';
    return;
  }

  datos.resultados.forEach((pro) => {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `
      <div>
        <div class="item-titulo">${pro.nombre}</div>
        ${pro.descripcion ? `<div class="item-detalle">${pro.descripcion}</div>` : ""}
        <div class="item-detalle">Cubre: ${pro.zonas.join(", ")}</div>
      </div>
      <span class="item-precio">${pro.calificacion_promedio} ★</span>`;
    item.onclick = () => intentar(() => elegirProfesional(pro, item));
    contenedor.appendChild(item);
  });
}

async function elegirProfesional(pro, elemento) {
  document
    .querySelectorAll("#lista-profesionales .item")
    .forEach((i) => i.classList.remove("seleccionado"));
  elemento.classList.add("seleccionado");

  estado.profesional = pro;
  estado.servicios = [];
  estado.bloque = null;
  mostrar("bloque-confirmar", false);

  await cargarServicios(pro.id);
  await cargarAgenda(pro.id);
}

async function cargarServicios(profesionalId) {
  const datos = await pedir(`/catalogo/profesionales/${profesionalId}/servicios/`);
  const contenedor = $("lista-servicios");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      '<p class="vacio">Este profesional todavia no publico servicios.</p>';
  }

  datos.resultados.forEach((servicio) => {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `
      <div>
        <div class="item-titulo">${servicio.nombre}</div>
        <div class="item-detalle">${servicio.descripcion}</div>
        <div class="item-detalle">${servicio.categoria_nombre} · ${
      servicio.duracion_minutos
    } minutos</div>
      </div>
      <span class="item-precio">${pesos(servicio.precio_base)}</span>`;
    item.onclick = () => alternarServicio(servicio, item);
    contenedor.appendChild(item);
  });

  mostrar("bloque-servicios", true);
}

function alternarServicio(servicio, elemento) {
  const posicion = estado.servicios.findIndex((s) => s.id === servicio.id);
  if (posicion >= 0) {
    estado.servicios.splice(posicion, 1);
    elemento.classList.remove("seleccionado");
  } else {
    estado.servicios.push(servicio);
    elemento.classList.add("seleccionado");
  }
  refrescarConfirmacion();
}

async function cargarAgenda(profesionalId) {
  const datos = await pedir(
    `/reservas/disponibilidad/?profesional_id=${profesionalId}`
  );
  const contenedor = $("lista-bloques");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      '<p class="vacio">Este profesional no tiene horarios libres.</p>';
  }

  datos.resultados.forEach((bloque) => {
    const item = document.createElement("div");
    item.className = "item";
    item.innerHTML = `
      <div>
        <div class="item-titulo">${fecha(bloque.inicio)}</div>
        <div class="item-detalle">Disponible ${bloque.duracion_minutos} minutos</div>
      </div>`;
    item.onclick = () => {
      document
        .querySelectorAll("#lista-bloques .item")
        .forEach((i) => i.classList.remove("seleccionado"));
      item.classList.add("seleccionado");
      estado.bloque = bloque;
      refrescarConfirmacion();
    };
    contenedor.appendChild(item);
  });

  mostrar("bloque-agenda", true);
}

function refrescarConfirmacion() {
  const listo = estado.servicios.length > 0 && estado.bloque;
  mostrar("bloque-confirmar", listo);
  if (!listo) return;

  const total = estado.servicios.reduce(
    (suma, s) => suma + Number(s.precio_base),
    0
  );
  const minutos = estado.servicios.reduce(
    (suma, s) => suma + s.duracion_minutos,
    0
  );

  $("reserva-zona").value = $("buscar-zona").value || "Laureles";
  $("resumen-reserva").innerHTML = `
    ${estado.servicios.map((s) => `<div>${s.nombre}</div>`).join("")}
    <div class="item-detalle">${fecha(estado.bloque.inicio)} · ${minutos} min</div>
    <div class="total">Total estimado: ${pesos(total)}</div>`;
}

async function crearReserva() {
  const reserva = await pedir("/reservas/", {
    method: "POST",
    body: JSON.stringify({
      bloque_id: estado.bloque.id,
      direccion: $("reserva-direccion").value,
      zona: $("reserva-zona").value,
      servicios: estado.servicios.map((s) => ({ servicio_id: s.id, cantidad: 1 })),
    }),
  });

  avisar(`Reserva #${reserva.id} creada por ${pesos(reserva.total)}`);
  estado.servicios = [];
  estado.bloque = null;
  cambiarVista("vista-reservas");
}

async function cargarReservas() {
  const datos = await pedir("/reservas/");
  const contenedor = $("lista-reservas");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML = '<p class="vacio">Todavia no tienes reservas.</p>';
    return;
  }

  datos.resultados.forEach((reserva) => {
    const item = pintarReserva(reserva, true);
    contenedor.appendChild(item);
  });
}

function pintarReserva(reserva, conAcciones) {
  const item = document.createElement("div");
  item.className = "item estatico";

  const detalles = reserva.detalles
    .map((d) => `${d.cantidad} x ${d.servicio} — ${pesos(d.subtotal)}`)
    .join("<br>");

  const penalizacion =
    Number(reserva.penalizacion) > 0
      ? `<br>Penalizacion aplicada: ${pesos(reserva.penalizacion)}`
      : "";

  item.innerHTML = `
    <div class="cabecera-reserva">
      <div>
        <div class="item-titulo">Reserva #${reserva.id} · ${
    conAcciones ? reserva.profesional : reserva.cliente
  }</div>
        <div class="item-detalle">${fecha(reserva.inicio)}</div>
        <div class="item-detalle">${reserva.direccion} (${reserva.zona})</div>
      </div>
      <span class="etiqueta ${reserva.estado}">${reserva.estado}</span>
    </div>
    <div class="detalles-reserva">
      ${detalles}<br>
      <strong>Total: ${pesos(reserva.total)}</strong> · tarifa ${reserva.tarifa_aplicada}
      ${penalizacion}
    </div>`;

  const activa = reserva.estado === "PENDIENTE" || reserva.estado === "CONFIRMADA";
  if (conAcciones && activa) {
    const acciones = document.createElement("div");
    acciones.className = "acciones";

    if (reserva.estado === "PENDIENTE") {
      const pagar = document.createElement("button");
      pagar.className = "boton pequeno";
      pagar.textContent = "Pagar con tarjeta";
      pagar.onclick = () => intentar(() => pagarReserva(reserva.id));
      acciones.appendChild(pagar);
    }

    const cancelar = document.createElement("button");
    cancelar.className = "boton pequeno peligro";
    cancelar.textContent = "Cancelar";
    cancelar.onclick = () => intentar(() => cancelarReserva(reserva.id));
    acciones.appendChild(cancelar);

    item.appendChild(acciones);
  }
  return item;
}

async function pagarReserva(id) {
  const pago = await pedir(URL_PAGOS, {
    method: "POST",
    body: JSON.stringify({ reserva_id: id, medio: "TARJETA" }),
  });
  avisar(`Pago aprobado (${pago.referencia_externa}). Reserva confirmada.`);
  await cargarReservas();
}

async function cancelarReserva(id) {
  const reserva = await pedir(`/reservas/${id}/cancelacion/`, {
    method: "POST",
    body: JSON.stringify({ motivo: "Cancelada desde la aplicacion" }),
  });
  const retenido = Number(reserva.penalizacion);
  avisar(
    retenido > 0
      ? `Reserva cancelada. Se retuvo ${pesos(retenido)} por politica de cancelacion.`
      : "Reserva cancelada sin penalizacion."
  );
  await cargarReservas();
}

// ================================================================ PROFESIONAL
function avisoDeVerificacion() {
  const pro = estado.perfil.profesional;
  if (!pro || pro.verificado) return "";
  return `<div class="tarjeta alerta">
      Tu cuenta esta <strong>pendiente de verificacion</strong>. Puedes publicar
      servicios y horarios, pero no apareceras en las busquedas hasta que un
      administrador te verifique (regla RN-07).
    </div>`;
}

async function cargarMisServicios() {
  $("aviso-verificacion").innerHTML = avisoDeVerificacion();

  const datos = await pedir("/catalogo/mis-servicios/");
  const contenedor = $("lista-mis-servicios");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      '<p class="vacio">Todavia no has publicado servicios.</p>';
    return;
  }

  datos.resultados.forEach((servicio) => {
    const item = document.createElement("div");
    item.className = "item estatico";
    item.innerHTML = `
      <div class="cabecera-reserva">
        <div>
          <div class="item-titulo">${servicio.nombre}</div>
          <div class="item-detalle">${servicio.categoria_nombre}</div>
          <div class="item-detalle">${servicio.duracion_minutos} minutos · ${pesos(
      servicio.precio_base
    )}</div>
        </div>
        <span class="etiqueta ${servicio.activo ? "CONFIRMADA" : "CANCELADA"}">
          ${servicio.activo ? "ACTIVO" : "INACTIVO"}
        </span>
      </div>`;
    contenedor.appendChild(item);
  });
}

async function publicarServicio() {
  const creado = await pedir("/catalogo/mis-servicios/", {
    method: "POST",
    body: JSON.stringify({
      categoria: $("serv-categoria").value,
      nombre: $("serv-nombre").value,
      descripcion: $("serv-descripcion").value,
      precio_base: $("serv-precio").value,
      duracion_minutos: Number($("serv-duracion").value),
    }),
  });
  avisar(`Servicio "${creado.nombre}" publicado.`);
  $("serv-nombre").value = "";
  $("serv-descripcion").value = "";
  $("serv-precio").value = "";
  $("serv-duracion").value = "";
  await cargarMisServicios();
}

async function cargarMiAgenda() {
  const agenda = await pedir("/reservas/mi-agenda/");
  const contenedor = $("lista-mi-agenda");
  contenedor.innerHTML = "";

  if (!agenda.resultados.length) {
    contenedor.innerHTML =
      '<p class="vacio">Todavia no has publicado horarios.</p>';
  }

  agenda.resultados.forEach((bloque) => {
    const item = document.createElement("div");
    item.className = "item estatico";
    item.innerHTML = `
      <div class="cabecera-reserva">
        <div>
          <div class="item-titulo">${fecha(bloque.inicio)}</div>
          <div class="item-detalle">${bloque.duracion_minutos} minutos</div>
        </div>
        <span class="etiqueta ${
          bloque.estado === "LIBRE" ? "CONFIRMADA" : "PENDIENTE"
        }">${bloque.estado}</span>
      </div>`;
    contenedor.appendChild(item);
  });

  const recibidas = await pedir("/reservas/recibidas/");
  const lista = $("lista-recibidas");
  lista.innerHTML = "";

  if (!recibidas.resultados.length) {
    lista.innerHTML = '<p class="vacio">Nadie te ha reservado todavia.</p>';
    return;
  }
  recibidas.resultados.forEach((reserva) =>
    lista.appendChild(pintarReserva(reserva, false))
  );
}

async function abrirHorario() {
  const dia = $("agenda-dia").value;
  const hora = $("agenda-hora").value;
  const horas = Number($("agenda-horas").value);

  if (!dia || !hora) {
    avisar("Elige el dia y la hora de inicio.", "error", "FALTAN DATOS");
    return;
  }

  const inicio = new Date(`${dia}T${hora}`);
  const fin = new Date(inicio.getTime() + horas * 60 * 60 * 1000);

  await pedir("/reservas/disponibilidad/", {
    method: "POST",
    body: JSON.stringify({
      inicio: inicio.toISOString(),
      fin: fin.toISOString(),
    }),
  });

  avisar("Horario publicado.");
  await cargarMiAgenda();
}

// ---------------------------------------------------------------- arranque
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".pestana").forEach((pestana) => {
    pestana.onclick = () => {
      document
        .querySelectorAll(".pestana")
        .forEach((p) => p.classList.toggle("activa", p === pestana));
      ["panel-login", "panel-registro", "panel-registro-pro"].forEach((panel) =>
        mostrar(panel, pestana.dataset.panel === panel)
      );
    };
  });

  $("btn-login").onclick = () =>
    intentar(() => iniciarSesion($("login-correo").value, $("login-clave").value));

  $("btn-registro").onclick = () =>
    intentar(async () => {
      await pedir("/cuentas/registro/cliente/", {
        method: "POST",
        body: JSON.stringify({
          correo: $("reg-correo").value,
          contrasena: $("reg-clave").value,
          nombre: $("reg-nombre").value,
          telefono: $("reg-telefono").value,
        }),
      });
      avisar("Cuenta creada.");
      await iniciarSesion($("reg-correo").value, $("reg-clave").value);
    });

  $("btn-registro-pro").onclick = () =>
    intentar(async () => {
      const zonas = [...document.querySelectorAll("#pro-zonas input:checked")].map(
        (c) => c.value
      );
      await pedir("/cuentas/registro/profesional/", {
        method: "POST",
        body: JSON.stringify({
          correo: $("pro-correo").value,
          contrasena: $("pro-clave").value,
          nombre: $("pro-nombre").value,
          documento: $("pro-documento").value,
          descripcion: $("pro-descripcion").value,
          zonas_cobertura: zonas,
        }),
      });
      avisar("Cuenta profesional creada. Queda pendiente de verificacion.");
      await iniciarSesion($("pro-correo").value, $("pro-clave").value);
    });

  $("btn-buscar").onclick = () => intentar(buscarProfesionales);
  $("btn-reservar").onclick = () => intentar(crearReserva);
  $("btn-publicar-servicio").onclick = () => intentar(publicarServicio);
  $("btn-abrir-agenda").onclick = () => intentar(abrirHorario);

  if (estado.token) {
    intentar(entrarAlaApp);
  }
});
