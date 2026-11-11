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
  return new Intl.NumberFormat(document.documentElement.lang, {style:"currency", currency:"COP", maximumFractionDigits:0}).format(Number(valor));
}

function fecha(iso) {
  return new Date(iso).toLocaleDateString(document.documentElement.lang, {
    timeZone: "America/Bogota",
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
  if (codigo) {
    const etiqueta = document.createElement("span");
    etiqueta.className = "codigo";
    etiqueta.textContent = codigo;
    div.appendChild(etiqueta);
  }
  div.appendChild(document.createTextNode(mensaje));
  $("avisos").appendChild(div);
  setTimeout(() => div.remove(), 5000);
}

// ---------------------------------------------------------------- peticiones
async function pedir(ruta, opciones = {}) {
  const cabeceras = { "Content-Type": "application/json", "Accept-Language": document.documentElement.lang };
  if (estado.token) cabeceras["Authorization"] = "Bearer " + estado.token;

  const url = ruta.startsWith("/api/") ? ruta : API + ruta;
  let respuesta;
  try {
    respuesta = await fetch(url, { ...opciones, headers: cabeceras, signal: AbortSignal.timeout(15000) });
  } catch {
    throw new Error(gettext("No hay conexión con el servidor. Intenta de nuevo."));
  }

  if (respuesta.status === 204) return null;

  const cuerpo = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    // Un 401 con token guardado significa que la sesion vencio. Se cierra
    // para que el usuario vuelva a entrar, en vez de quedar reintentando.
    if (respuesta.status === 401 && estado.token) {
      cerrarSesion();
      const vencida = new Error(gettext("Tu sesión expiró. Vuelve a iniciar sesión."));
      vencida.codigo = "SESION";
      throw vencida;
    }

    // La API siempre responde errores con la misma forma:
    // {"error": {"codigo": "RN-01", "mensaje": "..."}}
    const error = cuerpo.error || {};
    const problema = new Error(error.mensaje || gettext("Ocurrió un error inesperado."));
    problema.codigo = error.codigo || "HTTP-" + respuesta.status;
    problema.contexto = error.contexto;
    throw problema;
  }
  return cuerpo;
}

async function intentar(accion, boton = document.activeElement) {
  if (boton?.tagName !== "BUTTON") boton = null;
  if (boton?.disabled) return;
  if (boton) { boton.disabled = true; boton.setAttribute("aria-busy", "true"); }
  try {
    await accion();
  } catch (error) {
    avisar(error.message, "error", error.codigo);
  } finally {
    if (boton) { boton.disabled = false; boton.removeAttribute("aria-busy"); }
  }
}

// ---------------------------------------------------------------- sesion
function cerrarSesion() {
  estado.token = null;
  estado.correo = null;
  estado.perfil = null;
  localStorage.removeItem("token");
  localStorage.removeItem("correo");
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
  avisar(gettext("Bienvenido a CasaLista"));
}

async function entrarAlaApp() {
  // El perfil dice que roles tiene la cuenta. Segun eso se arma el menu:
  // no tiene sentido mostrarle gettext("Mi agenda") a alguien que solo es cliente.
  estado.perfil = await pedir("/cuentas/perfil/");

  mostrar("pantalla-acceso", false);
  mostrar("pantalla-app", true);

  $("sesion").innerHTML = `<span>${esc(estado.correo)}</span>
    <button class="boton pequeno" id="btn-salir">${gettext("Salir")}</button>`;
  $("btn-salir").onclick = cerrarSesion;

  armarMenu();
}

function armarMenu() {
  const opciones = [];
  if (estado.perfil.cliente) {
    opciones.push({ vista: "vista-buscar", texto: gettext("Buscar servicio") });
    opciones.push({ vista: "vista-reservas", texto: gettext("Mis reservas") });
  }
  if (estado.perfil.profesional) {
    opciones.push({ vista: "vista-mi-agenda", texto: gettext("Mi agenda") });
    opciones.push({ vista: "vista-mis-servicios", texto: gettext("Mis servicios") });
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

  if (vista === "vista-buscar") intentar(buscarProfesionales, null);
  if (vista === "vista-reservas") intentar(cargarReservas, null);
  if (vista === "vista-mi-agenda") intentar(cargarMiAgenda, null);
  if (vista === "vista-mis-servicios") intentar(cargarMisServicios, null);
}

// ================================================================ CLIENTE
async function buscarProfesionales(pagina = 1) {
  const filtros = new URLSearchParams();
  if ($("buscar-zona").value) filtros.set("zona", $("buscar-zona").value);
  if ($("buscar-oficio").value) filtros.set("categoria", $("buscar-oficio").value);

  const consulta = filtros.toString();
  const datos = await pedirPagina("/catalogo/profesionales/" + (consulta ? "?" + consulta : ""), pagina);

  const contenedor = $("lista-profesionales");
  contenedor.innerHTML = "";
  mostrar("bloque-servicios", false);
  mostrar("bloque-agenda", false);
  mostrar("bloque-confirmar", false);

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      `<p class="vacio">${gettext("No hay profesionales verificados para esa búsqueda.")}</p>`;
    return;
  }

  datos.resultados.forEach((pro) => {
    const item = document.createElement("div");
    item.className = "item";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.innerHTML = `
      <div>
        <div class="item-titulo">${esc(pro.nombre)}</div>
        ${pro.descripcion ? `<div class="item-detalle">${esc(pro.descripcion)}</div>` : ""}
        <div class="item-detalle">${gettext("Cubre:")} ${pro.zonas.map(esc).join(", ")}</div>
      </div>
      <span class="item-precio">${pro.calificacion_promedio} ★</span>`;
    item.onclick = () => intentar(() => elegirProfesional(pro, item));
    contenedor.appendChild(item);
  });
  paginar(contenedor, datos, buscarProfesionales);
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

async function cargarServicios(profesionalId, pagina = 1) {
  const datos = await pedirPagina(`/catalogo/profesionales/${profesionalId}/servicios/`, pagina);
  const contenedor = $("lista-servicios");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      `<p class="vacio">${gettext("Este profesional todavía no publicó servicios.")}</p>`;
  }

  datos.resultados.forEach((servicio) => {
    const item = document.createElement("div");
    item.className = "item";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.innerHTML = `
      <div>
        <div class="item-titulo">${esc(servicio.nombre)}</div>
        <div class="item-detalle">${esc(servicio.descripcion)}</div>
        <div class="item-detalle">${esc(servicio.categoria_nombre)} · ${
      servicio.duracion_minutos
    } ${gettext("minutos")}</div>
      </div>
      <span class="item-precio">${pesos(servicio.precio_base)}</span>`;
    item.onclick = () => alternarServicio(servicio, item);
    contenedor.appendChild(item);
  });

  paginar(contenedor, datos, n => cargarServicios(profesionalId, n));
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

async function cargarAgenda(profesionalId, pagina = 1) {
  const datos = await pedirPagina(`/reservas/disponibilidad/?profesional_id=${profesionalId}`, pagina);
  const contenedor = $("lista-bloques");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      `<p class="vacio">${gettext("Este profesional no tiene horarios libres.")}</p>`;
  }

  datos.resultados.forEach((bloque) => {
    const item = document.createElement("div");
    item.className = "item";
    item.tabIndex = 0;
    item.setAttribute("role", "button");
    item.innerHTML = `
      <div>
        <div class="item-titulo">${fecha(bloque.inicio)}</div>
        <div class="item-detalle">${gettext("Disponible")} ${bloque.duracion_minutos} ${gettext("minutos")}</div>
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

  paginar(contenedor, datos, n => cargarAgenda(profesionalId, n));
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
    ${estado.servicios.map((s) => `<div>${esc(s.nombre)}</div>`).join("")}
    <div class="item-detalle">${fecha(estado.bloque.inicio)} · ${minutos} min</div>
    <div class="total">${gettext("Total estimado:")} ${pesos(total)}</div>`;
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

  avisar(interpolate(gettext("Reserva #%(id)s creada por %(total)s"), {id: reserva.id, total: pesos(reserva.total)}, true));
  estado.servicios = [];
  estado.bloque = null;
  cambiarVista("vista-reservas");
}

async function cargarReservas(pagina = 1) {
  const datos = await pedirPagina("/reservas/", pagina);
  const contenedor = $("lista-reservas");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML = `<p class="vacio">${gettext("Todavía no tienes reservas.")}</p>`;
    return;
  }

  datos.resultados.forEach((reserva) => {
    const item = pintarReserva(reserva, true);
    contenedor.appendChild(item);
  });
  paginar(contenedor, datos, cargarReservas);
}

function pintarReserva(reserva, conAcciones) {
  const item = document.createElement("div");
  item.className = "item estatico";

  const detalles = reserva.detalles
    .map((d) => `${d.cantidad} x ${esc(d.servicio)} — ${pesos(d.subtotal)}`)
    .join("<br>");

  const penalizacion =
    Number(reserva.penalizacion) > 0
      ? `<br>${gettext("Penalización aplicada:")} ${pesos(reserva.penalizacion)}`
      : "";

  item.innerHTML = `
    <div class="cabecera-reserva">
      <div>
        <div class="item-titulo">${gettext("Reserva")} #${reserva.id} · ${
    esc(conAcciones ? reserva.profesional : reserva.cliente)
  }</div>
        <div class="item-detalle">${fecha(reserva.inicio)}</div>
        <div class="item-detalle">${esc(reserva.direccion)} (${esc(reserva.zona)})</div>
      </div>
      <span class="etiqueta ${reserva.estado}">${gettext(reserva.estado)}</span>
    </div>
    <div class="detalles-reserva">
      ${detalles}<br>
      <strong>${gettext("Total:")} ${pesos(reserva.total)}</strong> · ${gettext("tarifa")} ${gettext(reserva.tarifa_aplicada)}
      ${penalizacion}
    </div>`;

  const activa = reserva.estado === "PENDIENTE" || reserva.estado === "CONFIRMADA";
  if (conAcciones && activa) {
    const acciones = document.createElement("div");
    acciones.className = "acciones";

    if (reserva.estado === "PENDIENTE") {
      const pagar = document.createElement("button");
      pagar.className = "boton pequeno";
      pagar.textContent = gettext("Pagar con tarjeta");
      pagar.onclick = () => intentar(() => pagarReserva(reserva.id));
      acciones.appendChild(pagar);
    }

    const cancelar = document.createElement("button");
    cancelar.className = "boton pequeno peligro";
    cancelar.textContent = gettext("Cancelar");
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
  avisar(interpolate(gettext("Pago aprobado (%(referencia)s). Reserva confirmada."), {referencia: pago.referencia_externa}, true));
  await cargarReservas();
}

async function cancelarReserva(id) {
  if (!window.confirm(gettext("¿Cancelar esta reserva? Se aplicará la política de cancelación según la anticipación de la visita."))) return;
  const reserva = await pedir(`/reservas/${id}/cancelacion/`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  const retenido = Number(reserva.penalizacion);
  avisar(
    retenido > 0
      ? interpolate(gettext("Reserva cancelada. Se retuvo %(monto)s por política de cancelación."), {monto: pesos(retenido)}, true)
      : gettext("Reserva cancelada sin penalización.")
  );
  await cargarReservas();
}

// ================================================================ PROFESIONAL
function avisoDeVerificacion() {
  const pro = estado.perfil.profesional;
  if (!pro || pro.verificado) return "";
  return `<div class="tarjeta alerta">${gettext("Tu cuenta está pendiente de verificación. Puedes publicar servicios y horarios; aparecerás en las búsquedas cuando un administrador te verifique.")}</div>`;
}

async function cargarMisServicios(pagina = 1) {
  $("aviso-verificacion").innerHTML = avisoDeVerificacion();

  const datos = await pedirPagina("/catalogo/mis-servicios/", pagina);
  const contenedor = $("lista-mis-servicios");
  contenedor.innerHTML = "";

  if (!datos.resultados.length) {
    contenedor.innerHTML =
      `<p class="vacio">${gettext("Todavía no has publicado servicios.")}</p>`;
    return;
  }

  datos.resultados.forEach((servicio) => {
    const item = document.createElement("div");
    item.className = "item estatico";
    item.innerHTML = `
      <div class="cabecera-reserva">
        <div>
          <div class="item-titulo">${esc(servicio.nombre)}</div>
          <div class="item-detalle">${esc(servicio.categoria_nombre)}</div>
          <div class="item-detalle">${servicio.duracion_minutos} ${gettext("minutos")} · ${pesos(
      servicio.precio_base
    )}</div>
        </div>
        <span class="etiqueta ${servicio.activo ? "CONFIRMADA" : "CANCELADA"}">
          ${gettext(servicio.activo ? "ACTIVO" : "INACTIVO")}
        </span>
      </div>`;
    contenedor.appendChild(item);
  });
  paginar(contenedor, datos, cargarMisServicios);
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
  avisar(interpolate(gettext('Servicio "%(nombre)s" publicado.'), {nombre: creado.nombre}, true));
  $("serv-nombre").value = "";
  $("serv-descripcion").value = "";
  $("serv-precio").value = "";
  $("serv-duracion").value = "";
  await cargarMisServicios();
}

async function cargarMiAgenda(pagina = 1, paginaRecibidas = 1) {
  const agenda = await pedirPagina("/reservas/mi-agenda/", pagina);
  const contenedor = $("lista-mi-agenda");
  contenedor.innerHTML = "";

  if (!agenda.resultados.length) {
    contenedor.innerHTML =
      `<p class="vacio">${gettext("Todavía no has publicado horarios.")}</p>`;
  }

  agenda.resultados.forEach((bloque) => {
    const item = document.createElement("div");
    item.className = "item estatico";
    item.innerHTML = `
      <div class="cabecera-reserva">
        <div>
          <div class="item-titulo">${fecha(bloque.inicio)}</div>
          <div class="item-detalle">${bloque.duracion_minutos} ${gettext("minutos")}</div>
        </div>
        <span class="etiqueta ${
          bloque.estado === "LIBRE" ? "CONFIRMADA" : "PENDIENTE"
        }">${gettext(bloque.estado)}</span>
      </div>`;
    contenedor.appendChild(item);
  });

  paginar(contenedor, agenda, n => cargarMiAgenda(n, paginaRecibidas));
  const recibidas = await pedirPagina("/reservas/recibidas/", paginaRecibidas);
  const lista = $("lista-recibidas");
  lista.innerHTML = "";

  if (!recibidas.resultados.length) {
    lista.innerHTML = `<p class="vacio">${gettext("Nadie te ha reservado todavía.")}</p>`;
    return;
  }
  recibidas.resultados.forEach((reserva) =>
    lista.appendChild(pintarReserva(reserva, false))
  );
  paginar(lista, recibidas, n => cargarMiAgenda(pagina, n));
}

async function abrirHorario() {
  const dia = $("agenda-dia").value;
  const hora = $("agenda-hora").value;
  const horas = Number($("agenda-horas").value);

  if (!dia || !hora) {
    avisar(gettext("Elige el día y la hora de inicio."), "error", "FALTAN DATOS");
    return;
  }

  const inicio = new Date(`${dia}T${hora}:00-05:00`);
  const fin = new Date(inicio.getTime() + horas * 60 * 60 * 1000);

  await pedir("/reservas/disponibilidad/", {
    method: "POST",
    body: JSON.stringify({
      inicio: inicio.toISOString(),
      fin: fin.toISOString(),
    }),
  });

  avisar(gettext("Horario publicado."));
  await cargarMiAgenda();
}

// ---------------------------------------------------------------- arranque
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form.panel").forEach(form => form.addEventListener("submit", e => e.preventDefault()));
  document.addEventListener("click", event => {
    const boton = event.target.closest("button");
    if (!boton?.classList.contains("principal")) return;
    const contenedor = boton.closest(".panel, .tarjeta");
    for (const campo of contenedor.querySelectorAll("input, select")) {
      if (!campo.reportValidity()) { event.preventDefault(); event.stopImmediatePropagation(); return; }
    }
  }, true);
  document.addEventListener("keydown", event => {
    if ((event.key === "Enter" || event.key === " ") && event.target.matches(".item[role=button]")) {
      event.preventDefault(); event.target.click();
    }
  });
  intentar(cargarClima, null);
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
      avisar(gettext("Cuenta creada."));
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
      avisar(gettext("Cuenta profesional creada. Queda pendiente de verificación."));
      await iniciarSesion($("pro-correo").value, $("pro-clave").value);
    });

  $("btn-buscar").onclick = () => intentar(buscarProfesionales, null);
  $("btn-reservar").onclick = () => intentar(crearReserva);
  $("btn-publicar-servicio").onclick = () => intentar(publicarServicio);
  $("btn-abrir-agenda").onclick = () => intentar(abrirHorario);

  if (estado.token) {
    intentar(entrarAlaApp);
  }
});


