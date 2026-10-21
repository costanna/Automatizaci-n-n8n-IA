"""Datos de ejemplo: los últimos meses de la tienda, con fechas relativas a hoy.

Así siempre hay apartados que vencen en 7 días, en 1 día, fuera de plazo, liquidados,
y ventas y abonos de hoy y de los meses anteriores para cierres e informes.
"""

import random
from datetime import date, timedelta

from models import abono, apartado, venta

CLIENTES = [
    "Carmen Ruiz", "Jorge Martín", "Lucía Gómez", "Ana Torres", "Pedro Sanz", "Rosa Díaz",
    "Miguel Ángel López", "Sofía Navarro", "Javier Moreno", "Elena Castro", "David Romero",
    "Laura Ortega", "Pablo Rubio", "Marta Molina", "Sergio Delgado", "Paula Ramos",
    "Raúl Iglesias", "Cristina Gil", "Alberto Vázquez", "Nuria Serrano", "Iván Blanco",
    "Beatriz Medina", "Óscar Garrido", "Silvia Cortés",
]
PRODUCTOS = [
    ("Botín piel marrón", 89.90), ("Zapatilla running azul", 64.50), ("Sandalia tacón negra", 45.00),
    ("Mocasín ante", 72.00), ("Bota agua niño", 29.95), ("Zapato vestir hombre", 95.00),
    ("Deportiva blanca", 55.00), ("Bailarina roja", 39.90), ("Bota montaña", 79.90),
    ("Botín piel negro", 92.00), ("Zueco sanitario", 34.50), ("Bota alta mujer", 119.00),
]
VENTAS = [
    ("Calcetines pack 3", 6.50), ("Plantillas gel", 12.00), ("Crema calzado", 4.50),
    ("Zapatilla casa", 18.95), ("Cordones", 2.50), ("Deportiva niño", 32.00),
    ("Bota montaña", 79.90), ("Botín piel negro", 92.00), ("Sandalia playa", 14.90),
]
FORMAS = ["efectivo", "efectivo", "tarjeta", "tarjeta", "bizum"]

# Días transcurridos desde que se hizo cada apartado y cuánto se ha ido pagando.
# 83 → vence en 7 días, 89 → vence mañana, más de 90 → fuera de plazo (sigue activo hasta que n8n lo venza).
ESCENARIOS = [
    (2, "parcial"), (5, "parcial"), (9, "parcial"), (15, "parcial"), (22, "parcial"), (30, "parcial"),
    (41, "parcial"), (50, "parcial"), (64, "parcial"), (75, "parcial"),
    (83, "parcial"), (83, "parcial"), (89, "parcial"),
    (96, "parcial"), (104, "parcial"), (118, "solo_inicial"),
    (12, "liquidado"), (28, "liquidado"), (45, "liquidado"), (60, "liquidado"), (88, "liquidado"),
    (130, "vencido"), (0, "solo_inicial"), (1, "parcial"),
]


def cargar():
    crear_apartado, registrar_abono = apartado.crear, abono.registrar
    registrar_venta, vencer_apartado = venta.registrar, apartado.vencer
    rnd = random.Random(42)
    hoy = date.today()

    for i, (dias, tipo) in enumerate(ESCENARIOS):
        cliente = CLIENTES[i % len(CLIENTES)]
        producto, precio = rnd.choice(PRODUCTOS)
        fecha = hoy - timedelta(days=dias)
        a = crear_apartado(
            cliente=cliente,
            telefono=f"600 000 {i + 1:03d}",
            email=f"{cliente.split()[0].lower()}{i + 1}@example.com",
            producto=producto, talla=str(rnd.randint(35, 45)), precio=precio,
            abono_inicial=rnd.choice([5, 5, 10, 15, 20]), forma_pago=rnd.choice(FORMAS), fecha=fecha,
        )
        if tipo == "solo_inicial":
            continue
        dias_pago = sorted(rnd.sample(range(1, max(dias, 2)), k=min(3, max(dias - 1, 1)))) if dias > 1 else []
        for d in dias_pago:
            if d > min(dias, 90):
                break
            pendiente = a["pendiente"]
            importe = pendiente if tipo == "liquidado" and d == dias_pago[-1] else round(min(pendiente, rnd.choice([5, 10, 15, 20])), 2)
            if importe <= 0 or a["estado"] != "activo":
                break
            a = registrar_abono(a["id"], importe, rnd.choice(FORMAS), fecha + timedelta(days=d))
        if tipo == "vencido":
            vencer_apartado(a["id"])

    # Ventas directas de los últimos 75 días, también de hoy (para el cierre diario).
    for d in range(75, -1, -1):
        dia = hoy - timedelta(days=d)
        if dia.weekday() == 6:  # domingo cerrado
            continue
        for _ in range(rnd.randint(2, 6)):
            concepto, importe = rnd.choice(VENTAS)
            registrar_venta(f"{concepto} T{rnd.randint(30, 45)}" if importe > 20 else concepto,
                            importe, rnd.choice(FORMAS), dia)
