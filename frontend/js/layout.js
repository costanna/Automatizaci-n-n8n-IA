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
    <header class="topbar"><div class="toldo" aria-hidden="true"></div><div class="topbar-inner">
      <a class="brand" href="/"><span class="sello">${icono("logo", 22)}</span>
        <span class="nombre"><small>Zapatería</small><strong>Paso Firme</strong></span></a>
      <nav class="nav" aria-label="Principal">
        ${MENU.map(([id, url, texto]) => `<a href="${url}" ${id === seccion ? 'aria-current="page"' : ""}>${icono(id)} ${texto}</a>`).join("")}
        <a href="#" id="descargar-excel">${icono("excel")} Descargar Excel</a>
        <a href="/docs">${icono("api")} API</a>
        <button type="button" class="theme-toggle" id="cambiar-tema"></button>
      </nav>
    </div></header>
    <main id="contenido"></main>`;
  montarInterruptorTema(document.getElementById("cambiar-tema"));
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

// El tema que se ve ahora: el elegido a mano (data-theme) o, si no hay, el del sistema.
const temaOscuro = () => {
  const elegido = document.documentElement.getAttribute("data-theme");
  return elegido ? elegido === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
};

// Interruptor claro/oscuro: la elección se guarda en el navegador y la aplica js/tema.js al cargar.
function montarInterruptorTema(boton) {
  const pintar = () => {
    const oscuro = temaOscuro();
    boton.innerHTML = icono(oscuro ? "sol" : "luna");
    boton.setAttribute("aria-label", oscuro ? "Cambiar al tema claro" : "Cambiar al tema oscuro");
    boton.title = boton.getAttribute("aria-label");
  };
  boton.addEventListener("click", () => {
    const nuevo = temaOscuro() ? "claro" : "oscuro";
    document.documentElement.setAttribute("data-theme", nuevo === "oscuro" ? "dark" : "light");
    try { localStorage.setItem("tema-paso-firme", nuevo); } catch (e) { /* sin almacenamiento */ }
    pintar();
  });
  // Si cambia el tema del sistema y no se ha elegido a mano, el icono también cambia.
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", pintar);
  pintar();
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
