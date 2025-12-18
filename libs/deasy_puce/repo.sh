#!/bin/bash
set -e
# Conexión al índice (idempotente)
devpi use http://localhost:3141/javier/dev
# Asegurar login
devpi login javier --password=1234 || true
# Construir y subir
pipenv run python -m build
devpi upload
