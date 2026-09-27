from __future__ import annotations

import json
import os
from datetime import date, datetime
from html import escape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MENU_URL = "https://www.maltepe.edu.tr/sks/tr/yemek-listesi"
TZ_NAME = "Europe/Istanbul"
GUN_ADLARI = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar",
}
TARIH_BICIMLERI = ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y")


def _token() -> str:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN secret tanımlı değil.")
    return token


def telegram_api(method: str, payload: dict | None = None):
    url = f"https://api.telegram.org/bot{_token()}/{method}"
    data = json.dumps(payload or {}).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=35) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"Telegram API bağlantı hatası: {exc}") from exc

    if not result.get("ok"):
        raise RuntimeError(
            f"Telegram API {method} başarısız: {result.get('description', 'Bilinmeyen hata')}"
        )
    return result.get("result")


def telegram_bilgilerini_al() -> dict:
    return telegram_api("getMe") or {}


def telegram_mesaj_gonder(chat_id: str, text: str):
    return telegram_api(
        "sendMessage",
        {
            "chat_id": str(chat_id),
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
    )


def telegram_guncellemelerini_al(offset: int) -> list[dict]:
    return telegram_api(
        "getUpdates",
        {
            "offset": offset,
            "timeout": 0,
            "allowed_updates": ["message"],
        },
    ) or []


def telegram_webhook_kaldir() -> None:
    telegram_api("deleteWebhook", {"drop_pending_updates": False})


def tarihi_coz(metin: str) -> date | None:
    for bicim in TARIH_BICIMLERI:
        try:
            return datetime.strptime(metin.strip(), bicim).date()
        except ValueError:
            continue
    return None


def telegram_menu_mesaji(kayit: dict) -> str:
    tarih = kayit.get("_tarih") or tarihi_coz(str(kayit.get("tarih", "")))
    tarih_metni = tarih.strftime("%d.%m.%Y") if tarih else str(kayit.get("tarih", ""))
    gun = GUN_ADLARI.get(tarih.weekday(), kayit.get("gun", "")) if tarih else kayit.get("gun", "")

    satirlar = [f"🍽️ <b>Menü ({escape(tarih_metni)})</b>", ""]
    for yemek in kayit.get("yemekler", []):
        satirlar.append(f"▪️ {escape(str(yemek))}")

    if kayit.get("kalori"):
        satirlar.extend(["", f"🔥 <b>Kalori:</b> {escape(str(kayit['kalori']))}"])

    satirlar.extend(
        [
            "",
            f'🔗 <a href="{escape(MENU_URL, quote=True)}">Sitede Gör</a>',
        ]
    )
    return "\n".join(satirlar)


def telegram_yardim_mesaji() -> str:
    return (
        "🍽️ <b>Maltepe Yemek Botu</b>\n\n"
        "/bugün — Bugünün menüsü\n"
        "/yarın — Yarının menüsü\n"
        "/hafta — Haftanın menüsü\n"
        "/test — Sistem testi"
    )


def telegram_menuleri_gonder(chat_id: str, menu: list[dict]) -> None:
    """Günleri tek mesajda toplar; uzun devam parçaları sessiz gönderilir."""
    blocks = []
    for kayit in menu:
        tarih = kayit.get("_tarih") or tarihi_coz(str(kayit.get("tarih", "")))
        label = (tarih.strftime("%d.%m.%Y") + " " + GUN_ADLARI[tarih.weekday()]) if tarih else str(kayit.get("tarih", ""))
        lines = ["🍽️ " + label]
        lines.extend("▪️ " + str(y) for y in kayit.get("yemekler", []))
        if not kayit.get("yemekler"):
            lines.append("Menü bilgisi henüz yok.")
        if kayit.get("kalori"):
            lines.append("Kalori: " + str(kayit["kalori"]))
        blocks.append("\n".join(lines))
    text = "\n\n".join(blocks) + "\n\n" + MENU_URL
    # 1800 Unicode karakter, en kötü durumda 3600 UTF-16 birimi.
    for index, start in enumerate(range(0, len(text), 1800)):
        telegram_api("sendMessage", {
            "chat_id": str(chat_id),
            "text": text[start:start + 1800],
            "disable_web_page_preview": True,
            "disable_notification": index > 0,
        })
