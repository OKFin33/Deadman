#!/usr/bin/env bash
set -euo pipefail

java_major_version() {
  local java_home="$1"
  local version
  version="$("$java_home/bin/javac" -version 2>&1 | awk '{print $2}')"
  echo "${version%%.*}"
}

if [[ -z "${JAVA_HOME:-}" || ! -x "$JAVA_HOME/bin/javac" || "$(java_major_version "$JAVA_HOME")" -lt 21 ]]; then
  for candidate in \
    "/Applications/Android Studio.app/Contents/jbr/Contents/Home" \
    "/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home" \
    "/opt/homebrew/opt/openjdk@21"; do
    if [[ -x "$candidate/bin/java" ]]; then
      export JAVA_HOME="$candidate"
      break
    fi
  done
fi

if [[ -z "${JAVA_HOME:-}" || ! -x "$JAVA_HOME/bin/javac" ]]; then
  echo "Android debug build requires JDK 21. Set JAVA_HOME to JDK 21 or install Android Studio's bundled JBR." >&2
  exit 1
fi

javac_version="$("$JAVA_HOME/bin/javac" -version 2>&1 | awk '{print $2}')"
major_version="${javac_version%%.*}"
if [[ "$major_version" != "21" && "$major_version" -lt 21 ]]; then
  echo "Android debug build requires JDK 21+. Current javac is $javac_version at $JAVA_HOME." >&2
  exit 1
fi

cd "$(dirname "$0")/../android"
./gradlew assembleDebug
