#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
export FREETARGET_MAC_SIGN_IDENTITY="${FREETARGET_MAC_SIGN_IDENTITY:-Developer ID Application: STRUVEDESIGNS LLC (PKH73HWP3S)}"
export FREETARGET_MAC_ICLOUD_PROFILE="${FREETARGET_MAC_ICLOUD_PROFILE:-$HOME/Downloads/freETarget_Mac_iCloud.provisionprofile}"
if [ ! -f "$FREETARGET_MAC_ICLOUD_PROFILE" ]; then
  echo "Put freETarget_Mac_iCloud.provisionprofile in Downloads, or set FREETARGET_MAC_ICLOUD_PROFILE."
  exit 1
fi
exec bash ./BUILD_MAC.command
