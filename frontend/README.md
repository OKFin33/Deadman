# Deadman Frontend

Canonical standalone frontend package for Branch 3 / Deadman / `要是我来`.

Run from this directory:

```bash
npm install
npm run dev
npm test
npm run build
```

Android APK shell:

```bash
npm run build
npm run android:sync
npm run android:debug
```

`android:debug` uses `JAVA_HOME` when set, otherwise it tries Android Studio's
bundled JBR 21 on macOS. Capacitor Android 8 requires JDK 21+.

The APK must be built with an explicit backend URL:

```bash
VITE_DEADMAN_API_BASE_URL=https://<backend-host>/api/deadman npm run android:debug
```

For local-device recording, run the backend on port `7860`, use
`adb reverse tcp:7860 tcp:7860`, and build with:

```bash
VITE_DEADMAN_API_BASE_URL=http://127.0.0.1:7860/api/deadman npm run android:debug
```

The standalone app renders the mobile-first Branch 3 player as its first
screen. Public assets are served from `../assets/public`, preserving URLs such
as `/assets/branch3/companion/tomato-robes/webp/idle.webp`.

Current modules:

- `src/player/Branch3PlayerDemo.tsx`
- `src/companion/TomatoCompanion.tsx`
- `src/companion/tomatoCompanionMachine.ts`

The original OSeria-Alter workspace may still have legacy compatibility hosts,
but this standalone repo owns the frontend source and public asset boundary.

Do not commit provider keys or local `.env` files. A contest APK can be built
against a private backend URL, but the tracked repo should keep all secrets out
of source control. Use `env.example` as the public reference for frontend build
variables.
