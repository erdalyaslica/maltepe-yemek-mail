# Maltepe Üniversitesi günlük yemek menüsü

Hafta içi her gün Türkiye saatiyle 10.00'da yemek listesini Firecrawl ile alır,
Excel dosyası oluşturur ve Gmail üzerinden e-posta gönderir.

## GitHub Secrets

Repository > Settings > Secrets and variables > Actions > New repository secret
alanından şu dört secret eklenmelidir:

- `FIRECRAWL_API_KEY`: `fc-...` ile başlayan Firecrawl anahtarı
- `GMAIL_ADDRESS`: `eyaslica@gmail.com`
- `GMAIL_APP_PASSWORD`: Google hesabından oluşturulan 16 karakterli uygulama şifresi
- `MAIL_TO`: `erdalyaslica@maltepe.edu.tr`

Normal Gmail parolası kesinlikle kullanılmamalıdır.

## İlk test

GitHub deposunda Actions > Günlük yemek menüsü > Run workflow seçilir. Başarılı
olursa sonraki çalıştırmalar hafta içi otomatik gerçekleşir.

## Zamanlama

GitHub cron zamanları UTC'dir. Türkiye saati yıl boyunca UTC+3 olduğundan
`0 7 * * 1-5`, hafta içi 10.00 anlamına gelir.
