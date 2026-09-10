# Empaquetar `frontend/` como app de escritorio

La idea: **no duplicar el frontend**. El mismo código de `frontend/` se
sirve como página web normal Y se empaqueta como binario nativo. Dos rutas,
elige una según cómo les vaya a instalar el toolchain:

## Opción A (recomendada): Tauri

Más ligero que Electron (usa el WebView del sistema operativo en vez de
empaquetar Chromium completo), pero necesita Rust instalado.

**Pruébenlo ESTA NOCHE, no en medio del hackathon** — instalar Rust +
dependencias del sistema (WebView2 en Windows, WebKitGTK en Linux) la
primera vez puede tardar 20-40 min y es justo el tipo de sorpresa que no
quieres a las 3am del sábado.

```bash
# 1. Instalar Rust (una sola vez): https://rustup.rs
# 2. Desde la raíz del repo:
cd frontend
npm install @tauri-apps/cli@latest --save-dev
npx tauri init
#   - "What is your app name?" → el nombre del proyecto
#   - "Web assets location" → ../frontend/dist  (o "dist" si ya estás en frontend/)
#   - "Dev server URL" → http://localhost:5173
#   - "Dev command" → npm run dev
#   - "Build command" → npm run build

# Correr en modo desarrollo (abre una ventana nativa):
npx tauri dev

# Generar el instalador/binario final:
npx tauri build
```

Esto crea una carpeta `src-tauri/` con la config de Rust — no necesitas
escribir Rust tú mismo para un dashboard normal, solo configurar el
`tauri.conf.json` (íconos, tamaño de ventana, permisos).

## Opción B (fallback): Electron

Más pesado (empaqueta su propio Chromium, instaladores de 100+ MB) pero el
setup es 100% JavaScript, sin toolchain nuevo — mejor opción si Rust da
problemas y ya se les acaba el tiempo.

```bash
cd frontend
npm install --save-dev electron electron-builder
```

Crea `frontend/electron/main.js`:

```js
const { app, BrowserWindow } = require("electron");
const path = require("path");

function createWindow() {
  const win = new BrowserWindow({ width: 1000, height: 700 });
  win.loadFile(path.join(__dirname, "../dist/index.html"));
}

app.whenReady().then(createWindow);
```

Y en `package.json` agrega:

```json
"main": "electron/main.js",
"scripts": {
  "electron": "npm run build && electron ."
}
```

```bash
npm run electron
```

## Justificación para el pitch ("¿por qué no solo una página web?")

No basta con decir "porque sí" frente a los jueces — dale un motivo técnico
real, por ejemplo:

- Notificaciones nativas del sistema operativo para alertas financieras
  (una pestaña de navegador cerrada no puede avisarte nada).
- Un ícono en la bandeja del sistema con el balance/estado siempre visible,
  sin tener un tab abierto.
- Funciona sin conexión mostrando el último snapshot de datos (cache local).

Elige la que de verdad usen — un desktop app "porque se ve más técnico" sin
una razón de producto real se nota en el Q&A.
