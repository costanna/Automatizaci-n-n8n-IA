#!/bin/sh
# Arranque de n8n en la nube.
#
# Si la instancia está vacía (no hay base de datos), se importan los flujos que
# viajan en la imagen. Si ya hay datos, no se importa nada: así los cambios de
# los flujos se despliegan con la PR, no en cada reinicio.
set -e

DATOS="${N8N_USER_FOLDER:-/home/node/.n8n}"

if [ -z "$DB_TYPE" ] || [ "$DB_TYPE" = "sqlite" ]; then
  if [ ! -f "$DATOS/database.sqlite" ]; then
    echo "[arranque] instancia vacia: importando los flujos"
    n8n import:workflow --separate --input=/opt/paso-firme/workflows
  else
    echo "[arranque] la instancia ya tiene datos: no se importan los flujos"
  fi
else
  echo "[arranque] base de datos en Postgres: importa los flujos a mano con scripts/enlazar_flujos.py"
fi

exec n8n start
