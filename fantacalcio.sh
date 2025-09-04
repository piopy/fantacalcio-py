#!/bin/bash
cd "$(dirname "$0")"
poetry run python cli.py "$@"