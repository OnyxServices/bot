import imaplib
import email
from email.header import decode_header
import os
import time
import re
import requests
from datetime import datetime

# --- CONFIGURACIÓN DESDE VARIABLES DE ENTORNO ---
EMAIL = os.environ["EMAIL_CUENTA"]
PASSWORD = os.environ["EMAIL_PASSWORD"]
REMITENTE = os.environ["EMAIL_REMITENTE"]
INTERVALO_BUSQUEDA = int(os.environ.get("INTERVALO_BUSQUEDA", "10"))

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# --- ESTADO INTERNO ---
ULTIMO_ID_PROCESADO = None

# Colores para consola
CYAN = '\033[96m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
END = '\033[0m'


def enviar_telegram(mensaje):
    """Envía un mensaje de texto al bot de Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        return response.json()
    except Exception as e:
        print(f"{RED}Error enviando a Telegram: {e}{END}")


def extraer_informacion(texto):
    """Extrae Montos, Nombres y Fechas usando Regex."""
    datos = {"montos": [], "nombres": [], "fechas": []}

    patrones_monto = [
        r"(?:\$|USD|EUR|MXN|Zelle:?)\s*\d+(?:[.,]\d+)*",
        r"\d+(?:[.,]\d+)*\s*(?:USD|EUR|MXN|Zelle|\$)",
        r"Monto:\s*[\$]?\s*\d+(?:[.,]\d+)*"
    ]
    for p in patrones_monto:
        datos["montos"].extend(re.findall(p, texto, re.IGNORECASE))

    patrones_nombre = [
        r"(?:De|Nombre|Enviado por|Titular|Cliente):\s*([A-Za-z ]{3,30})",
        r"Transferencia de\s*([A-Za-z ]{3,30})"
    ]
    for p in patrones_nombre:
        datos["nombres"].extend([c.strip() for c in re.findall(p, texto, re.IGNORECASE)])

    patrones_fecha = [
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"\d{1,2}\s(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\s\d{2,4}"
    ]
    for p in patrones_fecha:
        datos["fechas"].extend(re.findall(p, texto, re.IGNORECASE))

    # Eliminar duplicados conservando orden
    for k in datos:
        datos[k] = list(dict.fromkeys(datos[k]))

    return datos


def obtener_cuerpo_mensaje(msg):
    """Extrae el cuerpo de texto plano del correo."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        except Exception:
            pass
    return body


def buscar_correos():
    global ULTIMO_ID_PROCESADO
    mail = None
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, f'(FROM "{REMITENTE}")')
        if status != "OK":
            return

        mail_ids = messages[0].split()
        if not mail_ids:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sin correos nuevos de {REMITENTE}")
            return

        ultimo_id = mail_ids[-1]

        if ultimo_id == ULTIMO_ID_PROCESADO:
            return

        ULTIMO_ID_PROCESADO = ultimo_id

        status, msg_data = mail.fetch(ultimo_id, "(RFC822)")

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])

                subject_raw, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject_raw, bytes):
                    subject = subject_raw.decode(encoding if encoding else "utf-8", errors="ignore")
                else:
                    subject = subject_raw

                cuerpo = obtener_cuerpo_mensaje(msg)
                info = extraer_informacion(cuerpo)

                msg_telegram = "🔔 <b>NUEVO PAGO DETECTADO</b>\n\n"
                msg_telegram += f"📧 <b>Asunto:</b> {subject}\n"

                if info["nombres"]:
                    msg_telegram += f"👤 <b>Nombre:</b> {', '.join(info['nombres'])}\n"

                if info["montos"]:
                    msg_telegram += f"💰 <b>Monto:</b> {', '.join(info['montos'])}\n"
                else:
                    msg_telegram += "⚠️ <b>Monto:</b> No detectado automáticamente\n"

                if info["fechas"]:
                    msg_telegram += f"📅 <b>Fecha Ref:</b> {', '.join(info['fechas'])}\n"

                msg_telegram += f"\n✅ <i>Verificado a las {datetime.now().strftime('%H:%M:%S')}</i>"

                enviar_telegram(msg_telegram)
                print(f"{GREEN}✓ Mensaje enviado a Telegram — ID correo: {ultimo_id}{END}")

    except imaplib.IMAP4.error as e:
        print(f"{RED}Error IMAP: {e}{END}")
    except Exception as e:
        print(f"{RED}ERROR inesperado: {e}{END}")
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass


def main():
    print(f"{BOLD}{CYAN}=== Monitor de Pagos — Telegram Mode ==={END}")
    print(f"{YELLOW}Monitoreando correos de: {REMITENTE}{END}")
    print(f"{YELLOW}Intervalo de revisión: {INTERVALO_BUSQUEDA}s{END}\n")

    while True:
        buscar_correos()
        time.sleep(INTERVALO_BUSQUEDA)


if __name__ == "__main__":
    main()
