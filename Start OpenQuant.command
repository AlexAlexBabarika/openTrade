#!/bin/bash

set -u
cd -- "$(dirname -- "$0")"
export OPENQUANT_LAUNCHED_FROM_GUI=1
exec ./scripts/start-openquant.sh
