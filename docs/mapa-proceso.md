# Mapa del proceso de apartado

## 1. Cómo se hace hoy (a mano)

```
   Cliente            Dependienta              Libreta / Excel              Marisa
      |                    |                          |                      |
      | "quiero estos      |                          |                      |
      |  zapatos, aparto" |                          |                      |
      |------------------->|                          |                      |
      |                    |-- anota en la libreta -->|                      |
      |                    |                          |                      |
      |                    | "dame 20 de unpaid"     |                      |
      |------------------->|                          |                      |
      |                    |-- anota el abono ------>|                      |
      |                    |                          |                      |
      |                    |                          |-- suma a mano ------->|
      |                    |                          |   "¿cuánto he       |
      |                    |                          |    cobrado este     |
      |                    |                          |    mes?"             |
      |                    |                          |<--------------------|
      |                    |                          |  (calculadora,      |
      |                    |                          |   a veces tarde     |
      |                    |                          |   y con errores)    |
      |                    |                          |                      |
      | 3 meses despues   |                          |                      |
      |  sin pagar        |                          |                      |
      |------------------->|                          |                      |
      |                    |-- "este se le pasó" ---->|                      |
      |                    |   (busca en la libreta  |                      |
      |                    |    si se le abona algo)  |                      |
      |                    |                          |-- "no me acuerdo     |
      |                    |                          |   de quien era" ---->|
```

**Lo que falla hoy**

| Problema | Consecuencia |
|---|---|
| El plazo se apunta a mano | Apartados que se vencen y nadie se entera: los zapatos se quedan en el almacén |
| No se avisa a los clientes | El cliente se entera tarde y hay que llamarlo por teléfono |
| La caja se suma a mano | Errores de cálculo y cierre tarde |
| No se sabe cuánto queda por cobrar | Marisa no sabe si el mes va bien |
| Los pagos por Bizum se miran en el banco | Se adivina de quién es cada pago y algunos se pierden |

## 2. Cómo queda automatizado

```
   Cliente                  App de la tienda                n8n                    Marisa
      |                          |                           |                       |
      |  aparta por la pantalla  |                           |                       |
      |------------------------->|                           |                       |
      |                          |-- POST /webhook/tienda -->|  00 despachador      |
      |                          |   {evento, datos}         |  Switch por evento    |
      |                          |                           |                       |
      |                          |                           |-- flujo 01 ----------|--> email al cliente
      |                          |                           |   (que ha apartado,  |
      |                          |                           |    cuanto falta y    |
      |                          |                           |    hasta cuando)     |
      |                          |                           |                       |
      |  paga un abono          |                           |                       |
      |------------------------->|                           |                       |
      |                          |-- POST /webhook/tienda -->|  00 -> flujo 02      |
      |                          |                           |--> email con el      |
      |                          |                           |    recibo (o aviso   |
      |                          |                           |    de que ya puede   |
      |                          |                           |    recoger)          |
      |                          |                           |                       |
      |  paga por Bizum         |                           |                       |
      |   desde casa             |                           |                       |
      |        |                 |                           |                       |
      |        |  aviso del banco (IMAP) -->|  03 abonos a        |                       |
      |        |                          |     distancia        |                       |
      |        |                          |   el modelo extrae   |                       |
      |        |                          |   flujo: decide      |                       |
      |        |                          |        |             |                       |
      |        |                          |        | POST /api |                       |
      |        |                          |        +----------->|  se registra el abono |
      |        |                          |        |             |--> recibo al cliente  |
      |        |                          |        |             |                       |
      |        |                          |        | si hay dudas |                       |
      |        |                          |        +------------>|--> email a Marisa     |
      |                          |                           |   (no se registra)   |
      |                          |                           |                       |
      |  cada mañana             |                           |  06 recordatorios    |                       |
      |                          |<-- GET /api/apartados ----|                       |
      |                          |                           |  vence por API los   |                       |
      |  <-- email: te vence -----|                           |  que estan fuera     |--> email a Marisa
      |      en 7 dias y 1 dia  |                           |  de plazo            |   (zapatos que
      |                          |                           |                       |    vuelven a la venta)
      |  <-- email: tu vale -----|                           |                       |
      |                          |                           |                       |
      |                          |                           |  05 cierre diario    |--> resumen cada noche
      |                          |                           |  07 informe mensual  |--> informe el dia 1
      |                          |                           |  04 venta grande     |--> aviso de venta
      |                          |                           |  08 error workflow   |--> aviso de error
```

