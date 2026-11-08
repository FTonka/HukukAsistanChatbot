# Mevzuat PDF'leri

Bu klasöre kanun ve yönetmelik PDF'lerini koyun. Klasördeki **tüm** `.pdf` dosyaları okunur:

- Tek birleştirilmiş dosya (ör. `Mevzuat.pdf`) **veya**
- kanun başına bir dosya (ör. `4857_Is_Kanunu.pdf`, `6698_KVKK.pdf`). Bu durumda başlık algılanamayan
  dosyalarda dosya adı kanun adı olarak kullanılır.

Kaynak: <https://www.mevzuat.gov.tr> → kanunu arayın → sayfanın üstündeki **PDF** simgesi.
Resmî Gazete'den indirilen yönetmelik PDF'leri de desteklenir.

PDF'leri koyduktan sonra etiketlemeyi kontrol edin (indeks kurmaz, OpenAI'ye istek göndermez):

```bash
python tools/inspect_pdf.py
```

Çıktıda her kanun için sayfa aralığı ve madde sayısı görünür. "Bilinmiyor" satırı varsa o sayfalarda
kanun başlığı algılanamamıştır; `HukukAsistan.py` içindeki `TITLE_RE` / `META_RE` desenlerine bakın.
