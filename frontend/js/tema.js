// Tema claro u oscuro. Se carga en el <head> como script normal (no módulo) para aplicar el tema
// antes de pintar la página: si no, se ve un destello del otro tema.
// Sin elección guardada no se pone data-theme y el CSS sigue al sistema (prefers-color-scheme).
(function () {
  try {
    const guardado = localStorage.getItem("tema-paso-firme");
    if (guardado === "claro") document.documentElement.setAttribute("data-theme", "light");
    if (guardado === "oscuro") document.documentElement.setAttribute("data-theme", "dark");
  } catch (e) {
    // Sin almacenamiento (modo privado): se queda el tema del sistema.
  }
})();