## 3. Diagrama BPMN del proceso automatizado

```mermaid
flowchart TD
    subgraph Tienda[App de la tienda]
        A[Cliente aparta un par] --> B[Se crea el apartado con su abono inicial]
        B --> C{{Abono por debajo de 5 EUR?}}
        C -- si --> Z[Error 422: no se puede crear]
        C -- no --> D[Apartado activo, fecha limite = +90 dias]
        D --> E{{El abono liquida el apartado?}}
        E -- si --> F[Estado liquidado]
        E -- no --> G[Estado activo]
        F --> H[La app avisa a n8n por webhook]
        G --> H
    end

    subgraph N8n[n8n]
        H --> I[00 Despachador: Switch por evento]
        I --> J[01 Confirmacion al cliente]
        I --> K[02 Recibo del abono]
        I --> L[04 Aviso de venta grande]
        I --> M[03 Abonos a distancia]
        I --> N[08 Avisos de error]

        M --> O[El modelo extrae ordenante, importe y concepto]
        O --> P[Busca el apartado por API]
        P --> Q{Un apartado claro?}
        Q -- no --> R[No se registra: se pregunta a Marisa]
        Q -- si --> S{Cabe el importe y esta en plazo?}
        S -- no --> R
        S -- si --> T[Registra el abono por API]
        T --> K

        U[06 Cada mañana 08:30] --> V{Clasifica los apartados activos]
        V --> W[Avisa de los que vencen en 7 y en 1 dia]
        V --> X[Vence por API los que estan fuera de plazo]
        X --> Y[La app genera el vale y se avisa a cliente y tienda]

        Y2[05 Cada noche 23:00] --> Z2[Cierre con ventas, abonos y forma de pago]
        Y3[07 Dia 1 de cada mes] --> Z3[Informe mensual y total pendiente]
    end

    B --> H
    J --> M1[Email al cliente]
    K --> M2[Email al cliente]
    L --> M3[Email a Marisa]
    R --> M4[Email a Marisa: que aparto es]
    W --> M5[Email al cliente: te va a vencer]
    X --> M6[Email al cliente con el vale y a la tienda]
    Z2 --> M7[Resumen a Marisa]
    Z3 --> M8[Informe a Marisa]
    N --> M9[Email a Marisa: flujo, paso y error]
```

## 4. Reglas de negocio, antes y después

| Regla | Antes | Después |
|---|---|---|
| Abono inicial mínimo 5 € | Lo apunta la dependienta | Lo aplica la app (error 422) |
| Plazo máximo 90 días | Fecha en la libreta | `fecha_limite = fecha + 90 días`, calculada por la app |
| No abonar de más | Lo comprueba la dependienta | Lo aplica la app; el flujo 3 avisa a Marisa antes de intentarlo |
| Apartado liquidado | Anotado a mano | La app lo marca sola en cuanto el pendiente llega a 0 |
| Apartado vencido | "Se le pasó" | El flujo 6 lo vence por API y la app genera el vale |
| Ventas del día | Suma a mano con calculadora | El flujo 5 suma las ventas y los abonos del día |
| Recaudación mensual | Columna del Excel | El flujo 7 la saca de la API el día 1 |
| Pendiente de cobro | No se sabe | El flujo 7 lo suma de los apartados activos |
| Pagos por Bizum | Avisos del banco a mano | El flujo 3 los registra, o pregunta a Marisa |

## 5. Lo que sigue siendo de la tienda

- La app sigue siendo la que guarda los datos y aplica las reglas: n8n no calcula importes de
  dinero, los lee.
- La dependienta sigue viendo la misma pantalla: no hemos cambiado la app.
- La libreta sigue existiendo durante la transición, pero ya no es la fuente de verdad.
