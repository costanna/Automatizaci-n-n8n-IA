#!/bin/sh
# Arranque de n8n en la nube.
#
# La primera vez, importa los flujos (y las credenciales, si estan en la imagen).
# Las siguientes, no: asi los cambios de los flujos llegan con la PR, no en cada
# reinicio del contenedor.
#
# El marcador (un fichero vacio en el volumen) es lo que evita importar dos veces.
set -e

DATOS="${N8N_USER_FOLDER:-/home/node/.n8n}"
MARCADOR="$DATOS/.paso-firme-importado"

if [ -f "$MARCADOR" ]; then
  echo "[arranque] la instancia ya esta importada: no se toca nada"
else
  # Las credenciales (si vienen en la imagen y el sitio de la imagen las tiene).
  if [ -d /opt/paso-firme/credenciales ] && [ -n "$(ls -A /opt/paso-firme/credenciales 2>/dev/null)" ]; then
    echo "[arranque] importando las credenciales"
    n8n import:credentials --separate --input=/opt/paso-firme/credenciales || \
      echo "[arranque] AVISO: no se pudieron importar las credenciales"
  fi

  if [ -d /opt/paso-firme/workflows ] && [ -n "$(ls -A /opt/paso-firme/workflows 2>/dev/null)" ]; then
    echo "[arranque] importando los flujos"
    n8n import:workflow --separate --input=/opt/paso-firme/workflows || \
      echo "[arranque] AVISO: no se pudieron importar los flujos"
  fi

  touch "$MARCADOR"
  echo "[arranque] importacion terminada"
fi

exec n8n start
