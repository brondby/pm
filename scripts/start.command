#!/usr/bin/env bash

# macOS launcher wrapper; delegates to the shared shell start script.
DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$DIR/start.sh"
