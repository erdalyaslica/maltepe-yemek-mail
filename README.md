#günlük yemek menüsü

Hafta içi her gün Türkiye saatiyle 10.00'da yemek listesini kontrol eder, Excel dosyası
oluşturur ve Gmail üzerinden e-posta gönderir.

Hafta içi e-postasında günün menüsü ve haftanın kalan iş günleri yer alır.
Hafta sonu e-postasında gelecek haftanın tüm iş günleri yer alır. Her yemeğin
yanında Google Görseller araması açan bir düğme bulunur.

Güncel aya ait geçerli Excel `menu-arsivi/YYYY-AA.xlsx` yolunda bulunuyorsa
Firecrawl çağrılmaz. Yeni ayda dosya bulunana kadar site iş günlerinde kontrol
edilir; dolu liste bulunduğunda dosya otomatik olarak depoya kaydedilir ve ayın
kalanındaki e-postalar bu dosyadan hazırlanır.

Yeni ayın listesi sitede birkaç gün gecikirse sistem durmaz; yeni liste
bulunana kadar en son kayıtlı Excel dosyasını e-posta eki olarak göndermeye
devam eder.

## GitHub Secrets

Repository > Settings > Secrets and variables > Actions > New repository secret
alanından şu altı secret eklenmelidir:

- `FIRECRAWL_API_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `MAIL_TO`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## İlk test

GitHub deposunda Actions > Günlük yemek menüsü > Run workflow seçilir. Başarılı
olursa sonraki çalıştırmalar hafta içi otomatik gerçekleşir.

İlk başarılı çalıştırmadan sonra depoda `menu-arsivi` klasörünün ve güncel aya
ait Excel'in oluştuğu kontrol edilebilir. Telegram için `Telegram yemek botu`
workflow'u elle çalıştırılabilir; daha sonra bot yaklaşık 10 dakikada bir gelen
komutları kontrol eder.

## Zamanlama

Günlük bildirim hafta içi Türkiye saatiyle 10.00'da gönderilir. GitHub'ın kendi
zamanlayıcısı (`schedule`) yoğunlukta saatlerce gecikebildiği için görevi
Cloudflare Worker'daki cron tetikleyicisi başlatır (`wrangler.toml`,
`0 7 * * MON-FRI`; cron zamanları UTC'dir, Türkiye UTC+3'tür). Saati değiştirmek
için bu satır düzenlenip Worker yeniden yayımlanır (`npx wrangler deploy`).

Workflow'daki `schedule` yalnızca yedektir: Worker görevi başlatamazsa bildirim
yine gönderilir; o gün zaten gönderildiyse yedek çalışma tekrar göndermez.

## Telegram

Günlük menü e-postaya ek olarak Telegram'a da gönderilir. Telegram botu yaklaşık
10 dakikada bir kontrol edilir; aşağıdaki komutlar desteklenir:

- `/bugün` veya `/bugun`
- `/yarın` veya `/yarin`
- `/hafta`
- `/test`
- `/yardım`

Telegram için Actions secrets alanına şu iki secret eklenmelidir:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Bot yalnızca `TELEGRAM_CHAT_ID` ile belirtilen sohbete yanıt verir.
