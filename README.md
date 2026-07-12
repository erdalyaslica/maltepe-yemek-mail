# Maltepe Üniversitesi günlük yemek menüsü

Hafta içi her gün Türkiye saatiyle 10.00'da yemek listesini Firecrawl ile alır,
Excel dosyası oluşturur ve Gmail üzerinden e-posta gönderir.

Güncel aya ait geçerli Excel `menu-arsivi/YYYY-AA.xlsx` yolunda bulunuyorsa
Firecrawl çağrılmaz. Yeni ayda dosya bulunana kadar site iş günlerinde kontrol
edilir; dolu liste bulunduğunda dosya otomatik olarak depoya kaydedilir ve ayın
kalanındaki e-postalar bu dosyadan hazırlanır.

Yeni ayın listesi sitede birkaç gün gecikirse sistem durmaz; yeni liste
bulunana kadar en son kayıtlı Excel dosyasını e-posta eki olarak göndermeye
devam eder.

## GitHub Secrets

Repository > Settings > Secrets and variables > Actions > New repository secret
alanından şu dört secret eklenmelidir:


Normal Gmail parolası kesinlikle kullanılmamalıdır.

## İlk test

GitHub deposunda Actions > Günlük yemek menüsü > Run workflow seçilir. Başarılı
olursa sonraki çalıştırmalar hafta içi otomatik gerçekleşir.

İlk başarılı çalıştırmadan sonra depoda `menu-arsivi` klasörünün ve güncel aya
ait Excel'in oluştuğu kontrol edilebilir.

## Zamanlama

GitHub cron zamanları UTC'dir. Türkiye saati yıl boyunca UTC+3 olduğundan
`0 7 * * 1-5`, hafta içi 10.00 anlamına gelir.
