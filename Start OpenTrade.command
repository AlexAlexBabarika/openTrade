#!/bin/bash

set -u
cd -- "$(dirname -- "$0")"
export OPENTRADE_LAUNCHED_FROM_GUI=1
exec ./scripts/start-opentrade.sh