function esc(valor) {
  const nodo = document.createElement("span");
  nodo.textContent = String(valor ?? "");
  return nodo.innerHTML;
}

async function cargarClima() {
  try {
    const clima = await pedir("/integraciones/clima/");
    $("clima").textContent = interpolate(gettext("%(temperatura)s °C · Precipitación: %(lluvia)s mm · Actualizado: %(hora)s (Bogotá)"), {
      temperatura: clima.temperatura_c, lluvia: clima.precipitacion_mm, hora: clima.observado_en,
    }, true);
  } catch (error) { $("clima").textContent = error.message; }
}


function pedirPagina(ruta, pagina) {
  const separador = ruta.includes("?") ? "&" : "?";
  return pedir(ruta + separador + "pagina=" + pagina);
}

function paginar(contenedor, datos, cargar) {
  if (datos.paginas <= 1) return;
  const nav = document.createElement("nav");
  nav.className = "paginacion";
  const etiqueta = document.createElement("span");
  etiqueta.textContent = interpolate(gettext("Página %(actual)s de %(total)s"), {actual:datos.pagina,total:datos.paginas}, true);
  for (const [texto,numero] of [[gettext("Anterior"),datos.pagina-1],[gettext("Siguiente"),datos.pagina+1]]) {
    const boton = document.createElement("button");
    boton.className = "boton pequeno";
    boton.textContent = texto;
    boton.disabled = numero < 1 || numero > datos.paginas;
    boton.onclick = () => intentar(() => cargar(numero), boton);
    nav.appendChild(boton);
  }
  nav.insertBefore(etiqueta,nav.lastChild);
  contenedor.appendChild(nav);
}
