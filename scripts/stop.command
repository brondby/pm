#!/usr/bin/env bash

# macOS launcher wrapper; delegates to the shared shell stop script.
DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$DIR/stop.sh"
