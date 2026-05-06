# 🔔 Monitor de Pagos — Telegram Bot

Script que monitorea una bandeja de Gmail en busca de correos de un remitente específico y envía una notificación a Telegram con los datos del pago detectado (monto, nombre, fecha).

---

## 📁 Estructura del proyecto

```
monitor-pagos/
├── buscar_correo.py   # Script principal
├── requirements.txt   # Dependencias Python
├── render.yaml        # Configuración para Render
├── .env.example       # Plantilla de variables de entorno
├── .gitignore         # Archivos ignorados por Git
└── README.md
```

---

## 🚀 Despliegue en Render via GitHub

### Paso 1 — Subir el proyecto a GitHub

1. Crea un repositorio **privado** en [github.com](https://github.com) (privado para proteger tu configuración).
2. Desde tu computadora, ejecuta:

```bash
git init
git add .
git commit -m "Primer commit — Monitor de Pagos"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

---

### Paso 2 — Crear el servicio en Render

1. Entra a [render.com](https://render.com) y crea una cuenta (es gratis).
2. En el Dashboard, haz clic en **"New +"** → **"Background Worker"**.
3. Conecta tu cuenta de GitHub y selecciona el repositorio que acabas de crear.
4. Render detectará automáticamente el archivo `render.yaml`. Confirma los valores:
   - **Name:** `monitor-pagos`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python buscar_correo.py`

---

### Paso 3 — Configurar las Variables de Entorno en Render

En la sección **"Environment"** del servicio en Render, agrega estas variables una por una:

| Variable             | Descripción                                              |
|----------------------|----------------------------------------------------------|
| `EMAIL_CUENTA`       | Tu correo Gmail que recibe los pagos                     |
| `EMAIL_PASSWORD`     | Contraseña de aplicación de Gmail (ver nota abajo)       |
| `EMAIL_REMITENTE`    | El correo del remitente que envía los pagos              |
| `TELEGRAM_TOKEN`     | Token del bot de Telegram (obtenido con @BotFather)      |
| `TELEGRAM_CHAT_ID`   | ID del chat donde llegan las notificaciones              |
| `INTERVALO_BUSQUEDA` | Segundos entre cada revisión (por defecto: `10`)         |

> ⚠️ **IMPORTANTE:** Nunca escribas estas credenciales directamente en el código ni las subas a GitHub.

---

### 🔑 Cómo obtener la Contraseña de Aplicación de Gmail

Gmail no permite usar tu contraseña normal con IMAP. Necesitas una **Contraseña de Aplicación**:

1. Ve a tu cuenta de Google → **Seguridad**.
2. Activa la **Verificación en dos pasos** (si no la tienes).
3. Busca **"Contraseñas de aplicación"**.
4. Crea una nueva para "Correo" → "Otro" → ponle un nombre (ej: `monitor-render`).
5. Google te dará una clave de 16 caracteres — esa es tu `EMAIL_PASSWORD`.

---

### 🤖 Cómo obtener el Token y Chat ID de Telegram

**Token del bot:**
1. Abre Telegram y busca **@BotFather**.
2. Envía `/newbot`, sigue las instrucciones.
3. BotFather te dará el token (formato: `123456789:ABC-...`).

**Chat ID:**
1. Escribe un mensaje a tu bot.
2. Visita: `https://api.telegram.org/botTU_TOKEN/getUpdates`
3. Busca el campo `"chat":{"id": XXXXXXXXX}` — ese número es tu `TELEGRAM_CHAT_ID`.

---

### Paso 4 — Hacer el Deploy

1. Haz clic en **"Create Background Worker"** (o **"Deploy"** si ya existe).
2. Render instalará las dependencias y arrancará el script automáticamente.
3. Puedes ver los logs en tiempo real desde el Dashboard de Render.

---

## 🛠️ Prueba local (opcional)

```bash
# 1. Crea el entorno virtual
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

# 2. Instala dependencias
pip install -r requirements.txt

# 3. Crea tu archivo .env copiando el ejemplo
cp .env.example .env
# Edita .env con tus credenciales reales

# 4. Carga las variables y corre el script
export $(cat .env | xargs)    # En Windows usa dotenv o set manual
python buscar_correo.py
```

---

## ⚠️ Consideraciones del Plan Gratuito de Render

- Los **Background Workers gratuitos** pueden pausarse después de inactividad.
- Si necesitas que el monitor corra **24/7 sin interrupciones**, actualiza al plan **Starter** (~$7/mes).
- Puedes revisar el estado del servicio en cualquier momento desde el Dashboard de Render.
