import imaplib
import email
from email.header import decode_header
import os
import time
import re
import requests
from datetime import datetime
import threading
import http.server
import socketserver

# --- CONFIGURACIÓN DE ENTORNO ---
# Render inyectará estas variables. Nunca las subas a GitHub.
EMAIL = os.getenv("EMAIL_USER")
PASSWORD = os.getenv("EMAIL_PASS")
REMITENTE = os.getenv("REMITENTE_EMAIL")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# Fallback a 10 segundos si no se define, y al puerto 10000 asignado por Render
INTERVALO_BUSQUEDA = int(os.getenv("INTERVALO_BUSQUEDA", 10))
PORT = int(os.getenv("PORT", 10000)) 

# --- VARIABLES DE ESTADO ---
ULTIMO_ID_PROCESADO = None

# Colores para consola (útiles en los logs de Render)
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
END = '\033[0m'

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    """Manejador HTTP mínimo para responder a los pings de Render."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot activo y escuchando")
        
    def log_message(self, format, *args):
        # Sobrescribimos esto para evitar que el log se llene de peticiones GET de Render
        pass

def dummy_server():
    """Levanta un servidor web falso para engañar el health check de Render."""
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), HealthCheckHandler) as httpd:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {CYAN}Servidor web falso corriendo en puerto {PORT}{END}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Error en el servidor dummy: {e}")

def enviar_telegram(mensaje):
    """Envía un mensaje de texto al bot de Telegram."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"{RED}Faltan credenciales de Telegram.{END}")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        return response.json()
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def extraer_informacion(texto):
    """Extrae Montos, Nombres y Fechas usando Regex."""
    datos = {"montos": [], "nombres": [], "fechas": []}
    
    patrones_monto = [
        r"(?:\$|USD|EUR|MXN|Zelle:?)\s*\d+(?:[.,]\d+)*",
        r"\d+(?:[.,]\d+)*\s*(?:USD|EUR|MXN|Zelle|\$)",
        r"Monto:\s*[\$]?\s*\d+(?:[.,]\d+)*"
    ]
    for p in patrones_monto:
        coincidencias = re.findall(p, texto, re.IGNORECASE)
        datos["montos"].extend(coincidencias)

    patrones_nombre = [
        r"(?:De|Nombre|Enviado por|Titular|Cliente):\s*([A-Za-z ]{3,30})",
        r"Transferencia de\s*([A-Za-z ]{3,30})"
    ]
    for p in patrones_nombre:
        coincidencias = re.findall(p, texto, re.IGNORECASE)
        datos["nombres"].extend([c.strip() for c in coincidencias])

    patrones_fecha = [
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"\d{1,2}\s(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\s\d{2,4}"
    ]
    for p in patrones_fecha:
        coincidencias = re.findall(p, texto, re.IGNORECASE)
        datos["fechas"].extend(coincidencias)

    for k in datos:
        datos[k] = list(dict.fromkeys(datos[k]))
    return datos

def obtener_cuerpo_mensaje(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
                except: pass
    else:
        body = msg.get_payload(decode=True).decode(errors="ignore")
    return body

def buscar_correos():
    global ULTIMO_ID_PROCESADO
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, f'(FROM "{REMITENTE}")')
        if status != "OK": return

        mail_ids = messages[0].split()
        if not mail_ids:
            # Comentado para evitar spam en los logs de Render cada 10 segundos
            # print(f"[{datetime.now().strftime('%H:%M:%S')}] Sin correos de {REMITENTE}")
            return

        ultimo_id = mail_ids[-1]

        if ultimo_id == ULTIMO_ID_PROCESADO:
            return

        ULTIMO_ID_PROCESADO = ultimo_id
        status, msg_data = mail.fetch(ultimo_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else "utf-8")

                cuerpo = obtener_cuerpo_mensaje(msg)
                info = extraer_informacion(cuerpo)

                msg_telegram = f"🔔 <b>NUEVO PAGO DETECTADO</b>\n\n"
                msg_telegram += f"📧 <b>Asunto:</b> {subject}\n"
                
                if info["nombres"]:
                    msg_telegram += f"👤 <b>Nombre:</b> {', '.join(info['nombres'])}\n"
                
                if info["montos"]:
                    msg_telegram += f"💰 <b>Monto:</b> {', '.join(info['montos'])}\n"
                else:
                    msg_telegram += f"⚠️ <b>Monto:</b> No detectado automáticamente\n"

                if info["fechas"]:
                    msg_telegram += f"📅 <b>Fecha Ref:</b> {', '.join(info['fechas'])}\n"
                
                msg_telegram += f"\n✅ <i>Verificado a las {datetime.now().strftime('%H:%M:%S')}</i>"

                enviar_telegram(msg_telegram)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {GREEN}✓ Mensaje enviado a Telegram por ID: {ultimo_id}{END}")

    except Exception as e:
        print(f"{RED}ERROR de conexión IMAP: {e}{END}")
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except: pass

def main():
    print(f"{BOLD}{CYAN}Iniciando Monitor de Pagos (Render Web Service Mode)...{END}")
    
    # Validar que las variables esenciales existan antes de arrancar
    if not EMAIL or not PASSWORD:
        print(f"{RED}Error: Faltan variables de entorno (EMAIL_USER o EMAIL_PASS).{END}")
        return

    # Iniciar el servidor web dummy en segundo plano
    server_thread = threading.Thread(target=dummy_server, daemon=True)
    server_thread.start()

    # Bucle principal del monitor
    while True:
        buscar_correos()
        time.sleep(INTERVALO_BUSQUEDA)

if __name__ == "__main__":
    main()