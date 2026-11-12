# HukukAsistan.py: Fonksiyon ve Parametre Belgesi

Bu belge `HukukAsistan.py` dosyasındaki **her sabiti, deseni, sınıfı ve fonksiyonu** açıklar: ne yapar, hangi parametreleri alır, ne döndürür, nasıl kullanılır. Örneklerdeki çıktılar projedeki gerçek PDF'lerle (4857 İş Kanunu, 6502 TKHK, 6698 KVKK, Kira Hukuku sunumu) alınmıştır.

Dosyaların genel haritası için: [DOSYA_REHBERI.md](DOSYA_REHBERI.md).

---

## İçindekiler

1. [Genel bakış ve veri modeli](#1-genel-bakış-ve-veri-modeli)
2. [Ayarlar (sabitler)](#2-ayarlar-sabitler)
3. [Prompt'lar](#3-promptlar)
4. [Düzenli ifade desenleri](#4-düzenli-ifade-desenleri)
5. [Bölüm A: Sorgu yeniden yazımı](#5-bölüm-a-sorgu-yeniden-yazımı)
6. [Bölüm B: PDF → kanun ve madde etiketi](#6-bölüm-b-pdf--kanun-ve-madde-etiketi)
7. [Bölüm C: İndeks](#7-bölüm-c-indeks)
8. [Bölüm D: Arama](#8-bölüm-d-arama)
9. [Bölüm E: Cevap üretimi](#9-bölüm-e-cevap-üretimi)
10. [Bölüm F: Sohbet geçmişi](#10-bölüm-f-sohbet-geçmişi)
11. [Bölüm G: Arayüz](#11-bölüm-g-arayüz)
12. [Çağrı zinciri: kim kimi çağırır](#12-çağrı-zinciri-kim-kimi-çağırır)
13. [Dosyayı kütüphane olarak kullanmak](#13-dosyayı-kütüphane-olarak-kullanmak)

---

## 1. Genel bakış ve veri modeli

### İki akış

Dosya iki bağımsız işi yapar:

```
İNDEKSLEME (PDF değişince bir kez)
PDFs/*.pdf ─► load_pages ─► _segment_articles ─► build_chunks ─► build_index ─► vectorstore/

SORU CEVAPLAMA (her soruda)
soru ─► detect_laws ─► MevzuatRetriever ─► rewrite_query + search_documents (rrf_merge)
     ─► ConversationalRetrievalChain + QA_PROMPT ─► cevap + format_sources ─► arayüz ─► save_chat (chats/<id>.json)
```

### Adlandırma kuralı

Adı alt çizgiyle başlayan fonksiyonlar (`_fold`, `_segment_articles`, `_similarity` gibi) **iç yardımcılardır**: dosyanın kendi içinde kullanılır, dışarıdan çağırmak için tasarlanmamıştır ama `tools/` betikleri bazılarını kullanır. Alt çizgisiz olanlar (`load_pages`, `build_chunks`, `detect_laws`, `create_answer`) dışarıdan kullanılması beklenen "genel" fonksiyonlardır.

### Veri modeli: `Document` ve metadata

Tüm akış LangChain'in `Document` nesnesini taşır. Bir `Document` iki şeyden oluşur: `page_content` (metin) ve `metadata` (sözlük). Fonksiyonlar bu sözlüğe adım adım alan ekler:

| Alan | Kim ekler | Tip | Örnek | Anlamı |
|---|---|---|---|---|
| `source` | `load_pages` | str | `"İş Kanunu 1.5.4857.pdf"` | Dosya adı |
| `page` | PyPDFLoader | int | `10` | Sayfa numarası, **0 tabanlı** (10 = kullanıcıya "s. 11" gösterilir) |
| `page_label`, `total_pages`, `producer`, `creator`, `author`, `creationdate`, `moddate` | PyPDFLoader | | | PDF'in kendi meta bilgileri; program kullanmaz |
| `law` | `load_pages` | str | `"İŞ KANUNU"` | Kanun adı. Algılanamadıysa `"Bilinmiyor"` veya dosya adı |
| `law_no` | `load_pages` | str | `"4857"` | Kanun numarası; yoksa `""` |
| `madde` | `_segment_articles` | str | `"Madde 17"`, `"Geçici Madde 2"`, `"Ek Madde 1"`, `"Giriş"` | Madde etiketi (ön ekli). Madde başlamadan önceki metin `"Giriş"` |
| `madde_no` | `_segment_articles` | int | `17` | Madde numarası; `"Giriş"` için `0` |
| `baslik` | `_segment_articles` | str | `"Süreli fesih"` | Maddenin üstündeki kısa başlık satırı; yoksa `""` |
| `mulga` | `_segment_articles` | bool | `False` | Madde metni "(Mülga" ile başlıyorsa `True` |

Bu metadata üç yerde kullanılır: kanun filtresinde (`law`), kaynak gösteriminde (`law`, `madde`, `page`) ve değerlendirme betiklerinde (`madde_no`).

---

## 2. Ayarlar (sabitler)

Dosyanın en başında, `# --- ayarlar` satırının altında. Davranışı değiştirmek için ilk bakılacak yer.

| Sabit | Varsayılan | Ne yapar | Değiştirince |
|---|---|---|---|
| `PDF_DIR` | `"PDFs"` | PDF'lerin okunacağı klasör. `HUKUK_PDF_DIR` ortam değişkeniyle geçersiz kılınabilir. | Başka klasör okunur; indeks yenilenir |
| `INDEX_DIR` | `"vectorstore"` | İndeksin yazılacağı klasör. `HUKUK_INDEX_DIR` ile geçersiz kılınabilir. | Testlerde geçici indeks için |
| `CHAT_DIR` | `"chats"` | Sohbet geçmişi klasörü; her sohbet bir JSON dosyası. `HUKUK_CHAT_DIR` ile geçersiz kılınabilir. | Testlerde geçici klasör için |
| `CHAT_TITLE_LEN` | `48` | Yan paneldeki sohbet başlığının (ilk soru) en fazla karakter sayısı. | Daha uzun/kısa başlık |
| `INDEX_VERSION` | `2` | İndeks imzasına yazılan sürüm sayısı. | Artırınca indeks zorla yeniden kurulur; parçalama/etiketleme kodunu değiştirdiğinizde artırın |
| `CHUNK_SIZE` | `600` | Uzun maddeler bu karakter uzunluğunda parçalanır. Deneyde 1200'den iyi çıktı. | Küçük: daha çok, daha odaklı parça; büyük: daha az parça, daha çok bağlam. İndeks yenilenir |
| `CHUNK_OVERLAP` | `80` | Ardışık parçaların paylaştığı karakter sayısı. | Cümle bölünmelerini yumuşatır |
| `TOP_K` | `8` | Soruda kanun algılanırsa o kanundan getirilen parça sayısı. | Büyük: daha çok bağlam ama daha uzun prompt |
| `GENERAL_K` | `10` | Kanun algılanmazsa tüm mevzuattan getirilen parça sayısı. | Durum sorularında birden çok kanun gelebileceği için TOP_K'dan büyük |
| `EMBEDDING_MODEL` | `"text-embedding-3-small"` | Parçaları ve soruyu vektöre çeviren model. | İndeks yenilenir |
| `CHAT_MODEL` | `"gpt-4o-mini"` | Cevap üreten ve soruyu yeniden yazan sohbet modeli. | Maliyet/kalite dengesi; `gpt-4o` aralık seçiminde daha iyi |
| `UNKNOWN_LAW` | `"Bilinmiyor"` | Başlığı algılanamayan sayfalara verilen kanun adı. | |
| `MAX_HISTORY_TURNS` | `6` | Modele gönderilen en fazla soru-cevap çifti. | Uzun sohbetlerde token tasarrufu |
| `QUERY_REWRITE` | `True` | Soruyu kanun diline çeviren ikinci arama sorgusu açık mı. | `False`: soru başına 1 LLM çağrısı azalır, geri getirim düşebilir |
| `RRF_K` | `60` | Reciprocal Rank Fusion sabiti. | Literatürdeki standart değer; dokunmak gerekmez |

### `EXAMPLE_QUESTIONS`

Karşılama ekranında buton olarak gösterilen 4 örnek soru. Listeye soru ekleyip çıkarabilirsiniz; arayüz iki sütuna sırayla dağıtır.

### `LAW_ALIASES`

Soruda geçen kısaltma veya kısa adı, kanunun tam adında aranacak ifadeye eşler. Hem anahtar hem değer `_fold` ile küçük harfe indirgenerek karşılaştırılır.

```python
LAW_ALIASES = {
    "kvkk": "kişisel verilerin korunması",   # "KVKK'ya göre" -> KİŞİSEL VERİLERİN KORUNMASI KANUNU
    "tbk": "borçlar kanunu",
    "tkhk": "tüketicinin korunması",
    "tüketici kanunu": "tüketicinin korunması",
    "kira kanunu": "borçlar kanunu",          # yüklü değilse eşleşme bulunmaz
    ...
}
```

**Yeni kısaltma eklemek:** `"vuk": "vergi usul"` gibi bir satır ekleyin. Değer, yüklü kanunun adında (küçük harfle) **geçen** bir ifade olmalıdır; yoksa kısaltma hiçbir kanuna eşlenmez (örnek: `"kira kanunu"` şu an boş döner çünkü Borçlar Kanunu yüklü değil).

---

## 3. Prompt'lar

### `QA_PROMPT`

Cevap üreten modele verilen talimat. İki değişken alır: `{context}` (getirilen mevzuat parçaları) ve `{question}` (soru). LangChain zinciri bunları kendisi doldurur.

Talimatın özü, madde madde:

1. Yalnızca verilen alıntılara dayan; Türkçe, anlaşılır, tarafsız cevap ver.
2. Her hukuki ifadeyi "İş Kanunu m. 17" biçiminde kanun adı ve madde numarasıyla belirt.
3. Alıntılarda cevap yoksa söyle; madde numarası veya hüküm **uydurma**.
4. Alıntı "(Mülga" ile başlıyorsa yürürlükten kalktığını belirt.
5. Somut durum sorularında uygulanabilecek kanun ve maddeleri koşul, istisna, süre ve miktarlarıyla say; kullanıcının verdiği bilgileri (çalışma süresi vb.) hesaba kat.
6. Eşiğe bağlı hükümlerde (süre, yaş, miktar) önce **tüm aralıkları aynen listele**, sonra kullanıcının değerinin hangi aralığa girdiğini adım adım belirle. (Bu kural, "2 yıl çalışan işçi" sorusunda modelin 6 hafta yerine 4 hafta demesi üzerine eklendi.)
7. Sonda kısa bir avukat / adli yardım hatırlatması yap; bu hatırlatma cevabın yerine geçmesin.

### `REWRITE_PROMPT`

Soruyu kanun diline çeviren modele verilen talimat. Tek değişken: `{question}`. Modelden en fazla 25 kelimelik, madde numarası içermeyen tek satır istenir ve günlük dil → kanun dili örnekleri verilir ("ihbar süresi → bildirim süresi", "ev sahibi → kiraya veren", "ürün bozuk çıktı → ayıplı mal, tüketicinin seçimlik hakları").

---

## 4. Düzenli ifade desenleri

Bu desenler PDF metninden yapı çıkarmanın ve sorudan kanun tanımanın temelidir. Farklı düzende bir PDF eklediğinizde en çok bunlara dokunmanız gerekir.

### `TITLE_RE`: kanun başlığı

Büyük harfli, en fazla 15 sözcüklük ve belirli bir sözcükle biten başlıkları yakalar. Bitiş sözcükleri: `KANUN HÜKMÜNDE KARARNAME`, `CUMHURBAŞKANLIĞI KARARNAMESİ`, `KARARNAMESİ`, `ANAYASASI`, `KANUNU`, `KANUN`, `YÖNETMELİĞİ`, `YÖNETMELİK`, `TÜZÜĞÜ`, `TÜZÜK`, `TEBLİĞİ`, `TEBLİĞ`. Bitişten sonra harf gelmemelidir (böylece "KANUNUN" eşleşmez).

| Metin | Eşleşir mi |
|---|---|
| `İŞ KANUNU` | Evet |
| `TÜKETİCİNİN KORUNMASI HAKKINDA KANUN` | Evet |
| `8423 İŞ KANUNU` (Düstur sayfa numarasıyla) | Evet; öndeki sayı `_law_from_header` içinde atılır |
| `İş Kanunu` (küçük harf) | Hayır |
| `BU KANUNUN AMACI` | Hayır (KANUNUN'dan sonra harf var) |

### `META_RE`: künye satırı

Sayfanın gerçekten bir kanunun ilk sayfası olduğunu doğrular. Şunlardan biri aranır (büyük/küçük harf önemsiz): `Kanun Numarası`, `Kabul Tarihi`, `Resmî Gazete`, `Yayımlandığı`, `Karar Sayısı`. Başlık **yalnızca** künye ile aynı sayfadaysa kabul edilir; böylece metin içindeki büyük harfli atıflar ("İŞ KANUNU hükümleri saklıdır") yanlış başlık sayılmaz.

### `LAW_NO_RE`: kanun numarası

`Kanun Numarası : 4857` satırındaki sayıyı çeker. Yönetmeliklerde bu satır yoktur; numara boş kalır.

### `ARTICLE_RE`: madde başlığı

```
(?<!\w)((?:EK|Ek|GEÇİCİ|Geçici|MÜLGA|Mülga)\s+)?(MADDE|Madde)\s+(\d+)\s*[-–—]
```

Üç yakalama grubu: (1) isteğe bağlı ön ek, (2) `MADDE`/`Madde`, (3) numara. Sonunda tire zorunludur.

| Metin | Eşleşir mi | Neden |
|---|---|---|
| `Madde 17 –` | Evet | grup3 = 17 |
| `MADDE 1-` | Evet | KVKK'daki biçim |
| `Geçici Madde 6 –` | Evet | grup1 = "Geçici " |
| `17 nci maddesi` | Hayır | Küçük harf, tire yok; metin içi atıf |
| `Madde 17 uyarınca` | Hayır | Tire yok |

### `PREFIX_MAP`

Ön ekin katlanmış halini standart yazıma çevirir: `{"ek": "Ek", "geçici": "Geçici", "mülga": "Mülga"}`. Böylece "GEÇİCİ MADDE 2" de "Geçici Madde 2" etiketi alır.

### `GENERIC_WORDS`

Kanun adından ayırt edici çekirdek üretirken atılan sözcükler (katlanmış biçimde): `kanunu`, `kanun`, `hakkinda`, `türk`, `türkiye`, `cumhuriyeti`, `ve`, `ile`, `dair`, `ilişkin`, `bazi`, `hükmünde`, `kararname`, `yönetmeliği`, `tüzüğü`, `tebliği`, `sayili` vb. `_law_keys` kullanır.

### `SITUATION_RE`: durum sorusu

Soru kanun adı içermese de "takip sorusu" sayılmamasını sağlayan ifadeler: `hangi kanun`, `hangi madde`, `hangi mevzuat`, `hakkim`, `haklarim`, `ne yapabilir`, `ne yapmali`, `yasal mi`, `hukuki mi`, `dava aç`, `suç mu`. Katlanmış metinde aranır (`haklarım` → `haklarim`).

### `LAW_NO_IN_TEXT_RE`: sorudaki kanun numarası

`4857 sayılı` biçimindeki 3–5 haneli sayıyı yakalar. Katlanmış metinde çalışır (`sayılı` → `sayili`).

---

## 5. Bölüm A: Sorgu yeniden yazımı

### `rewrite_query(question, llm=None)`

**Ne yapar:** Günlük dildeki soruyu, mevzuatta geçen resmi terimlerle yazılmış tek satırlık arama sorgusuna çevirir. Amaç kelime boşluğunu kapatmaktır: kullanıcı "ihbar süresi" der, İş Kanunu m. 17 "bildirim süresi" yazar.

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `question` | str | zorunlu | Kullanıcının sorusu |
| `llm` | ChatOpenAI | `None` | Kullanılacak sohbet modeli. Verilmezse `ChatOpenAI(model=CHAT_MODEL, temperature=0)` oluşturulur. Betikler aynı nesneyi tekrar kullanmak için verir. |

**Dönüş:** `str`. Modelin cevabının ilk satırı, baştaki/sondaki tırnaklar atılmış. Model boş dönerse `""`.

**Maliyet:** 1 kısa LLM çağrısı.

**Örnek (gerçek koşudan):**

```python
>>> ha.rewrite_query("2 yıl çalışan bir işçinin ihbar süresi ne kadardır?")
'İki yıl süreyle çalışmış bir işçinin bildirim süresi ne kadardır?'
```

**Not:** Arama sırasında bu çeviri özgün sorunun **yerine geçmez**; ikisi ayrı aranır ve `rrf_merge` ile birleştirilir. Çeviri başarısız olursa (ağ hatası) `MevzuatRetriever` sessizce yalnızca özgün soruyla arar.

---

## 6. Bölüm B: PDF → kanun ve madde etiketi

### `_fold(text)`

**Ne yapar:** Türkçe'ye uygun küçük harfe çevirir ve `i / ı / İ / I` farklarını tek biçime (`i`) indirger. Soru ile kanun adını karşılaştırırken "İŞ KANUNU" ile "iş kanunu" ile "Is Kanunu" aynı sayılsın diye.

| Parametre | Tip | Açıklama |
|---|---|---|
| `text` | str | Herhangi bir metin |

**Dönüş:** `str`

```python
>>> ha._fold("İŞ KANUNU")
'iş kanunu'
>>> ha._fold("Kişisel Verilerin Korunması")
'kişisel verilerin korunmasi'        # ı -> i
>>> ha._fold("Iğdır")
'iğdir'
```

**Neden gerekli:** Python'un standart `lower()` fonksiyonu `I` harfini `i` yapar ama `İ` için "i̇" (noktalı) üretir; Türkçe karşılaştırmalarda bu tutarsızlık yaratır.

### `_law_from_header(text)`

**Ne yapar:** Bir sayfanın metnine bakıp "bu sayfa bir kanunun ilk sayfası mı?" sorusunu cevaplar. Öyleyse kanun adı ve numarasını çıkarır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `text` | str | Sayfanın tam metni (yalnızca ilk 1500 karakterine bakılır) |

**Dönüş:** `(title, law_no)` ikilisi. Başlık bulunamazsa `(None, "")`. Numara bulunamazsa `(title, "")`.

**Adımlar:**

1. İlk 1500 karakterdeki boşlukları tek boşluğa indirger.
2. `META_RE` künye satırı yoksa `(None, "")` döner (en sık çıkış yolu; sayfaların çoğu böyledir).
3. `TITLE_RE` ile başlığı arar.
4. Başlığın önündeki, büyük harf içermeyen sözcükleri (Düstur sayfa numarası gibi) atar.
5. Başlık 5–160 karakter aralığında değilse reddeder.
6. `LAW_NO_RE` ile numarayı arar.

**Örnek (KVKK PDF'inin 1. sayfası):**

```python
>>> text = 'KİŞİSEL VERİLERİN KORUNMASI KANUNU \n \nKanun Numarası : 6698 \nKabul Tarihi : 24/3/2016 ...'
>>> ha._law_from_header(text)
('KİŞİSEL VERİLERİN KORUNMASI KANUNU', '6698')

>>> ha._law_from_header(pages[5].page_content)     # kanunun 6. sayfası, künye yok
(None, '')
```

### `_pdf_files()`

**Ne yapar:** `PDF_DIR` klasöründeki `.pdf` ve `.PDF` dosyalarını bulur.

**Parametre:** yok. **Dönüş:** alfabetik sıralı yol listesi (`list[str]`). Klasör boşsa `[]`.

```python
>>> ha._pdf_files()
['PDFs\\KVKK 1.5.6698.pdf', 'PDFs\\Kira Hukuku.pdf', 'PDFs\\Tüketici Kanunu 1.5.6502.pdf', 'PDFs\\İş Kanunu 1.5.4857.pdf']
```

### `load_pages()`

**Ne yapar:** Tüm PDF'leri sayfa sayfa okur ve her sayfaya `law`, `law_no`, `source` metadata'sı yazar. Kanun adı bir kez algılandıktan sonra **sonraki sayfalara taşınır**; yeni bir künye sayfası gelince değişir.

**Parametre:** yok (klasörü `PDF_DIR`'den alır).

**Dönüş:** `list[Document]`, her eleman bir sayfa.

**Kurallar:**

- Klasörde **birden fazla** dosya varsa ve bir dosyada hiç başlık algılanmazsa, dosya adı (alt çizgi ve tire boşluğa çevrilerek) kanun adı olur. Böylece `Kira Hukuku.pdf` → `law="Kira Hukuku"`.
- **Tek** dosya varsa başlık algılanmayan sayfalar `"Bilinmiyor"` kalır.
- Aynı ada sahip ama farklı numaralı iki kanun gelirse ikincisinin adına numara eklenir: `İŞ KANUNU` ve `İŞ KANUNU (1475)`.

**Örnek:**

```python
>>> pages = ha.load_pages()
>>> len(pages)
194
>>> pages[0].metadata
{'source': 'KVKK 1.5.6698.pdf', 'page': 0, 'law': 'KİŞİSEL VERİLERİN KORUNMASI KANUNU', 'law_no': '6698', ...}
```

Kanun bazında dağılım: KVKK sayfa 1–21, Kira Hukuku 1–65, TKHK 1–53, İş Kanunu 1–55.

**Maliyet:** Yalnızca disk okuma; OpenAI çağrısı yok. 194 sayfa birkaç saniye.

### `_segment(doc, text, article)`

**Ne yapar:** `_segment_articles` için yardımcı. Verilen metin parçasından, sayfanın metadata'sını kopyalayıp üstüne madde bilgisini ekleyen yeni bir `Document` üretir.

| Parametre | Tip | Açıklama |
|---|---|---|
| `doc` | Document | Metnin alındığı sayfa (metadata'sı miras alınır) |
| `text` | str | Parçanın metni |
| `article` | tuple | `(label, no, baslik, mulga)`, örn. `("Madde 17", 17, "Süreli fesih", False)` |

**Dönüş:** `Document`; metadata'sına `madde`, `madde_no`, `baslik`, `mulga` eklenmiş.

### `_segment_articles(pages)`

**Ne yapar:** Sayfa metinlerini **madde sınırlarından** böler. Her madde ayrı bir `Document` olur; sayfa sonunda biten madde sonraki sayfada aynı etiketle devam eder.

| Parametre | Tip | Açıklama |
|---|---|---|
| `pages` | list[Document] | `load_pages()` çıktısı |

**Dönüş:** `list[Document]`; boş metinli parçalar atılmış.

**Algoritma (her sayfa için):**

1. O kanunun "şu an açık olan maddesi"ni `current_by_law` sözlüğünden alır (ilk sayfa için `("Giriş", 0, "", False)`).
2. `ARTICLE_RE` ile sayfadaki tüm madde başlıklarını bulur.
3. Her başlık için bir üstteki satıra bakar: 90 karakterden kısaysa, `.;:,` ile bitmiyorsa, rakamla veya `(` ile başlamıyorsa ve kendisi bir madde başlığı değilse, o satır **madde başlığı** (`baslik`) sayılır ve kesme noktası o satırın başına çekilir. Mevzuatta "Süreli fesih" satırı tam olarak böyle, "Madde 17 –" satırının hemen üstündedir.
4. Ön ek (`Ek`, `Geçici`, `Mülga`) `PREFIX_MAP` ile standartlaştırılır; başlıktan sonraki 40 karakter "(Mülga" ile başlıyorsa `mulga=True`.
5. Kesme noktaları arasındaki metinler ayrı `Document` olur; sayfa başından ilk kesmeye kadar olan kısım önceki maddenin devamıdır.
6. Sayfanın son maddesi `current_by_law`'a yazılır ki sonraki sayfa devam edebilsin.

**Örnek:**

```python
>>> segs = ha._segment_articles(pages)
>>> len(segs)
431
>>> [ (s.metadata["madde"], s.metadata["baslik"], s.metadata["page"]) for s in segs[:4] ]
[('Giriş', '', 0), ('Madde 1', 'Amaç', 0), ('Madde 2', 'Kapsam', 0), ('Madde 3', 'Tanımlar', 0)]
```

İş Kanunu m. 17 segmentinin metadata ve metni:

```python
{'law': 'İŞ KANUNU', 'madde': 'Madde 17', 'madde_no': 17, 'baslik': 'Süreli fesih', 'mulga': False, 'page': 10}
'Süreli fesih \nMadde 17 - Belirsiz süreli iş sözleşmelerinin feshinden önce durumun diğer tarafa \nbildirilmesi gerekir. ...'
```

Mülga ve geçici maddeler de yakalanır: İş Kanunu `Madde 33`, `Madde 65`, `Madde 77`, `Madde 78` mülga; KVKK `Geçici Madde 1` ("Geçiş hükümleri"), `Geçici Madde 2`, `Geçici Madde 3`.

### `build_chunks(pages=None, chunk_size=None, chunk_overlap=None)`

**Ne yapar:** İndekse girecek son parçaları üretir. Üç adım: madde segmentleri → uzun segmentleri `CHUNK_SIZE`'a göre böl → her parçanın başına `[KANUN | Madde N | Başlık]` bağlam etiketi ekle. Etiket metnin parçası olur, dolayısıyla embedding modeli de görür; "İş Kanunu m. 17" diye arayan bir sorgu bu etiketle eşleşir.

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `pages` | list[Document] | `None` | Sayfalar. `None` ise `load_pages()` çağrılır. Betikler PDF'i bir kez okuyup aynı sayfaları birden çok kez vermek için kullanır. |
| `chunk_size` | int | `None` | Parça uzunluğu (karakter). `None` veya `0` ise `CHUNK_SIZE` (600). |
| `chunk_overlap` | int | `None` | Örtüşme. `None` ise `CHUNK_OVERLAP` (80); `0` verilirse gerçekten 0 olur. |

**Dönüş:** `list[Document]`; `page_content` etiketli, metadata segmentten miras.

**Örnek:**

```python
>>> chunks = ha.build_chunks(pages)
>>> len(chunks)
907
>>> c17 = [c for c in chunks if c.metadata["law"] == "İŞ KANUNU" and c.metadata["madde_no"] == 17]
>>> len(c17)                     # m. 17 uzun olduğu için 4 parçaya bölündü
4
>>> print(c17[0].page_content[:120])
[İŞ KANUNU | Madde 17 | Süreli fesih]
Süreli fesih
Madde 17 - Belirsiz süreli iş sözleşmelerinin feshinden önce durumun diğer tarafa

>>> len(ha.build_chunks(pages, chunk_size=300, chunk_overlap=30))
1652                             # daha küçük parça, daha çok adet
```

---

## 7. Bölüm C: İndeks

### `_index_signature()`

**Ne yapar:** İndeksin "parmak izi"ni üretir. `vectorstore/signature.json` dosyasına yazılır ve her açılışta yeniden hesaplanıp karşılaştırılır.

**Parametre:** yok. **Dönüş:** `dict`:

```python
{"version": 2,
 "files": [{"name": "KVKK 1.5.6698.pdf", "size": 465042, "mtime": 1794144994}, ...],
 "chunk_size": 600, "chunk_overlap": 80, "embedding_model": "text-embedding-3-small"}
```

Bu alanlardan herhangi biri değişirse (PDF eklendi/silindi/değişti, ayar değişti, `INDEX_VERSION` artırıldı) indeks yeniden kurulur.

### `_make_embeddings()`

**Ne yapar:** OpenAI embedding nesnesini standart ayarlarla oluşturur.

**Parametre:** yok. **Dönüş:** `OpenAIEmbeddings(model=EMBEDDING_MODEL, chunk_size=200)`.

**Dikkat:** Buradaki `chunk_size=200` metin parçası boyutu **değildir**; bir istekte OpenAI'ye gönderilen parça **sayısıdır**. OpenAI'nin istek başına 300 bin token sınırını aşmamak için düşük tutulur.

### `build_index(embeddings)`

**Ne yapar:** Sıfırdan indeks kurar: PDF oku → parçala → embed et → FAISS'e yaz → diske kaydet → imzayı yaz.

| Parametre | Tip | Açıklama |
|---|---|---|
| `embeddings` | OpenAIEmbeddings | `_make_embeddings()` çıktısı |

**Dönüş:** `FAISS` vektör deposu nesnesi.

**Hata:** PDF'lerden hiç metin çıkmazsa (taranmış görüntü PDF'i) `RuntimeError` fırlatır.

**Maliyet:** Tüm parçaların embedding'i (907 parça ≈ 20 saniye). Yalnızca `load_or_build_index` gerektiğinde çağırır.

### `load_or_build_index(embeddings=None)`

**Ne yapar:** Dışarıdan çağrılması beklenen indeks fonksiyonu. Diskte geçerli indeks varsa yükler, yoksa `build_index` ile kurar.

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `embeddings` | OpenAIEmbeddings | `None` | `None` ise `_make_embeddings()` kullanılır |

**Dönüş:** `FAISS` nesnesi.

**Karar mantığı:**

```
signature.json var mı?  ─hayır─► build_index
        │evet
içeriği == _index_signature() ?  ─hayır─► build_index
        │evet
FAISS.load_local(...)   (1 saniyeden az)
```

`allow_dangerous_deserialization=True` bayrağı gerekir çünkü `index.pkl` bir pickle dosyasıdır; dosyayı bu uygulama yazdığı için güvenlidir.

**Örnek:**

```python
>>> db = ha.load_or_build_index()
>>> db.index.ntotal
907
```

### `get_vectorstore()`

**Ne yapar:** `load_or_build_index()`'in Streamlit için önbelleklenmiş sarmalayıcısı. `@st.cache_resource` sayesinde sunucu çalıştığı sürece **bir kez** çalışır; her kullanıcı etkileşiminde yeniden yüklenmez. İlk çalıştırmada "Mevzuat indeksi hazırlanıyor..." döner simgesi gösterir.

**Parametre:** yok. **Dönüş:** `FAISS`. Yalnızca Streamlit içinden çağrılmalıdır; betikler doğrudan `load_or_build_index()` kullanır.

### `law_catalog(db)`

**Ne yapar:** İndeksteki parçaların metadata'sını tarayıp kanun bazında özet çıkarır. Yan paneldeki "Yüklü mevzuat" listesi ve `detect_laws` bu kataloğu kullanır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `db` | FAISS | İndeks |

**Dönüş:** Kanun adına göre sıralı `dict`:

```python
>>> ha.law_catalog(db)
{'Kira Hukuku':                          {'law_no': '',     'madde_count': 0,   'chunks': 132},
 'KİŞİSEL VERİLERİN KORUNMASI KANUNU':   {'law_no': '6698', 'madde_count': 36,  'chunks': 116},
 'TÜKETİCİNİN KORUNMASI HAKKINDA KANUN': {'law_no': '6502', 'madde_count': 91,  'chunks': 312},
 'İŞ KANUNU':                            {'law_no': '4857', 'madde_count': 136, 'chunks': 347}}
```

`"Bilinmiyor"` etiketli parçalar kataloğa alınmaz. `madde_count` farklı madde etiketlerinin sayısıdır ("Madde 17" dört parçaya bölünse de 1 sayılır).

### `get_law_catalog()`

`law_catalog(get_vectorstore())`'un `@st.cache_resource` ile önbelleklenmiş hali. Yalnızca Streamlit içinden.

---

## 8. Bölüm D: Arama

### `is_situation_question(text)`

**Ne yapar:** Sorunun somut bir durum sorusu olup olmadığını söyler ("haklarım neler", "hangi kanun", "yasal mı"). Böyle sorular kanun adı içermese de **takip sorusu sayılmaz** ve tüm mevzuatta aranır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `text` | str | Soru |

**Dönüş:** `bool`

```python
>>> ha.is_situation_question("İşten çıkarıldım, haklarım neler?")
True
>>> ha.is_situation_question("Hangi kanun uygulanır?")
True
>>> ha.is_situation_question("Peki ihbar süresi?")        # takip sorusu
False
>>> ha.is_situation_question("Madde 17 ne diyor?")
False
```

### `_law_keys(name)`

**Ne yapar:** Bir kanun adı için soruda aranacak anahtar ifadeleri üretir. Üç aday: tam ad, "türk" ön eki atılmış ad, ve `GENERIC_WORDS` çıkarıldıktan sonra kalan en az iki sözcüklü **ardışık** çekirdek. Tek sözcüklü çekirdek üretilmez ("borçlar" tek başına "borçlarımı ödeyemiyorum" sorusuyla yanlış eşleşirdi).

| Parametre | Tip | Açıklama |
|---|---|---|
| `name` | str | Kanun adı (parantezli ekler, örn. "(1475)", atılır) |

**Dönüş:** `set[str]`, katlanmış biçimde.

```python
>>> sorted(ha._law_keys("KİŞİSEL VERİLERİN KORUNMASI KANUNU"))
['kişisel verilerin korunmasi', 'kişisel verilerin korunmasi kanunu']
>>> sorted(ha._law_keys("TÜKETİCİNİN KORUNMASI HAKKINDA KANUN"))
['tüketicinin korunmasi', 'tüketicinin korunmasi hakkinda kanun']   # "hakkinda" ve "kanun" atıldı
>>> sorted(ha._law_keys("İŞ KANUNU"))
['iş kanunu']                                                        # çekirdek "iş" tek sözcük, eklenmedi
>>> sorted(ha._law_keys("TÜRK BORÇLAR KANUNU"))
['borçlar kanunu', 'türk borçlar kanunu']
```

### `_mentions(folded_text, key)`

**Ne yapar:** Anahtar ifade metinde **sözcük başında** geçiyor mu? Yalnızca sol sınır kontrol edilir; böylece Türkçe ekler ("iş kanunu**na**", "kvkk**'ya**") eşleşmeyi bozmaz.

| Parametre | Tip | Açıklama |
|---|---|---|
| `folded_text` | str | `_fold` uygulanmış soru |
| `key` | str | `_fold` uygulanmış anahtar |

**Dönüş:** `bool`

```python
>>> ha._mentions(ha._fold("İş Kanununa göre"), "iş kanunu")
True
>>> ha._mentions(ha._fold("KVKK'ya göre"), "kvkk")
True
>>> ha._mentions("yaşlıları koruma", "iş kanunu")
False
```

### `detect_laws(text, catalog)`

**Ne yapar:** Metinde (soru veya önceki cevap) hangi yüklü kanunların geçtiğini bulur. Üç yol: **ad** (`_law_keys`), **kısaltma** (`LAW_ALIASES`), **numara** (`LAW_NO_IN_TEXT_RE`, "4857 sayılı"). Sonuç arama filtresi olur.

| Parametre | Tip | Açıklama |
|---|---|---|
| `text` | str | Soru veya cevap metni |
| `catalog` | dict | `law_catalog()` çıktısı; yalnızca yüklü kanunlar aranır |

**Dönüş:** Sıralı `list[str]`; hiçbiri geçmiyorsa `[]`.

**Örnekler (gerçek katalogla):**

```python
>>> ha.detect_laws("KVKK'ya göre verilerim silinir mi?", catalog)
['KİŞİSEL VERİLERİN KORUNMASI KANUNU']            # kısaltma yolu
>>> ha.detect_laws("İş Kanunu'na göre ihbar süresi nedir?", catalog)
['İŞ KANUNU']                                      # ad yolu
>>> ha.detect_laws("4857 sayılı kanun kıdem tazminatı", catalog)
['İŞ KANUNU']                                      # numara yolu
>>> ha.detect_laws("Tüketici kanununa göre ayıplı mal", catalog)
['TÜKETİCİNİN KORUNMASI HAKKINDA KANUN']           # "tüketici kanunu" kısaltması
>>> ha.detect_laws("İşten çıkarıldım, haklarım neler?", catalog)
[]                                                 # kanun adı yok -> genel arama
>>> ha.detect_laws("kira kanunu fesih", catalog)
[]                                                 # kısaltma var ama hedef (Borçlar Kanunu) yüklü değil
```

### `_similarity(db, query, k, laws)`

**Ne yapar:** Tek bir sorgu için FAISS benzerlik araması. `laws` doluysa metadata filtresiyle yalnızca o kanunların parçalarında arar.

| Parametre | Tip | Açıklama |
|---|---|---|
| `db` | FAISS | İndeks |
| `query` | str | Arama metni |
| `k` | int | Döndürülecek parça sayısı |
| `laws` | list[str] | Boş ise filtre yok |

**Dönüş:** `list[Document]`, en benzerden en az benzere.

**Teknik not:** Filtreli aramada `fetch_k=db.index.ntotal` verilir, yani FAISS önce **tüm** indeksi sıralar, sonra filtre uygulanır. Böylece filtre sonrasında da tam `k` parça garanti edilir. 907 parçalık düz indekste maliyeti ihmal edilebilir.

### `_doc_key(doc)`

**Ne yapar:** Bir parçayı tanımlayan anahtar üretir; `rrf_merge` iki listedeki aynı parçayı eşlemek için kullanır.

**Dönüş:** `(law, madde, page, page_content[:80])` dörtlüsü.

```python
>>> ha._doc_key(docs[0])
('İŞ KANUNU', 'Madde 3', 2, '[İŞ KANUNU | Madde 3 | İşyerini bildirme]\ntebliğ tarihinden itibaren otuz iş gün')
```

Aynı maddenin farklı parçaları (`Madde 17`'nin 4 parçası gibi) ilk 80 karakterleri farklı olduğu için ayrı anahtar alır; böylece RRF birleştirmesinde birbirinin yerine sayılmazlar.

### `rrf_merge(result_lists, k, c=RRF_K)`

**Ne yapar:** Reciprocal Rank Fusion. Birden çok sıralı sonuç listesini tek listede birleştirir. Her parçanın puanı, göründüğü her listede `1 / (c + sıra)` değerlerinin toplamıdır; iki listede de üstte çıkan parça en yüksek puanı alır.

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `result_lists` | list[list[Document]] | zorunlu | Birleştirilecek listeler (projede 2: özgün soru, çevrilmiş soru) |
| `k` | int | zorunlu | Döndürülecek parça sayısı |
| `c` | int | `RRF_K` (60) | Yumuşatma sabiti; büyüdükçe sıra farkları önemsizleşir |

**Dönüş:** Puana göre azalan `list[Document]`, ilk `k` eleman.

**Örnek:** İki arama şu sıraları vermiş olsun: Liste 1 = [m.17, m.18, m.25], Liste 2 = [m.25, m.17, m.53].

| Parça | Liste 1 sırası | Liste 2 sırası | Puan |
|---|---|---|---|
| Madde 17 | 1 | 2 | 1/61 + 1/62 = 0.03252 |
| Madde 25 | 3 | 1 | 1/63 + 1/61 = 0.03227 |
| Madde 18 | 2 | – | 1/62 = 0.01613 |
| Madde 53 | – | 3 | 1/63 = 0.01587 |

```python
>>> [d.metadata["madde"] for d in ha.rrf_merge([liste1, liste2], k=3)]
['Madde 17', 'Madde 25', 'Madde 18']
```

İki listede de geçen parçalar (17, 25) tek listede geçenlerin (18, 53) önüne geçer.

### `search_documents(db, query, k, laws=(), rewritten=None)`

**Ne yapar:** Uygulamanın asıl arama fonksiyonu. Özgün soruyla arar; `rewritten` verilmişse ve özgün sorudan farklıysa onunla da arar ve iki listeyi `rrf_merge` ile birleştirir. Değerlendirme betikleri (`evaluate.py`, `experiments.py`) de **bu** fonksiyonu kullanır, dolayısıyla ölçülen şey uygulamanın gerçek davranışıdır.

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `db` | FAISS | zorunlu | İndeks |
| `query` | str | zorunlu | Kullanıcının özgün sorusu |
| `k` | int | zorunlu | Döndürülecek parça sayısı |
| `laws` | list[str] | `()` | Filtre; boşsa tüm mevzuat |
| `rewritten` | str | `None` | `rewrite_query` çıktısı; `None` veya boş ise tek sorgu |

**Dönüş:** `list[Document]`

```python
>>> docs = ha.search_documents(db, "2 yıl çalışan işçinin ihbar süresi ne kadar?", k=5,
...                            laws=["İŞ KANUNU"],
...                            rewritten="İki yıl çalışan işçinin bildirim süresi")
>>> [(d.metadata["madde"], d.metadata["page"] + 1) for d in docs]
[('Madde 3', 3), ('Madde 53', 28), ('Madde 21', 13), ('Madde 102', 42), ('Madde 8', 8)]
```

Bu gerçek çıktı öğreticidir: doğru madde (m. 17) ilk 5'e **girmedi**. Aynı soru `tools/evaluate.py` ile k=10 çalıştırıldığında m. 17 dokuzuncu sırada gelir (`eval/results.json`). "İki yıl" ve "süre" sözcükleri İş Kanunu'nda birçok maddede geçtiği için vektör araması dağılır; `GENERAL_K`'nın 10 ve `CHUNK_SIZE`'ın 600 seçilmesinin nedeni budur.

### `class MevzuatRetriever(BaseRetriever)`

**Ne yapar:** LangChain zincirinin "belge getirici" olarak çağırdığı sınıf. Zincir soruyu verir, sınıf parçaları döndürür. İçeride `rewrite_query` ve `search_documents` kullanır. LangChain'in `BaseRetriever` sınıfından türediği için alanları Pydantic alanı olarak tanımlanır.

**Alanlar (kurucu parametreleri):**

| Alan | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `vectorstore` | FAISS | zorunlu | İndeks |
| `laws` | list[str] | `[]` | Filtre kanunları; boşsa genel arama |
| `rewrite` | bool | `QUERY_REWRITE` | Yeniden yazım açık mı |
| `llm` | ChatOpenAI | `None` | Yeniden yazımda kullanılacak model; `None` ise `rewrite_query` kendi oluşturur |
| `last_rewrite` | str | `""` | Son aramada kullanılan çevrilmiş sorgu; arayüz "Kaynaklar" altında göstermek için okur |

**Metot: `_get_relevant_documents(query, *, run_manager=None)`**

LangChain tarafından çağrılır. Adımlar: `rewrite` açıksa `rewrite_query` ile çeviri (hata olursa boş string), `last_rewrite`'a yaz, sonra `search_documents(vectorstore, query, k, laws, rewritten)`. Buradaki `k`, `laws` doluysa `TOP_K` (8), boşsa `GENERAL_K` (10).

**Örnek:**

```python
>>> r = ha.MevzuatRetriever(vectorstore=db, laws=["İŞ KANUNU"])
>>> docs = r.invoke("ihbar süresi ne kadar?")      # LangChain'in standart çağrısı
>>> len(docs), r.last_rewrite
(8, 'Bildirim süresi ne kadardır?')                # laws dolu -> TOP_K = 8 parça
```

---

## 9. Bölüm E: Cevap üretimi

### `create_answer(question, chat_history, db=None, catalog=None)`

**Ne yapar:** Bir soruyu uçtan uca cevaplar: kanun tespiti → gerekirse sohbet geçmişinden kanun → getirici → LangChain zinciri → cevap. Hem arayüz (`handle_question`) hem `answer_eval.py` bunu çağırır.

| Parametre | Tip | Varsayılan | Açıklama |
|---|---|---|---|
| `question` | str | zorunlu | Kullanıcının sorusu |
| `chat_history` | list[tuple[str, str]] | zorunlu | Önceki `(soru, cevap)` çiftleri; ilk soruda `[]` |
| `db` | FAISS | `None` | İndeks; `None` ise Streamlit önbelleğinden (`get_vectorstore`) alınır |
| `catalog` | dict | `None` | Kanun kataloğu; `None` ise `get_law_catalog()` |

**Dönüş:** 4 elemanlı demet `(answer, source_docs, laws, rewritten)`:

| Eleman | Tip | Açıklama |
|---|---|---|
| `answer` | str | Modelin cevabı (Markdown) |
| `source_docs` | list[Document] | Cevapta kullanılan parçalar; `format_sources` ile listelenir |
| `laws` | list[str] | Uygulanan kanun filtresi; genel aramada `[]` |
| `rewritten` | str | Kanun diline çevrilmiş arama sorgusu; kapalıysa `""` |

**Kanun seçim mantığı:**

```
detect_laws(question) dolu mu?  ─evet─► o kanunlarla filtreli ara
        │hayır
is_situation_question(question)?  ─evet─► tüm mevzuatta ara (laws = [])
        │hayır  (takip sorusu)
geçmişi sondan başa tara: ilk soru veya cevapta kanun bulunursa onu kullan
        │bulunamadı
tüm mevzuatta ara
```

**LLM çağrısı sayısı (soru başına):** 1 yeniden yazım + 1 cevap = 2. Sohbet geçmişi doluysa LangChain zinciri takip sorusunu geçmişle birleştirip bağımsız soruya çeviren **1 ek çağrı** yapar (toplam 3).

**Modeller:** cevap için `ChatOpenAI(model=CHAT_MODEL, temperature=0.2)` (hafif çeşitlilik), yeniden yazım için `temperature=0` (kararlı).

**Örnek (betikten, Streamlit olmadan):**

```python
>>> db = ha.load_or_build_index(); catalog = ha.law_catalog(db)
>>> answer, docs, laws, rw = ha.create_answer(
...     "2 yıl çalışan bir işçinin ihbar süresi ne kadardır?", [], db=db, catalog=catalog)
>>> laws, rw
([], 'İki yıl süreyle çalışan işçinin bildirim süresi ne kadardır?')
>>> print(answer[:200])
2 yıl çalışan bir işçinin ihbar süresi, İş Kanunu'nun 17. maddesine göre aşağıdaki gibi belirlenir:
- İşi altı aydan birbuçuk yıla kadar sürmüş olan işçi için ... dört hafta sonra,
- İşi bir buçuk yıldan üç yıla kadar sürmüş olan işçi için ... altı hafta sonra.
2 yıl, "bir buçuk yıldan üç yıla kadar" aralığına girmektedir. ... altı haftadır.
```

Takip sorusu örneği:

```python
>>> history = [("KVKK'ya göre verilerimi sildirebilir miyim?", "Evet, KVKK m. 7 ve m. 11 ...")]
>>> answer, docs, laws, rw = ha.create_answer("Peki başvuruma kaç günde cevap verilir?", history, db=db, catalog=catalog)
>>> laws
['KİŞİSEL VERİLERİN KORUNMASI KANUNU']     # soruda kanun yok, geçmişten alındı
>>> rw
'Başvuruya yanıt verme süresi.'
>>> ha.format_sources(docs)
['KİŞİSEL VERİLERİN KORUNMASI KANUNU · Geçici Madde 1, Madde 12, Madde 13, Madde 14, Madde 15, Madde 21 · s. 7, 8, 11, 12, 18']
>>> print(answer[:170])
Veri sorumlusuna yapılan başvurulara cevap verilme süresi, başvurunun niteliğine göre en kısa sürede
ve en geç otuz gün içinde sonuçlandırılmalıdır (Kişisel Verilerin Korunması Kanunu m. 13/2).
```

### `format_sources(docs)`

**Ne yapar:** Getirilen parçaları kanun bazında gruplayıp arayüzdeki "Kaynaklar" satırlarını üretir. Aynı maddenin birden çok parçası tek kez yazılır; maddeler numaraya göre, sayfalar artan sırada.

| Parametre | Tip | Açıklama |
|---|---|---|
| `docs` | list[Document] | `create_answer`'ın döndürdüğü kaynak parçalar |

**Dönüş:** `list[str]`, kanun başına bir satır.

```python
>>> ha.format_sources(docs)
['İŞ KANUNU · Madde 17, Madde 18 · s. 12, 13',
 'KİŞİSEL VERİLERİN KORUNMASI KANUNU · Madde 13 · s. 7']
```

Sayfa numarası metadata'daki 0 tabanlı `page` değerine 1 eklenerek yazılır.

### `_history_pairs(messages)`

**Ne yapar:** Streamlit'in mesaj listesini (`{"role": ..., "content": ...}` sözlükleri) `create_answer`'ın beklediği `(soru, cevap)` çiftlerine çevirir. Cevapsız kalan son kullanıcı mesajı atılır.

| Parametre | Tip | Açıklama |
|---|---|---|
| `messages` | list[dict] | `st.session_state.messages` |

**Dönüş:** `list[tuple[str, str]]`

```python
>>> msgs = [{"role": "user", "content": "İhbar süresi?"},
...         {"role": "assistant", "content": "6 hafta..."},
...         {"role": "user", "content": "Peki kıdem?"}]
>>> ha._history_pairs(msgs)
[('İhbar süresi?', '6 hafta...')]          # son soru henüz cevapsız, çifte girmedi
```

---

## 10. Bölüm F: Sohbet geçmişi

Günlük sohbet uygulamalarındaki "geçmiş sohbetler" paneli. Her sohbet `CHAT_DIR/<id>.json` dosyasında saklanır; bu bölümdeki fonksiyonlar Streamlit'e bağlı **değildir**, betiklerden de çağrılabilir. Dosya biçimi:

```json
{"id": "20261112-132448-8094e2", "title": "KVKK'ya göre veri sorumlusu başvuruma en geç ka…",
 "created": "2026-11-12T13:24:48", "updated": "2026-11-12T13:25:31",
 "messages": [{"role": "user", "content": "..."},
              {"role": "assistant", "content": "...", "sources": ["..."], "law": "...", "rewrite": "..."}]}
```

`messages` listesi, arayüzün `st.session_state.messages` içinde tuttuğu sözlüklerin aynısıdır (bkz. `render_message`).

### `_chat_path(chat_id)`

Kimlikten dosya yolunu üretir: `os.path.join(CHAT_DIR, f"{chat_id}.json")`.

### `chat_title(messages)`

**Ne yapar:** Sohbet başlığını üretir: ilk kullanıcı mesajı, fazla boşlukları tek boşluğa indirgenmiş ve `CHAT_TITLE_LEN`'i aşıyorsa `…` ile kısaltılmış.

| Parametre | Tip | Açıklama |
|---|---|---|
| `messages` | list[dict] | Mesaj listesi |

**Dönüş:** `str`; hiç kullanıcı mesajı yoksa `"Yeni sohbet"`.

```python
>>> ha.chat_title([{"role": "user", "content": "2 yıl çalışan   bir işçinin ihbar süresi ne kadardır? Ayrıca kıdem..."}])
'2 yıl çalışan bir işçinin ihbar süresi ne kadar…'       # 48 karakter
>>> ha.chat_title([])
'Yeni sohbet'
```

### `save_chat(chat_id, messages)`

**Ne yapar:** Sohbeti diske yazar. Yeni sohbette (`chat_id=None`) zaman damgalı bir kimlik üretir; var olan sohbette `created` alanını korur, `updated` alanını şimdiki zamana çeker ve başlığı yeniden hesaplar.

| Parametre | Tip | Açıklama |
|---|---|---|
| `chat_id` | str veya None | Var olan sohbetin kimliği; `None` ise yeni sohbet |
| `messages` | list[dict] | Kaydedilecek tüm mesajlar (ekleme değil, tam liste) |

**Dönüş:** `str`, sohbetin kimliği (yeni üretilmiş veya verilenin aynısı).

```python
>>> cid = ha.save_chat(None, msgs)
>>> cid
'20261112-132220-d4d99c'                  # YYYYAAGG-SSDDss-rastgele6
>>> ha.save_chat(cid, msgs + [yeni_soru, yeni_cevap]) == cid
True                                      # aynı dosya güncellendi
```

### `load_chat(chat_id)`

**Ne yapar:** Kayıtlı sohbetin mesaj listesini okur.

**Dönüş:** `list[dict]`; dosya yoksa veya bozuksa `[]` (hata fırlatmaz).

### `delete_chat(chat_id)`

**Ne yapar:** Sohbet dosyasını siler. Dosya zaten yoksa sessizce geçer. **Dönüş:** yok.

### `list_chats()`

**Ne yapar:** `CHAT_DIR` içindeki tüm sohbetlerin özetini verir; bozuk JSON dosyalarını atlar.

**Dönüş:** `list[dict]`, her biri `{"id", "title", "updated"}`, en son güncellenen başta.

```python
>>> ha.list_chats()
[{'id': '20261112-132448-8094e2', 'title': "KVKK'ya göre veri sorumlusu başvuruma en geç ka…", 'updated': '2026-11-12T13:25:31'},
 {'id': '20261112-132220-d4d99c', 'title': '2 yıl çalışan bir işçinin ihbar süresi ne kadar…', 'updated': '2026-11-12T13:22:20'}]
```

### `_chat_group(updated_iso)`

**Ne yapar:** Yan panelde kullanılan tarih grubunu döndürür.

| `updated` | Dönüş |
|---|---|
| Bugün | `"Bugün"` |
| 1 gün önce | `"Dün"` |
| 2–6 gün önce | `"Son 7 gün"` |
| 7 gün ve öncesi, veya çözümlenemeyen tarih | `"Daha eski"` |

### `_label(text)`

**Ne yapar:** Buton etiketinde Markdown özel karakterlerini (`*`, `_`, `$`, `[`, `#` vb.) ters bölü ile kaçırır; böylece "KVKK *silme* hakkı" gibi bir soru başlığı kalın/italik yorumlanmaz, olduğu gibi görünür.

```python
>>> ha._label("KVKK *silme* hakkı _test_ $x")
'KVKK \\*silme\\* hakkı \\_test\\_ \\$x'
```

---

## 11. Bölüm G: Arayüz

Bu bölümdeki her şey Streamlit'e bağlıdır; betiklerden çağrılmaz.

### `CSS`

Sayfaya enjekte edilen stil metni. Renk değişkenleri en üstte: `--ha-accent` (lacivert `#1e3a8a`, logo ve rozet), `--ha-accent-soft` (açık arka plan), `--ha-border`, `--ha-muted` (gri açıklama metni). Streamlit'in sağ üstteki menüsü (`stMainMenu`), "Deploy" eylemleri (`stToolbarActions`) ve altbilgisi gizlenir; üst şeridin (`stToolbar`) **tamamı gizlenmez**, çünkü yan panel daraltıldığında paneli yeniden açan » düğmesi bu şeridin içinde durur (Streamlit 1.67). Yan panel kapalıyken `body:has([data-testid="stSidebar"][data-collapsed="true"])` seçicisiyle içeriğin üst boşluğu artırılır ki » düğmesi logonun üstüne binmesin. Yan paneldeki sohbet butonları sola yaslı ve tek satırda kesilir (`[data-testid="stSidebar"] .stButton` kuralları). `@media (max-width: 640px)` bloğu telefon ekranı için kenar boşluklarını ve yazı boyutlarını küçültür. Sınıf adları `ha-` ön ekiyle başlar: `ha-hero` (başlık şeridi), `ha-welcome` (karşılama kartı), `ha-badge` (kanun rozeti), `ha-note` (alt uyarı), `ha-confirm` (silme onayı notu).

### `DISCLAIMER`

Sayfanın altında her zaman görünen kısa sorumluluk notu: "Bu asistan hukuki tavsiye vermez; ... bir avukata danışın."

### `_badge(label)`

Cevabın üstündeki 📖 kanun rozetini çizer.

| Parametre | Tip | Açıklama |
|---|---|---|
| `label` | str | Rozet metni, örn. `"İŞ KANUNU"` veya virgülle ayrılmış birden çok kanun |

### `_sources_block(sources, rewrite)`

"Kaynaklar" başlıklı açılır kutuyu çizer: madde satırları liste olarak, altında varsa "Arama sorgusu (kanun dili): ..." notu.

| Parametre | Tip | Açıklama |
|---|---|---|
| `sources` | list[str] | `format_sources` çıktısı |
| `rewrite` | str | Çevrilmiş sorgu; boşsa not yazılmaz |

### `render_message(m)`

Geçmişteki tek bir mesajı sohbet balonu olarak çizer. Kullanıcı için 🧑, asistan için ⚖️ avatarı.

| Parametre | Tip | Açıklama |
|---|---|---|
| `m` | dict | Mesaj sözlüğü. Zorunlu: `role` (`"user"`/`"assistant"`), `content`. İsteğe bağlı (asistan): `law` (rozet), `sources` (kaynak satırları), `rewrite` |

```python
m = {"role": "assistant", "content": "İhbar süresi altı haftadır...",
     "law": "İŞ KANUNU", "sources": ["İŞ KANUNU · Madde 17 · s. 11"],
     "rewrite": "İşçinin bildirim süresi"}
```

### `handle_question(question)`

Yeni bir soru geldiğinde yapılan her şey:

1. Soruyu `st.session_state.messages`'a ekler ve balon olarak çizer.
2. Önceki mesajlardan `_history_pairs` ile geçmiş çıkarır.
3. "Mevzuat taranıyor..." döner simgesi altında `create_answer` çağırır.
4. Hata olursa (ağ, API anahtarı, kota) kullanıcıya "Üzgünüm, cevap üretilemedi: ..." mesajı gösterir; uygulama çökmez.
5. Rozet, cevap ve kaynak kutusunu çizer.
6. Asistan mesajını (`content`, `sources`, `law`, `rewrite` ile) geçmişe ekler.
7. `save_chat` ile sohbeti diske yazar; yeni sohbetse kimliği `st.session_state.chat_id`'ye koyar.
8. Yan paneldeki sohbet listesi bu turda zaten çizilmişti; yeni sohbet eklendiyse veya sıra değiştiyse (`sidebar_ids` ile karşılaştırır) `st.rerun()` ile sayfayı tazeler, böylece sohbet listede hemen görünür.

| Parametre | Tip | Açıklama |
|---|---|---|
| `question` | str | Kullanıcının yazdığı veya örnek butonundan gelen soru |

### `_start_new_chat()`

Oturum durumunu boş sohbete çeker: `messages = []`, `chat_id = None`, `confirm_delete = None`. İlk açılışta ve "Yeni sohbet" butonunda çağrılır. Diske bir şey yazmaz; dosya ilk cevapla oluşur.

### `_open_chat(chat_id)`

Kayıtlı sohbeti `load_chat` ile okuyup oturum durumuna yükler ve `chat_id`'yi ayarlar. Sonraki sorular bu sohbete eklenir.

### `render_sidebar(catalog)`

Yan panelin tamamını çizer:

1. Başlık ve alt yazı.
2. **"➕ Yeni sohbet"** (birincil buton) → `_start_new_chat()` + yenile.
3. `list_chats()` ile sohbetler; kimlikler `st.session_state.sidebar_ids`'e yazılır (bkz. `handle_question` adım 8).
4. **"Sohbetler"** başlığı; sohbet yoksa "Henüz kayıtlı sohbet yok" notu.
5. Her sohbet için, grubu değişince `_chat_group` etiketi ("Bugün", "Dün", ...), ardından bir satır: sola yaslı başlık butonu (açık sohbet `secondary`, diğerleri `tertiary` yani düz metin görünümlü) ve 🗑️ butonu.
6. **Silme iki adımlıdır:** 🗑️'ye basınca `confirm_delete = id` olur ve o satırın yerine "“başlık” silinsin mi?" notuyla **Sil / Vazgeç** butonları gelir. Sil, `delete_chat` çağırır; silinen sohbet açık olandıysa `_start_new_chat()`.
7. "Yüklü mevzuat (N)" açılır listesi ve uyarı notu.

| Parametre | Tip | Açıklama |
|---|---|---|
| `catalog` | dict | `get_law_catalog()` çıktısı |

Oturum durumunda kullanılan anahtarlar: `messages`, `chat_id`, `confirm_delete`, `sidebar_ids`, `pending_question`.

### `main()`

Uygulamanın giriş noktası; Streamlit her etkileşimde bu fonksiyonu baştan çalıştırır.

1. Sayfa ayarları (başlık "Hukuk Asistanı", ikon ⚖️, ortalanmış düzen, yan panel masaüstünde açık, telefonda kapalı) ve `CSS`.
2. **Ön kontroller:** `OPENAI_API_KEY` yoksa kırmızı hata ve dur; `PDFs/` boşsa sarı uyarı ve dur.
3. `st.session_state.messages` yoksa `_start_new_chat()`.
4. `get_law_catalog()` — ilk çalıştırmada indeksi kurar (döner simge).
5. **Yan panel:** `render_sidebar(catalog)`.
6. **Başlık şeridi** (`ha-hero`).
7. **Soru girişi:** `st.chat_input` alttaki kutudan; veya örnek soru butonuna basılmışsa `st.session_state.pending_question`'dan alınır.
8. Sohbet boşsa ve soru yoksa **karşılama kartı** ve iki sütunda `EXAMPLE_QUESTIONS` butonları. Butona basınca soru `pending_question`'a yazılır ve sayfa yenilenir (7. adımda okunur).
9. Geçmişteki tüm mesajları `render_message` ile çiz.
10. Yeni soru varsa `handle_question`.
11. Altta `DISCLAIMER`.

Dosyanın son satırı:

```python
if __name__ == "__main__":
    main()
```

Bu sayede `streamlit run HukukAsistan.py` arayüzü başlatır, ama `import HukukAsistan` (betiklerden) arayüzü **başlatmaz**; yalnızca fonksiyonlar yüklenir.

---

## 12. Çağrı zinciri: kim kimi çağırır

### İndeksleme

```
main ─► get_law_catalog ─► get_vectorstore ─► load_or_build_index
                                                  ├─ _make_embeddings
                                                  ├─ _index_signature ─► _pdf_files
                                                  └─ build_index ─► build_chunks ─► load_pages ─► _pdf_files, _law_from_header
                                                                                 └─► _segment_articles ─► _segment
                        law_catalog (katalog çıkarımı)
```

### Soru cevaplama

```
main ─► handle_question ─► _history_pairs
                       ─► create_answer ─► detect_laws ─► _law_keys, _mentions   (+ LAW_ALIASES, LAW_NO_IN_TEXT_RE)
                                        ─► is_situation_question
                                        ─► MevzuatRetriever._get_relevant_documents
                                                ├─ rewrite_query          (LLM çağrısı 1)
                                                └─ search_documents ─► _similarity ×2 ─► rrf_merge ─► _doc_key
                                        ─► ConversationalRetrievalChain + QA_PROMPT   (LLM çağrısı 2; geçmiş varsa +1)
                       ─► format_sources
                       ─► render / _badge / _sources_block
                       ─► save_chat ─► chat_title, _chat_path      (chats/<id>.json)
                       ─► list_chats (sıra değiştiyse st.rerun)
```

### Yan panel

```
main ─► render_sidebar ─► list_chats ─► _chat_group, _label
                       ─► "Yeni sohbet"  ─► _start_new_chat
                       ─► sohbet butonu  ─► _open_chat ─► load_chat
                       ─► 🗑️ + "Sil"     ─► delete_chat
```

### Betiklerin kullandığı fonksiyonlar

| Betik | Çağırdığı `ha.` fonksiyonları |
|---|---|
| `tools/inspect_pdf.py` | `_pdf_files`, `load_pages`, `_segment_articles`, `build_chunks` |
| `tools/build_index.py` | `_pdf_files`, `load_or_build_index`, `law_catalog` |
| `tools/evaluate.py` | `load_or_build_index`, `law_catalog`, `detect_laws`, `rewrite_query`, `search_documents`, `_fold` |
| `tools/experiments.py` | `load_pages`, `build_chunks`, `_index_signature`, `law_catalog`, `detect_laws`, `rewrite_query`, `search_documents`, `ARTICLE_RE`, `_fold` |
| `tools/answer_eval.py` | `load_or_build_index`, `law_catalog`, `create_answer`, `detect_laws`, `_fold` |
| `tools/baseline_naive.py` | `_pdf_files`, `_make_embeddings`, `CHAT_MODEL` (kasıtlı olarak etiketleme fonksiyonlarını **kullanmaz**) |

---

## 13. Dosyayı kütüphane olarak kullanmak

Streamlit olmadan, kendi betiğinizden tüm akışı çalıştırmak için (proje kökünde `.env` dosyası olmalı):

```python
import os, sys
sys.path.insert(0, r"C:\Users\Fetta\Desktop\HukukAsistanChatbot")
os.chdir(r"C:\Users\Fetta\Desktop\HukukAsistanChatbot")
import HukukAsistan as ha

# 1. İndeks ve katalog (ilk seferde kurar, sonra diskten yükler)
db = ha.load_or_build_index()
catalog = ha.law_catalog(db)

# 2. Yalnızca arama (LLM yok, ucuz)
laws = ha.detect_laws("KVKK'ya göre başvuruya kaç günde cevap verilir?", catalog)
docs = ha.search_documents(db, "KVKK'ya göre başvuruya kaç günde cevap verilir?", k=5, laws=laws)
for d in docs:
    print(d.metadata["law"], d.metadata["madde"], "s.", d.metadata["page"] + 1)

# 3. Tam cevap (2 LLM çağrısı)
answer, docs, laws, rewritten = ha.create_answer(
    "KVKK'ya göre başvuruya kaç günde cevap verilir?", [], db=db, catalog=catalog)
print(answer)
print(ha.format_sources(docs))
print("Arama sorgusu:", rewritten)
```

**Hatırlatmalar:**

- `get_vectorstore` ve `get_law_catalog` **yalnızca** Streamlit içinde çalışır; betiklerde `load_or_build_index` ve `law_catalog` kullanın.
- `db` ve `catalog` parametrelerini `create_answer`'a vermezseniz fonksiyon Streamlit önbelleğine başvurur ve Streamlit dışında hata alırsınız.
- Parçalama veya etiketleme kodunu değiştirdiyseniz `INDEX_VERSION`'ı artırın; aksi halde eski indeks yüklenir ve değişikliği göremezsiniz.
- Geçici bir klasörle denemek için ortam değişkenleri: `HUKUK_PDF_DIR=test_pdfs`, `HUKUK_INDEX_DIR=test_index`, `HUKUK_CHAT_DIR=test_chats`.
- Sohbet geçmişi fonksiyonları (`save_chat`, `load_chat`, `list_chats`, `delete_chat`) Streamlit gerektirmez; kayıtlı sohbetleri betikle incelemek için `for c in ha.list_chats(): print(c["title"], len(ha.load_chat(c["id"])))` yeter.
