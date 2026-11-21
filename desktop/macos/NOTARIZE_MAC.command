#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
app="release/mac/freETarget Minimalist.app"
profile="${FREETARGET_NOTARY_PROFILE:-freETarget-notary}"
submission="release/mac/freETarget-clean-submission.zip"
final="release/mac/freETarget-Minimalist-0.3.11-beta.1-macOS-Notarized.zip"
if [ ! -d "$app" ]; then echo "Run BUILD_SIGNED_MAC.command first."; exit 1; fi
mkdir -p .build/notarization
codesign --verify --deep --strict --verbose=2 "$app"
ditto -c -k --sequesterRsrc --keepParent "$app" "$submission"
xcrun notarytool submit "$submission" --keychain-profile "$profile" --wait --output-format json > .build/notarization/result.json
cat .build/notarization/result.json
source tools/select_python.sh
ft_select_universal_python
"$FT_PYTHON" - <<'CHECK'
import json
from pathlib import Path
result=json.loads(Path('.build/notarization/result.json').read_text())
if result.get('status') != 'Accepted':
    raise SystemExit('Not accepted. Keep the submission ID and retrieve its notarytool log.')
CHECK
xcrun stapler staple "$app"
xcrun stapler validate "$app"
spctl --assess --type execute --verbose=4 --ignore-cache --no-cache "$app"
syspolicy_check distribution "$app"
ditto -c -k --sequesterRsrc --keepParent "$app" "$final"
echo "Verified distribution ZIP: $final"
