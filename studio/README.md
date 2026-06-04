# Deadman Studio

Static producer-side prototype for assembling and reviewing Deadman moment
packs.

This is intentionally a lightweight static app:

- `src/` contains JSX source modules;
- `assets/` contains browser-ready JavaScript modules used by `index.html`;
- `index.html` can be opened or served without a bundler.

Because the browser-ready files are intentional static artifacts, do not treat
`studio/assets/*.js` as ordinary build trash unless the Studio packaging model
changes.

The Studio is producer-facing. It should not require provider keys in tracked
source, and it should not persist raw provider traces or media files outside
ignored local artifact paths.

