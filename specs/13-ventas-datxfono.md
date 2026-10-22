# Spec · 13 Ventas del datáfono

| | |
|---|---|
| **Flujo** | `workflows/13-ventas-datxfono.json` |
| **Historia** | HU-13 · Entrada automática de datos 🟠 |
| **Disparador** | Programado: cada noche a las **02:00** (Europe/Madrid) |
| **Datos** | `data/datxfono.csv` (el volcado del datáfono) |

## Objetivo

Que los cobros con tarjeta del día entren solos en la tienda como ventas, sin que la dependienta
los apunte a mano y sin que se repitan.

## Entradas

El CSV del datáfono (`data/datxfono.csv`), una línea por cobro:

```csv
fecha,hora,importe,tarjeta,concepto
2026-10-20,10:15,79.90,****4321,Bota montaña T41
2026-10-20,11:12,64.50,****9010,Zapatilla running azul T43
```

## Salidas

| Tipo | Contenido |
|---|---|
| Ventas | Una venta por cobro del CSV, con `forma_pago: tarjeta` y la fecha del cobro |
| Aviso a la tienda | Cuántos cobros se han importado, cuántos se han omitido y el total |
| Histórico | Las claves de los cobros ya importados (en los *static data* del flujo) |

## Pasos

1. **Cada noche a las 02:00** (Schedule Trigger).
2. **Fecha de la importacion** (Code): el día de hoy y hace 30 días.
3. **Ventas que ya tiene la tienda** (HTTP Request): las ventas de los últimos 30 días.
4. **Leer el CSV del datáfono** + **Parsear el CSV** (Read Binary File + Spreadsheet File).
5. **Preparar las ventas** (Code): un item por cobro, quitando los que ya están:
   - **Clave de cobro**: `fecha|hora|importe|últimos4 de la tarjeta`. Con esa clave no se importa
     dos veces el mismo cobro aunque el flujo se ejecute muchas veces.
   - Además se descartan los cobros que ya están en la tienda (mismo día, mismo importe y mismo
     concepto), por si el datáfono vuelve a volcar el mismo archivo.
6. **Registrar las ventas** (HTTP Request `POST /api/ventas`): una petición por cobro.
7. **Guardar y resumir la importacion** (Code): guarda las claves en los *static data* y resume.
8. **Avisar a la tienda**: el resumen de la importación.

## Reglas

- **La importación a mano (`POST /webhook/datxfono`) va protegida** con la cabecera
  `X-Webhook-Token` (credencial `Webhooks - Tienda`): sin ella, n8n responde 403.
- **No se duplica nada**: la clave de cobro se guarda entre ejecuciones y además se compara con
  lo que ya tiene la tienda.
- Los importes del CSV pueden venir en formato español (`1.842,30`) o inglés (`89.90`): se
  normalizan.
- La fecha del cobro es la del datáfono, no la de la importación.
- R-A1: los importes se copian del CSV; la app no calcula nada aquí (es una venta directa).

## Casos de error

| Caso | Comportamiento |
|---|---|
| El CSV no está | El flujo sigue y avisa de que no hay nada que importar |
| Una línea con fecha o importe ilegibles | Se omite y se cuenta en el resumen |
| La API rechaza una venta (422) | Se cuenta como error y el resumen lo dice |
| El CSV trae cobros de hace semanas | Se importan (la tienda los necesita), pero el histórico se recorta a los 2.000 últimos |

## Criterios de aceptación

- [ ] Cada noche se importa el CSV de cobros con tarjeta como ventas.
- [ ] Ejecutarlo dos veces no crea ventas de más.
- [ ] La tienda recibe un resumen de lo importado.

## Datos de prueba

`data/datxfono.csv` (7 cobros de ejemplo). La prueba:

```bash
python scripts/probar_flujos.py --flujo 13
```

## Credenciales

| Credencial | Tipo | Dónde |
|---|---|---|
| `Tienda - API` | Header Auth | Leer las ventas y registrar las nuevas |
| `SMTP - Paso Firme` | SMTP | El resumen a la tienda (vía `SUB · Notificar`) |
