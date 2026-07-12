import os
import smtplib
from datetime import date, datetime, timedelta
from email.message import EmailMessage
from html import escape
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

import pandas as pd
from firecrawl import Firecrawl
from pydantic import BaseModel, Field


URL = "https://www.maltepe.edu.tr/sks/tr/yemek-lstesi"
TZ = ZoneInfo("Europe/Istanbul")
TARIH_BICIMLERI = ("%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%y")
GUN_ADLARI = {
    0: "Pazartesi",
    1: "Salı",
    2: "Çarşamba",
    3: "Perşembe",
    4: "Cuma",
    5: "Cumartesi",
    6: "Pazar",
}


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


def tarihi_coz(kayit: dict) -> date | None:
    metin = str(kayit.get("tarih", "")).strip()
    for bicim in TARIH_BICIMLERI:
        try:
            return datetime.strptime(metin, bicim).date()
        except ValueError:
            continue
    return None


def mail_araligini_bul(simdi: datetime) -> tuple[date, date, str, str]:
    bugun = simdi.date()
    if simdi.weekday() >= 5:
        gun_farki = 7 - simdi.weekday()
        baslangic = bugun + timedelta(days=gun_farki)
        bitis = baslangic + timedelta(days=4)
        return baslangic, bitis, "Gelecek Haftanın Menüsü", "Gelecek Hafta"

    baslangic = bugun
    bitis = bugun + timedelta(days=4 - simdi.weekday())
    return baslangic, bitis, "Bugün ve Haftanın Kalanı", "Bugün ve Kalan Hafta"


def araliktaki_menuleri_bul(menu: list[dict], baslangic: date, bitis: date) -> list[dict]:
    secilenler = []
    for kayit in menu:
        tarih = tarihi_coz(kayit)
        if tarih and baslangic <= tarih <= bitis:
            yeni_kayit = dict(kayit)
            yeni_kayit["_tarih"] = tarih
            secilenler.append(yeni_kayit)
    return sorted(secilenler, key=lambda x: x["_tarih"])


def excelden_oku(dosya: Path) -> list[dict]:
    tablo = pd.read_excel(dosya, dtype=str).fillna("")
    gerekli = {"Tarih", "Gün", "Yemekler", "Kalori"}
    if tablo.empty or not gerekli.issubset(tablo.columns):
        return []
    menu = []
    for _, satir in tablo.iterrows():
        menu.append({
            "tarih": satir["Tarih"].strip(),
            "gun": satir["Gün"].strip(),
            "yemekler": [x.strip() for x in satir["Yemekler"].splitlines() if x.strip()],
            "kalori": satir["Kalori"].strip(),
        })
    return menu


def son_exceli_bul(arsiv: Path) -> Path | None:
    dosyalar = sorted(arsiv.glob("*.xlsx"), reverse=True)
    for dosya in dosyalar:
        if excelden_oku(dosya):
            return dosya
    return None


def aya_ait_gecerli_mi(menu: list[dict], simdi: datetime) -> bool:
    if not menu:
        return False
    for kayit in menu:
        tarih = tarihi_coz(kayit)
        if tarih and tarih.year == simdi.year and tarih.month == simdi.month:
            return True
    return False


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


def google_gorsel_linki(yemek: str) -> str:
    return f"https://www.google.com/search?tbm=isch&q={quote_plus(yemek)}"


