# Android Shell

Capacitor Android shell for packaging the Deadman frontend as a contest/demo
APK.

This directory should track Capacitor project files only. Generated Gradle
build outputs, local properties, copied public assets, APK/AAB files, and
machine-local Android artifacts are ignored.

Before building an APK, provide an explicit backend URL:

```bash
VITE_DEADMAN_API_BASE_URL=https://<backend-host>/api/deadman npm run android:debug
```

For local device recording, use `adb reverse` and a local backend:

```bash
adb reverse tcp:7860 tcp:7860
VITE_DEADMAN_API_BASE_URL=http://127.0.0.1:7860/api/deadman npm run android:debug
```

