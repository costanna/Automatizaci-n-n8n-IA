#!/bin/sh
# Conecta un bot de Telegram con n8n.
#
# Telegram entrega los updates a una URL que le registres (setWebhook). Este script
# hace esa llamada con la URL de n8n y el token secreto que comprueba el webhook.
#
# Uso:
#   scripts/conectar_bot_telegram.sh <token-del-bot> [url-n8n] [secreto]
#
# Ejemplo (en local, con el mock de Telegram):
#   scripts/conectar_bot_telegram.sh 123456:ABC http://localhost:5678/webhook/telegram mi-secreto
#
# Ejemplo (en la nube, con un bot de verdad):
#   scripts/conectar_bot_telegram.sh 123456:ABC https://mi-n8n.onrender.com/webhook/telegram mi-secreto
#
# Para ver los updates que van y vienen:
#   curl "https://api.telegram.org/bot<token>/getUpdates"
set -e

TOKEN="${1:-}"
URL="${2:-http://localhost:5678/webhook/telegram}"
SECRETO="${3:-$(grep '^TELEGRAM_SECRET_TOKEN=' data/config.csv 2>/dev/null | cut -d, -f2-)}"

if [ -z "$TOKEN" ]; then
  echo "Uso: $0 <token-del-bot> [url-n8n] [secreto]" >&2
  exit 1
fi

if [ -z "$SECRETO" ]; then
  echo "Falta el token secreto: ponlo en el tercer argumento o en data/config.csv (TELEGRAM_SECRET_TOKEN)" >&2
  exit 1
fi

echo "Registrando el webhook en Telegram..."
echo "  url:     $URL"
echo "  secreto: ***"

curl -sS -X POST "https://api.telegram.org/bot${TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${URL}\",\"secret_token\":\"${SECRETO}\",\"allowed_updates\":[\"message\"],\"drop_pending_updates\":false}" \
  | sed 's/"ok":true/"ok": true/'

echo
echo "Comprobando:"
curl -sS "https://api.telegram.org/bot${TOKEN}/getWebhookInfo"
echo
echo "Listo. Escribe al bot y mira las ejecuciones en n8n."
