#!/usr/bin/env bash
# Detect hardcoded user-facing strings in Dart source files.
#
# Searches for Text('...') and Text("...") patterns in lib/,
# excluding generated files (*.g.dart, *.freezed.dart).
#
# Exits 0 with a summary. Does not fail the build (advisory only),
# since some Text() calls are intentionally hardcoded (icons, debug).
#
# Usage: bash scripts/check_hardcoded_strings.sh

set -euo pipefail

SEARCH_DIR="lib"

echo "Scanning $SEARCH_DIR for hardcoded Text() strings..."
echo

# Match Text('literal') or Text("literal") with at least 2 alpha chars.
# Uses grep -rP (Perl regex) for portability (no rg dependency).
MATCHES=$(grep -rPc \
  "Text\(['\"][A-Za-z ]{2,}" \
  --include='*.dart' \
  --exclude='*.g.dart' \
  --exclude='*.freezed.dart' \
  "$SEARCH_DIR" 2>/dev/null \
  | grep -v ':0$' || true)

if [ -z "$MATCHES" ]; then
  echo "No hardcoded Text() strings found."
  exit 0
fi

TOTAL=0
echo "File                                                  Count"
echo "------------------------------------------------------------"
while IFS=: read -r file count; do
  printf "%-55s %5d\n" "$file" "$count"
  TOTAL=$((TOTAL + count))
done <<< "$MATCHES"

echo "------------------------------------------------------------"
echo "Total hardcoded Text() strings: $TOTAL"
echo
echo "Consider replacing with context.l10n.keyName references."
exit 0
