// Página «Ventas directas»: formulario para registrar una venta y el historial, paginado.

import { api } from "../api.js";
import { avisoDeLaDireccion, mostrarAviso, montarLayout } from "../layout.js";
import { FORMAS_PAGO, esc, euros, fecha, icono, opcionesFormaPago, paginacion } from "../ui.js";

const principal = montarLayout("ventas");
const POR_PAGINA = 25;
let pagina = Number(new URLSearchParams(location.search).get("pagina")) || 1;
const capitalizar = (t) => t.charAt(0).toUpperCase() + t.slice(1);

async function pintar() {
  let { items, total } = await api.ventas({ pagina, porPagina: POR_PAGINA });
  const paginas = Math.max(1, Math.ceil(total / POR_PAGINA));
  if (pagina > paginas) {
    pagina = paginas;
    ({ items, total } = await api.ventas({ pagina, porPagina: POR_PAGINA }));
  }
  principal.innerHTML = `
    <div class="page-head"><h1>Ventas directas</h1></div>
    <div class="layout-2" style="grid-template-columns: 1fr;">
      <form id="formulario" class="card card-body" aria-label="Registrar venta">
        <div class="grid" style="align-items:end">
          <div><label for="concepto">Concepto</label><input id="concepto" name="concepto" required placeholder="Bota montaña T41"></div>
          <div><label for="importe">Importe (€)</label><input id="importe" name="importe" type="number" step="0.01" min="0.01" required></div>
          <div><label for="forma_pago">Forma de pago</label><select id="forma_pago" name="forma_pago">${opcionesFormaPago(FORMAS_PAGO)}</select></div>
          <div><button class="btn btn-primary" type="submit" style="width:100%">${icono("plus")} Registrar venta</button></div>
        </div>
      </form>
      <section class="card" aria-label="Historial de ventas">
        <div class="table-wrap">
          <table>
            <thead><tr><th>Fecha</th><th>Concepto</th><th>Forma de pago</th><th class="num">Importe</th></tr></thead>
            <tbody>${items.map((v) => `<tr><td>${fecha(v.fecha)}</td><td>${esc(v.concepto)}</td><td>${esc(capitalizar(v.forma_pago))}</td><td class="num">${euros(v.importe)}</td></tr>`).join("")}</tbody>
          </table>
          ${items.length ? "" : '<div class="empty">Todavía no hay ventas. Registra la primera con el formulario de arriba.</div>'}
        </div>
        ${paginacion(pagina, paginas, total, "/ventas?")}
      </section>
    </div>`;
  document.getElementById("formulario").addEventListener("submit", registrar);
}

async function registrar(evento) {
  evento.preventDefault();
  const f = new FormData(evento.target);
  const boton = evento.target.querySelector("button[type=submit]");
  boton.disabled = true;
  try {
    await api.registrarVenta({ concepto: f.get("concepto"), importe: Number(f.get("importe")), forma_pago: f.get("forma_pago") });
    location.href = `/ventas?ok=${encodeURIComponent("Venta registrada")}`;
  } catch (e) {
    mostrarAviso("error", e.message);
    boton.disabled = false;
  }
}

pintar().then(avisoDeLaDireccion).catch((e) => mostrarAviso("error", e.message));
