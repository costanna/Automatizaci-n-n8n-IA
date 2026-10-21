"""SERVICIO · Avisar a n8n por webhook cuando pasa algo en la tienda."""

import json
import logging
import urllib.request

import config

log = logging.getLogger("tienda")


def avisar(evento, datos):
    """Envía el evento a n8n. Si n8n no responde, la tienda sigue funcionando."""
    if not config.N8N_WEBHOOK_URL:
        return
    cuerpo = json.dumps({"evento": evento, "datos": datos}, default=str).encode()
    peticion = urllib.request.Request(config.N8N_WEBHOOK_URL, cuerpo, {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(peticion, timeout=5)
    except Exception as e:
        log.warning("No se pudo avisar a n8n (%s): %s", evento, e)
