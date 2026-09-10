from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram_utils import (
    telegram_guncellemelerini_al,
    telegram_menu_mesaji,
    telegram_mesaj_gonder,
    telegram_webhook_kaldir,
    telegram_yardim_mesaji,
)
from yemek_mail import (
    TZ,
    araliktaki_menuleri_bul,
    aya_ait_gecerli_mi,
    excelden_oku,
    excel_olustur,
    menu_verisini_al,
    son_exceli_bul,
)


OFFSET_FILE = Path("telegram-offset.txt")


def kayitli_offseti_oku() -> int:
    try:
        return int(OFFSET_FILE.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return 0


def offseti_kaydet(offset: int) -> None:
    OFFSET_FILE.write_text(f"{offset}\n", encoding="utf-8")


def menuyu_hazirla(simdi: datetime) -> list[dict]:
    arsiv = Path("menu-arsivi")
    arsiv.mkdir(exist_ok=True)
    dosya = arsiv / f"{simdi:%Y-%m}.xlsx"
    menu = excelden_oku(dosya) if dosya.exists() else []

    if aya_ait_gecerli_mi(menu, simdi):
        return menu

    if os.getenv("FIRECRAWL_API_KEY"):
        print("Güncel aylık liste yok; Firecrawl ile kontrol ediliyor.")
        yeni_menu = menu_verisini_al()
        if aya_ait_gecerli_mi(yeni_menu, simdi):
            excel_olustur(yeni_menu, str(dosya))
            return yeni_menu

    son_dosya = son_exceli_bul(arsiv)
    if son_dosya:
        print(f"En son kayıtlı liste kullanılıyor: {son_dosya}")
        return excelden_oku(son_dosya)

    raise RuntimeError("Gönderilecek kayıtlı yemek listesi bulunamadı.")


def hafta_araligini_bul(simdi: datetime) -> tuple[date, date]:
    bugun = simdi.date()
    if simdi.weekday() >= 5:
        baslangic = bugun + timedelta(days=7 - simdi.weekday())
    else:
        baslangic = bugun - timedelta(days=simdi.weekday())
    return baslangic, baslangic + timedelta(days=4)


def gunun_menusunu_gonder(menu: list[dict], chat_id: str, hedef: date) -> None:
    secilenler = araliktaki_menuleri_bul(menu, hedef, hedef)
    if not secilenler:
        telegram_mesaj_gonder(
            chat_id,
            f"ℹ️ <b>{hedef:%d.%m.%Y}</b> için kayıtlı yemek menüsü bulunamadı.",
        )
        return
    for kayit in secilenler:
        telegram_mesaj_gonder(chat_id, telegram_menu_mesaji(kayit))


def haftanin_menusunu_gonder(menu: list[dict], chat_id: str, simdi: datetime) -> None:
    baslangic, bitis = hafta_araligini_bul(simdi)
    secilenler = araliktaki_menuleri_bul(menu, baslangic, bitis)
    if not secilenler:
        telegram_mesaj_gonder(
            chat_id,
            f"ℹ️ <b>{baslangic:%d.%m.%Y} - {bitis:%d.%m.%Y}</b> aralığı için menü bulunamadı.",
        )
        return
    for kayit in secilenler:
        telegram_mesaj_gonder(chat_id, telegram_menu_mesaji(kayit))


def komutu_isle(message: dict, menu: list[dict], simdi: datetime, izinli_chat_id: str) -> None:
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id", ""))
    if not chat_id or chat_id != str(izinli_chat_id):
        print(f"İzin verilmeyen sohbet yok sayıldı: {chat_id}")
        return

    text = str(message.get("text") or "").strip()
    if not text:
        return

    komut = text.split()[0].split("@")[0].lower()
    if komut in {"/start", "/yardım", "/yardim", "/help"}:
        telegram_mesaj_gonder(chat_id, telegram_yardim_mesaji())
    elif komut in {"/bugün", "/bugun"}:
        gunun_menusunu_gonder(menu, chat_id, simdi.date())
    elif komut in {"/yarın", "/yarin"}:
        gunun_menusunu_gonder(menu, chat_id, simdi.date() + timedelta(days=1))
    elif komut == "/hafta":
        haftanin_menusunu_gonder(menu, chat_id, simdi)
    elif komut == "/test":
        telegram_mesaj_gonder(chat_id, "✅ Sistem testi: Telegram gönderim çalışıyor.")
    else:
        telegram_mesaj_gonder(
            chat_id,
            "Tanımadığım bir komut aldım. Kullanılabilir komutlar:\n\n"
            + telegram_yardim_mesaji(),
        )


def main() -> None:
    izinli_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not izinli_chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID secret tanımlı değil.")

    simdi = datetime.now(TZ)
    telegram_webhook_kaldir()
    updates = telegram_guncellemelerini_al(kayitli_offseti_oku())
    if not updates:
        print("Bekleyen Telegram komutu yok.")
        return

    menu = menuyu_hazirla(simdi)
    son_offset = kayitli_offseti_oku()
    for update in updates:
        update_id = int(update.get("update_id", 0))
        son_offset = max(son_offset, update_id + 1)
        message = update.get("message")
        if not message:
            continue
        try:
            komutu_isle(message, menu, simdi, izinli_chat_id)
        except Exception as exc:
            print(f"Komut işlenemedi: {exc}")
            chat_id = str((message.get("chat") or {}).get("id", ""))
            if chat_id == izinli_chat_id:
                telegram_mesaj_gonder(
                    chat_id,
                    "⚠️ Komut işlenirken bir hata oluştu. Birkaç dakika sonra tekrar deneyin.",
                )

    offseti_kaydet(son_offset)
    print(f"{len(updates)} Telegram güncellemesi işlendi. Yeni offset: {son_offset}")


if __name__ == "__main__":
    main()
