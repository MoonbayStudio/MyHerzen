# MyHerzen desktop (Windows, Linux)

Tauri 2 shell around the existing web client at `https://myherzen.moonbaystudio.ru/app/`.
The window hosts the remote page directly, so the desktop build always matches the
published site and needs no rebuild when the site changes. The site's own service
worker keeps the offline shell working inside the WebView. `dist/index.html` is the
local fallback page; it is not the running UI.

No Tauri commands are registered, so the remote page keeps browser-level privileges
only: it cannot read the filesystem or spawn processes.

## Artifacts

| Platform | Bundle | Engine |
| --- | --- | --- |
| Windows x86_64 | NSIS `.exe`, per-user install | WebView2 (preinstalled on Windows 10 21H2+ and Windows 11) |
| Linux x86_64 | `.deb`, `.AppImage` | WebKitGTK 4.1 |

Built on Ubuntu 22.04 (glibc 2.35), so the Linux artifacts run on Ubuntu 22.04+
and Debian 12+.

## Build

CI is the supported path: run the `desktop` workflow in GitHub Actions
(`workflow_dispatch`). It builds both platforms and uploads the bundles with their
SHA-256 sums.

Local Linux build on a Mac, through Docker:

```sh
docker build --platform linux/amd64 -f Dockerfile.linux -t myherzen-desktop-build:amd64 .
docker run --rm --platform linux/amd64 -v "$PWD:/src:ro" -v "$PWD/out:/out" \
  myherzen-desktop-build:amd64 bash -lc \
  'cp -r /src/. /build/ && cd /build && tauri build --bundles deb,appimage && \
   find src-tauri/target/release/bundle -type f \( -name "*.deb" -o -name "*.AppImage" \) -exec cp {} /out/ \;'
```

Windows bundles are not cross-built here; use the workflow.

Regenerate icons after changing `src-tauri/app-icon.png`:

```sh
tauri icon src-tauri/app-icon.png
```

Delete the generated `icons/android` and `icons/ios` directories afterwards — the
mobile clients keep their own assets.

## Code signing

Nothing is signed yet.

- **Linux** needs no signature. `.deb` and `.AppImage` install as they are.
- **Windows** is unsigned, so SmartScreen shows «Неизвестный издатель» on first run;
  the user has to choose «Подробнее» → «Выполнить в любом случае». Publish the
  SHA-256 next to the download, the same way the DMG and APK are published.
  Signing requires a code-signing certificate; since June 2023 the private key must
  live on a hardware token or HSM, which is why this is a separate decision rather
  than a CI secret.