def yemek_satiri_html(yemek: str) -> str:
    guvenli_yemek = escape(yemek)
    link = escape(google_gorsel_linki(yemek), quote=True)
    return f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #edf2f7;color:#172033;font-size:15px;line-height:1.45;">
            {guvenli_yemek}
          </td>
          <td style="padding:10px 0 10px 12px;border-bottom:1px solid #edf2f7;text-align:right;white-space:nowrap;">
            <a href="{link}" style="display:inline-block;background:#eef6ff;color:#155eef;text-decoration:none;border-radius:999px;padding:7px 11px;font-size:12px;font-weight:700;">
              Görseller
            </a>
          </td>
        </tr>
    """


def menu_karti_html(kayit: dict, bugun: date) -> str:
    tarih = kayit.get("_tarih") or tarihi_coz(kayit)
    tarih_metni = tarih.strftime("%d.%m.%Y") if tarih else escape(str(kayit.get("tarih", "")))
    gun = GUN_ADLARI.get(tarih.weekday(), kayit.get("gun", "")) if tarih else kayit.get("gun", "")
    rozet = "Bugün" if tarih == bugun else gun
    yemekler = kayit.get("yemekler", [])
    yemek_html = "".join(yemek_satiri_html(yemek) for yemek in yemekler)
    if not yemek_html:
        yemek_html = """
            <tr>
              <td colspan="2" style="padding:12px 0;color:#697386;font-size:14px;">
                Bu gün için yemek bilgisi bulunamadı.
              </td>
            </tr>
        """
    kalori = ""
    if kayit.get("kalori"):
        kalori = f"""
            <span style="display:inline-block;margin-top:12px;background:#fff7ed;color:#9a3412;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:700;">
              Kalori: {escape(str(kayit["kalori"]))}
            </span>
        """
    return f"""
      <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:18px 18px 14px;margin:0 0 14px;box-shadow:0 4px 18px rgba(15,23,42,0.05);">
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:8px;">
          <div>
            <div style="color:#0f172a;font-size:18px;font-weight:800;line-height:1.25;">{escape(gun)}</div>
            <div style="color:#64748b;font-size:13px;margin-top:2px;">{escape(tarih_metni)}</div>
          </div>
          <span style="background:#ecfdf5;color:#047857;border-radius:999px;padding:7px 11px;font-size:12px;font-weight:800;">
            {escape(rozet)}
          </span>
        </div>
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
          {yemek_html}
        </table>
        {kalori}
      </div>
    """


def mail_icerigi_olustur(menu: list[dict], simdi: datetime) -> tuple[str, str]:
    baslangic, bitis, baslik, konu_eki = mail_araligini_bul(simdi)
    secilenler = araliktaki_menuleri_bul(menu, baslangic, bitis)
    tarih_araligi = f"{baslangic:%d.%m.%Y} - {bitis:%d.%m.%Y}"
    kartlar = "".join(menu_karti_html(kayit, simdi.date()) for kayit in secilenler)
    if not kartlar:
        kartlar = f"""
          <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:18px;color:#475569;">
            {escape(tarih_araligi)} aralığı için menü bulunamadı. Güncel Excel dosyası ektedir.
          </div>
        """

    icerik = f"""
    <!doctype html>
    <html>
      <body style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;color:#172033;">
        <div style="display:none;max-height:0;overflow:hidden;">
          Maltepe Üniversitesi yemek listesi: {escape(konu_eki)}
        </div>
        <div style="max-width:680px;margin:0 auto;padding:28px 16px;">
          <div style="background:linear-gradient(135deg,#0f766e,#2563eb);border-radius:20px;padding:24px;margin-bottom:16px;color:#ffffff;">
            <div style="font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.86;">
              Maltepe Üniversitesi
            </div>
            <h1 style="margin:8px 0 6px;font-size:26px;line-height:1.2;">{escape(baslik)}</h1>
            <div style="font-size:14px;opacity:.92;">{escape(tarih_araligi)}</div>
          </div>
          {kartlar}
          <div style="color:#64748b;font-size:12px;line-height:1.5;margin-top:16px;text-align:center;">
            Excel dosyası ektedir. Görseller düğmeleri Google Görseller araması açar.
          </div>
        </div>
      </body>
    </html>
    """
    return konu_eki, icerik


def mail_gonder(menu: list[dict], excel: str) -> None:
    gonderen = os.environ["GMAIL_ADDRESS"]
    alici = os.environ["MAIL_TO"]
    simdi = datetime.now(TZ)
    tarih = simdi.strftime("%d.%m.%Y")
    konu_eki, icerik = mail_icerigi_olustur(menu, simdi)

    mesaj = EmailMessage()
    mesaj["Subject"] = f"Maltepe Üniversitesi Yemek Menüsü - {konu_eki} - {tarih}"
    mesaj["From"] = gonderen
    mesaj["To"] = alici
    mesaj.set_content("Yemek menüsü HTML destekli bir e-posta istemcisiyle görüntülenebilir.")
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
    simdi = datetime.now(TZ)
    arsiv = Path("menu-arsivi")
    arsiv.mkdir(exist_ok=True)
    dosya = arsiv / f"{simdi:%Y-%m}.xlsx"

    menu = excelden_oku(dosya) if dosya.exists() else []
    mail_dosyasi = dosya
    if aya_ait_gecerli_mi(menu, simdi):
        print(f"Kayıtlı aylık liste kullanılıyor: {dosya}")
    else:
        print("Bu aya ait geçerli liste yok; Firecrawl ile kontrol ediliyor.")
        yeni_menu = menu_verisini_al()
        if aya_ait_gecerli_mi(yeni_menu, simdi):
            menu = yeni_menu
            excel_olustur(menu, str(dosya))
            print(f"Yeni aylık liste kaydedildi: {dosya}")
        else:
            print("Sitede bu aya ait dolu yemek listesi henüz bulunamadı.")
            son_dosya = son_exceli_bul(arsiv)
            if not son_dosya:
                raise RuntimeError("Gönderilecek kayıtlı yemek listesi bulunamadı.")
            menu = excelden_oku(son_dosya)
            mail_dosyasi = son_dosya
            print(f"En son kayıtlı listeyle devam ediliyor: {son_dosya}")

    mail_gonder(menu, str(mail_dosyasi))
    print("Yemek listesi e-postası gönderildi.")
