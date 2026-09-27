"""Webhook isteğini işler; Telegram getUpdates veya deleteWebhook çağırmaz."""
import os
from datetime import datetime
from telegram_bot import menuyu_hazirla, komutu_isle
from telegram_utils import telegram_mesaj_gonder
from yemek_mail import TZ

def main():
    chat_id = os.environ["TELEGRAM_CHAT_ID"].strip()
    command = os.environ["MENU_COMMAND"]
    if command not in {"bugun", "yarin", "hafta"}:
        raise ValueError("Geçersiz menü komutu")
    try:
        simdi = datetime.fromtimestamp(int(os.environ["REQUESTED_AT"]), TZ)
        menu = menuyu_hazirla(simdi)
        komutu_isle({"chat": {"id": chat_id}, "text": "/" + command}, menu, simdi, chat_id)
    except Exception:
        telegram_mesaj_gonder(chat_id, "⚠️ Menü hazırlanamadı. GitHub Actions kaydını kontrol edin.")
        raise RuntimeError("Webhook menü görevi başarısız") from None

if __name__ == "__main__":
    main()
