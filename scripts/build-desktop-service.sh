#!/bin/sh
# Freeze the local service into build/service/daywright-service for the desktop app.
# It builds in its own environment under build/, so the development .venv12 is never changed.
set -eu
cd "$(dirname "$0")/.."

environment=build/desktop-venv
if [ ! -x "$environment/bin/python" ]; then
  python3.12 -m venv "$environment"
fi
"$environment/bin/pip" install --quiet --disable-pip-version-check -r backend/requirements-desktop.txt

# sqlite-vec ships its loadable extension as package data, and faster-whisper its voice-activity model.
"$environment/bin/pyinstaller" --noconfirm --clean --log-level WARN \
  --name daywright-service \
  --distpath build/service --workpath build/pyinstaller --specpath build/pyinstaller \
  --paths "$(pwd)" \
  --collect-all sqlite_vec \
  --collect-data faster_whisper \
  backend/desktop_service.py
