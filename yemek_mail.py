import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

import pandas as pd
from firecrawl import Firecrawl
from pydantic import BaseModel, Field


URL = "https://www.maltepe.edu.tr/sks/tr/yemek-lstesi"
TZ = ZoneInfo("Europe/Istanbul")


class MenuItem(BaseModel):
    tarih: str = Field(description="Menünün tarihi, mümkünse GG.AA.YYYY")
    gun: str = Field(description="Haftanın günü")
    yemekler: list[str] = Field(description="O gün sunulan yemeklerin tam listesi")
    kalori: str = Field(default="", description="Varsa toplam kalori")


class MenuListesi(BaseModel):
    menu: list[MenuItem]


def menu_verisini_al() -> list[dict]:
    app = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    sonuc = app.scrape(
        URL,
        formats=[
            "markdown",
            {
                "type": "json",
                "schema": MenuListesi.model_json_schema(),
                "prompt": (
                    "Sayfadaki güncel yemek listesini eksiksiz çıkar. Her tarihi ayrı "
                    "kayıt yap. Yalnızca sayfada açıkça bulunan bilgileri kullan; tahmin etme."
                ),
            },
        ],
        only_main_content=True,
    )
    veri = sonuc.json
    if hasattr(veri, "model_dump"):
        veri = veri.model_dump()
    menu = (veri or {}).get("menu", [])
    if not menu:
        raise RuntimeError("Sayfadan yemek listesi çıkarılamadı.")
    return menu


def bugunun_menusunu_bul(menu: list[dict]) -> dict | None:
    bugun = datetime.now(TZ)
    tarih_bicimleri = ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y")
    for kayit in menu:
        metin = str(kayit.get("tarih", "")).strip()
        for bicim in tarih_bicimleri:
            try:
                if datetime.strptime(metin, bicim).date() == bugun.date():
                    return kayit
            except ValueError:
                continue
    gun_adlari = {
        0: "pazartesi", 1: "salı", 2: "çarşamba", 3: "perşembe",
        4: "cuma", 5: "cumartesi", 6: "pazar",
    }
    return next(
        (x for x in menu if gun_adlari[bugun.weekday()] in str(x.get("gun", "")).lower()),
        None,
    )


def excel_olustur(menu: list[dict], dosya: str) -> None:
    satirlar = []
    for kayit in menu:
        satirlar.append({
            "Tarih": kayit.get("tarih", ""),
            "Gün": kayit.get("gun", ""),
            "Yemekler": "\n".join(kayit.get("yemekler", [])),
            "Kalori": kayit.get("kalori", ""),
        })
    tablo = pd.DataFrame(satirlar)
    with pd.ExcelWriter(dosya, engine="openpyxl") as writer:
        tablo.to_excel(writer, sheet_name="Yemek Listesi", index=False)
        ws = writer.sheets["Yemek Listesi"]
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for sutun, genislik in {"A": 15, "B": 15, "C": 55, "D": 14}.items():
            ws.column_dimensions[sutun].width = genislik
        for row in ws.iter_rows(min_row=2):
            row[2].alignment = __import__("openpyxl").styles.Alignment(wrap_text=True)


def mail_gonder(bugun: dict | None, excel: str) -> None:
    gonderen = os.environ["GMAIL_ADDRESS"]
    alici = os.environ["MAIL_TO"]
    tarih = datetime.now(TZ).strftime("%d.%m.%Y")
    if bugun:
        yemekler = "".join(f"<li>{y}</li>" for y in bugun.get("yemekler", []))
        icerik = f"<h2>{tarih} Maltepe Üniversitesi Menüsü</h2><ul>{yemekler}</ul>"
        if bugun.get("kalori"):
            icerik += f"<p><b>Kalori:</b> {bugun['kalori']}</p>"
    else:
        icerik = f"<h2>{tarih}</h2><p>Bugüne ait menü bulunamadı.</p>"
    icerik += "<p>Güncel yemek listesinin tamamı Excel eki olarak gönderilmiştir.</p>"

    mesaj = EmailMessage()
    mesaj["Subject"] = f"Maltepe Üniversitesi Yemek Menüsü - {tarih}"
    mesaj["From"] = gonderen
    mesaj["To"] = alici
    mesaj.set_content("Bugünün yemek menüsü HTML destekli bir e-posta istemcisiyle görüntülenebilir.")
    mesaj.add_alternative(icerik, subtype="html")
    with open(excel, "rb") as f:
        mesaj.add_attachment(
            f.read(), maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="maltepe_yemek_listesi.xlsx",
        )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gonderen, os.environ["GMAIL_APP_PASSWORD"])
        smtp.send_message(mesaj)


if __name__ == "__main__":
    menu = menu_verisini_al()
    dosya = "maltepe_yemek_listesi.xlsx"
    excel_olustur(menu, dosya)
    mail_gonder(bugunun_menusunu_bul(menu), dosya)
    print("Yemek listesi e-postası gönderildi.")
