"""Errores del negocio. Los controladores los convierten en respuestas HTTP (main.py)."""


class ReglaDeNegocio(ValueError):
    """Se ha intentado algo que las reglas de la zapatería no permiten (HTTP 422)."""


class NoEncontrado(LookupError):
    """No existe lo que se pide (HTTP 404)."""
