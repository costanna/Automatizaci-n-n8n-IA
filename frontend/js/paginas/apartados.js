// Página «Apartados»: lista con pestañas por estado, buscador y paginación.

import { api } from "../api.js";
import { avisoDeLaDireccion, mostrarAviso, montarLayout } from "../layout.js";
import { esc, euros, etiquetaEstado, icono, paginacion, plazo } from "../ui.js";

const principal = montarLayout("apartados");
const params = new URLSearchParams(location.search);
const estado = params.get("estado") ?? "activo";
const q = params.get("q") ?? "";
const POR_PAGINA = 25;
let pagina = Number(params.get("pagina")) || 1;

const PESTANAS = [["activo", "Activos"], ["liquidado", "Liquidados"], ["vencido", "Vencidos"], ["", "Todos"]];

function fila(a) {
  return `<tr>
    <td class="muted">#${a.id}</td>
    <td><a class="row-link" href="/apartados/${a.id}">${esc(a.cliente)}</a>${a.telefono ? `<span class="sub">${esc(a.telefono)}</span>` : ""}</td>
    <td>${esc(a.producto)}${a.talla ? `<span class="sub">Talla ${esc(a.talla)}</span>` : ""}</td>
    <td class="num">${euros(a.precio)}</td>
    <td class="num"><strong>${euros(a.pendiente)}</strong></td>
    <td>${esc(a.fecha_limite)}<span class="sub">${plazo(a)}</span></td>
    <td>${etiquetaEstado(a.estado)}</td>
  </tr>`;
}

function vacio() {
  return q
    ? `No hay apartados que coincidan con «${esc(q)}». Prueba con otro nombre o <a href="/?estado=">busca en todos los estados</a>.`
    : 'Todavía no hay apartados aquí. <a href="/apartados/nuevo">Crea el primero</a>.';
}

async function pintar() {
  let { items, total } = await api.apartados({ estado, q, pagina, porPagina: POR_PAGINA });
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  if (pagina > paginas) {
    pagina = paginas;
    ({ items, total } = await api.apartados({ estado, q, pagina, porPagina: POR_PAGINA }));
  }
  const resumen = await api.resumen();
  const base = `/?estado=${encodeURIComponent(estado)}${q ? `&q=${encodeURIComponent(q)}` : ""}&`;

  principal.innerHTML = `
    <div class="page-head">
      <h1>Apartados</h1>
      <a class="btn btn-primary" href="/apartados/nuevo">${icono("plus")} Nuevo apartado</a>
    </div>
    <section class="card" aria-label="Lista de apartados">
      <div class="toolbar">
        <nav class="tabs" aria-label="Filtrar por estado">
          ${PESTANAS.map(([valor, nombre]) => `<a href="/?estado=${valor}${q ? `&q=${encodeURIComponent(q)}` : ""}" ${valor === estado ? 'aria-current="page"' : ""}>
            ${nombre} <span class="count">${valor === "" ? resumen.total : resumen[valor]}</span></a>`).join("")}
        </nav>
        <form class="search" method="get" action="/" role="search">
          <input type="hidden" name="estado" value="${esc(estado)}">
          ${icono("search")}
          <label for="q" class="skip">Buscar apartado</label>
          <input id="q" name="q" type="search" value="${esc(q)}" placeholder="Buscar cliente, producto, teléfono o nº">
        </form>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Nº</th><th>Cliente</th><th>Producto</th><th class="num">Precio</th><th class="num">Pendiente</th><th>Fecha límite</th><th>Estado</th></tr></thead>
          <tbody>${items.map(fila).join("")}</tbody>
        </table>
        ${items.length ? "" : `<div class="empty">${vacio()}</div>`}
      </div>
      ${paginacion(pagina, paginas, total, base)}
    </section>`;
  avisoDeLaDireccion();
}

pintar().catch((e) => mostrarAviso("error", e.message));
