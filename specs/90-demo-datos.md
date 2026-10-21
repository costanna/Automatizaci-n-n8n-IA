# Spec · 90 Datos de demo

| | |
|---|---|
| **Flujo** | `workflows/90-demo-datos.json` |
| **Nivel** | Entregable: *un flujo de prueba que crea datos de ejemplo en la app por API* |
| **Disparador** | Manual (Manual Trigger): se ejecuta desde el editor de n8n |

## Objetivo

Poder enseñar el proyecto sin depender de que la base de datos tenga lo que hace falta en ese
momento: el flujo crea apartados con las características que cada automatización necesita
probar.

## Entradas

Ninguna: el propio flujo trae los datos de ejemplo.

## Salidas

| Tipo | Contenido |
|---|---|
| Apartados creados | 5, con las fechas y los importes que pide cada caso |
| Resumen a Marisa | Cuántos se han creado y cómo queda la tienda |

## Apartados que crea

| Cliente | Producto | Precio | Abono | Fecha | Para probar |
|---|---|---|---|---|---|
| `Cliente Demo Abono` | Botín piel marrón | 89,90 € | 20 € | hoy | La confirmación (HU-01) y el recibo (HU-02) |
| `Cliente Demo Pendiente` | Botín piel marrón | 64,50 € | 10 € | hoy | Un apartado con pendiente para el cierre y el informe |
| `Cliente Demo Liquidado` | Botín piel marrón | 45,00 € | 45,00 € | hoy | El aviso de liquidación |
| `Cliente Demo Vencido` | Botín piel marrón | 55,00 € | 5 € | hace 120 días | El vencimiento y el vale (HU-07) |
| `Cliente Demo Proximo` | Botín piel marrón | 72,00 € | 15 € | hace 83 días | El recordatorio de 7 días (HU-06) |

## Pasos

1. **Manual Trigger**.
2. **Preparar datos de demo** (Code): monta los cinco apartados con su fecha original.
3. **Crear apartado de demo** (HTTP Request `POST /api/apartados`): uno por item.
4. **Preparar el estado** (Code): un único item, para que la siguiente llamada sea una sola.
5. **Ver el estado de la tienda** (HTTP Request `GET /api/apartados/resumen`).
6. **Preparar resumen** (Code) y **Notificar** (subflujo): Marisa recibe la lista de lo creado.

## Reglas

- Los apartados se crean **por API**, con su fecha original, para que los flujos programados
  (cierre, recordatorios, informe) tengan algo que mirar.
- Los correos de ejemplo son `@example.com`: **no se envía ningún correo a una dirección real**.
- Si se ejecuta dos veces, se crean apartados nuevos con el mismo nombre: no es un problema
  (son datos de prueba), pero conviene reiniciar la tienda antes de una demo.

## Casos de error

| Caso | Comportamiento |
|---|---|
| La app no responde | El nodo HTTP devuelve el error y el flujo lo cuenta en el resumen |
| Un abono inicial por debajo de 5 € | La API responde 422 y ese apartado no se crea |

## Criterios de aceptación

- [ ] El flujo crea apartados de ejemplo en la app por API.
- [ ] Hay un apartado para cada caso que necesitan los demás flujos.
- [ ] Marisa recibe un resumen con lo que se ha creado.

## Datos de prueba

No tiene datos de entrada: los trae el propio flujo. Para verlos:

```bash
python scripts/probar_flujos.py
```
