#günlük yemek menüsü

Her gün Türkiye saatiyle 10.00'da yemek listesini kontrol eder, Excel dosyası
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

GitHub cron zamanları UTC'dir. Türkiye saati yıl boyunca UTC+3 olduğundan
`0 7 * * *`, her gün 10.00 anlamına gelir.


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
