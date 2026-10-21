// Estructura común de todas las páginas: cabecera con el menú y el hueco para el contenido.

import { api } from "./api.js";
import { alerta, icono } from "./ui.js";

const MENU = [
  ["apartados", "/", "Apartados"],
  ["ventas", "/ventas", "Ventas"],
];

export function montarLayout(seccion) {
  document.body.innerHTML = `
    <a class="skip" href="#contenido">Saltar al contenido</a>
    <header class="topbar"><div class="topbar-inner">
      <a class="brand" href="/">${icono("logo", 22)} Paso Firme</a>
      <nav class="nav" aria-label="Principal">
        ${MENU.map(([id, url, texto]) => `<a href="${url}" ${id === seccion ? 'aria-current="page"' : ""}>${icono(id)} ${texto}</a>`).join("")}
        <a href="#" id="descargar-excel">${icono("excel")} Descargar Excel</a>
        <a href="/docs">${icono("api")} API</a>
      </nav>
    </div></header>
    <main id="contenido"></main>`;
  document.getElementById("descargar-excel").addEventListener("click", async (evento) => {
    evento.preventDefault();
    try {
      await api.descargarExcel();
    } catch (e) {
      mostrarAviso("error", e.message);
    }
  });
  return document.getElementById("contenido");
}

// Si la dirección trae un mensaje (por ejemplo ?ok=Encargo+creado), lo muestra.
export function avisoDeLaDireccion() {
  const ok = new URLSearchParams(location.search).get("ok");
  if (ok) mostrarAviso("ok", ok);
}

// Pone un mensaje (de error o de éxito) arriba del contenido, sustituyendo el anterior.
export function mostrarAviso(tipo, texto) {
  const principal = document.getElementById("contenido");
  principal.querySelector(":scope > .alert")?.remove();
  principal.insertAdjacentHTML("afterbegin", alerta(tipo, texto));
  window.scrollTo({ top: 0 });
}
