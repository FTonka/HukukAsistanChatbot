# Dosya Rehberi: Projedeki Her Dosya Ne İşe Yarar?

Bu belge, `HukukAsistanChatbot` klasöründeki **her dosya ve klasörün** ne işe yaradığını, kimin tarafından oluşturulduğunu, silinirse ne olacağını ve ne zaman açıp bakmanız gerektiğini anlatır. Kod bilgisi gerektirmez; hangi dosyanın ne olduğunu öğrenmek için başvuru kaynağıdır.

`HukukAsistan.py` içindeki fonksiyonların ayrıntılı açıklaması ayrı bir belgededir: [HUKUKASISTAN_FONKSIYONLAR.md](HUKUKASISTAN_FONKSIYONLAR.md).

---

## 1. Kuş bakışı: proje beş katmandan oluşur

| Katman | Dosyalar | Görevi |
|---|---|---|
| **Uygulama** | `HukukAsistan.py` | Tek dosyalık ana program. PDF'leri okur, indeksler, soruyu cevaplar ve Streamlit arayüzünü çizer. Diğer tüm betikler bu dosyayı "kütüphane" gibi içe aktarır. |
| **Veri** | `PDFs/`, `vectorstore/`, `chats/` | Girdi (mevzuat PDF'leri), bu PDF'lerden otomatik üretilen arama indeksi ve kullanıcının kayıtlı sohbetleri. |
| **Ölçüm ve deney** | `tools/`, `eval/` | Tezdeki sayısal sonuçları üreten betikler ve bunların girdi/çıktı dosyaları. |
| **Yapılandırma** | `requirements.txt`, `requirements.lock.txt`, `.env`, `.env.example`, `.gitignore`, `.venv/` | Hangi kütüphaneler kurulacak, API anahtarı nerede, git neyi takip etmesin. |
| **Belgeler** | `README.md`, `PDFs/README.md`, `docs/`, `eval/INSAN_DEGERLENDIRME.md` | İnsanlar için açıklamalar; program bunları okumaz. |

---

## 2. Klasör ağacı (açıklamalı)

Sağ taraftaki işaretler: **[git]** = depoda takip edilir, **[oto]** = program çalışınca kendiliğinden oluşur ve git dışıdır, **[gizli]** = sizin oluşturduğunuz ama git dışı tutulan dosya.

```
HukukAsistanChatbot/
├─ HukukAsistan.py                 [git]  Ana uygulama (735 satır): indeksleme + arama + arayüz
├─ README.md                       [git]  Projenin genel tanıtımı, kurulum ve çalıştırma kılavuzu
├─ requirements.txt                [git]  Kurulacak 8 kütüphane (gevşek sürüm)
├─ requirements.lock.txt           [git]  Aynı 8 kütüphanenin tüm alt bağımlılıklarıyla sabitlenmiş 83 satırlık listesi
├─ .env                            [gizli] OPENAI_API_KEY=sk-... (asla paylaşmayın)
├─ .env.example                    [git]  .env dosyasının anahtar içermeyen şablonu
├─ .gitignore                      [git]  Git'in görmezden geleceği dosya listesi
├─ __pycache__/                    [oto]  Python'un derlenmiş önbelleği; silinebilir
├─ .venv/                          [oto]  Sanal Python ortamı (3.12); tüm kütüphaneler burada kurulu
│
├─ PDFs/                                  GİRDİ: mevzuat metinleri
│  ├─ README.md                    [git]  PDF nasıl indirilir, nereye konur
│  ├─ İş Kanunu 1.5.4857.pdf       [git]  4857 sayılı İş Kanunu (55 sayfa, 136 madde)
│  ├─ Tüketici Kanunu 1.5.6502.pdf [git]  6502 sayılı Tüketicinin Korunması Hakkında Kanun (53 sayfa, 91 madde)
│  ├─ KVKK 1.5.6698.pdf            [git]  6698 sayılı Kişisel Verilerin Korunması Kanunu (21 sayfa, 36 madde)
│  └─ Kira Hukuku.pdf              [gizli] Ders sunumu (65 sayfa, madde yapısı yok); telif nedeniyle git dışı
│
├─ vectorstore/                    [oto]  ÇIKTI: PDF'lerden üretilen FAISS arama indeksi (~6 MB)
│  ├─ index.faiss                         Parçaların sayısal vektörleri (907 parça × 1536 boyut)
│  ├─ index.pkl                           Parça metinleri ve metadata (kanun, madde, sayfa)
│  └─ signature.json                      İndeksin "parmak izi": hangi PDF'lerle, hangi ayarlarla kuruldu
│
├─ chats/                          [oto]  SOHBET GEÇMİŞİ: her sohbet bir JSON dosyası (ilk soruyla oluşur)
│  └─ 20261112-132448-8094e2.json         {"id", "title", "created", "updated", "messages": [...]}
│
├─ tools/                                 ÖLÇÜM BETİKLERİ (komut satırından çalışır)
│  ├─ inspect_pdf.py               [git]  PDF'ler doğru etiketlendi mi? (API çağrısı yok)
│  ├─ build_index.py               [git]  İndeksi uygulamayı açmadan kur
│  ├─ evaluate.py                  [git]  Geri getirim ölçümü: Kanun@k, Madde@k, MRR
│  ├─ experiments.py               [git]  Ablasyon deneyleri: parçalama, filtre, yeniden yazım, embedding, k
│  ├─ answer_eval.py               [git]  Cevap ölçümü: atıf doğruluğu, halüsinasyon, RAG vs salt LLM
│  └─ baseline_naive.py            [git]  Karşılaştırma tabanı: her soruda tüm PDF'i okuyan basit RAG
│
├─ eval/                                  DEĞERLENDİRME VERİLERİ (girdi soru setleri + betik çıktıları)
│  ├─ questions.example.json       [git]  8 örnek soru; altın soru setinin şeması
│  ├─ INSAN_DEGERLENDIRME.md       [git]  İnsan değerlendirme protokolü (Likert, kör değerlendirme, kappa)
│  ├─ experiments.md               [git]  experiments.py çıktısı: 32 satırlık tablo (madde vs fixed, k=1,3,5,10)
│  ├─ experiments.json             [oto]  Aynı sonuçların makine okunur hali
│  ├─ experiments_chunksize.md     [git]  Parça boyutu deneyi tablosu (600 vs 1200, 500 vs 1000)
│  ├─ experiments_chunksize.json   [git]  Aynı sonuçların makine okunur hali
│  ├─ results.json                 [oto]  evaluate.py çıktısı (k=10, yeniden yazım açık)
│  ├─ results_norewrite.json       [oto]  evaluate.py çıktısı (k=5, yeniden yazım kapalı)
│  ├─ answers.json                 [oto]  answer_eval.py çıktısı (7 soru, --judge ile)
│  ├─ answers_check.json           [oto]  answer_eval.py kontrol koşusu (2 soru)
│  └─ indexes/                     [oto]  experiments.py'nin kurduğu 4 deney indeksi (~21 MB)
│     ├─ madde__text-embedding-3-small/
│     ├─ madde-600__text-embedding-3-small/
│     ├─ fixed__text-embedding-3-small/
│     └─ fixed-500__text-embedding-3-small/
│
└─ docs/                                  PROJE BELGELERİ
   ├─ PROJE_5N1K.md                [git]  Tez için 5N1K dokümanı (ne, neden, nasıl, nerede, ne zaman, kim)
   ├─ DOSYA_REHBERI.md             [git]  Bu belge
   └─ HUKUKASISTAN_FONKSIYONLAR.md [git]  HukukAsistan.py fonksiyon ve parametre belgesi
```

---

## 3. Kök dizindeki dosyalar

### `HukukAsistan.py`

**Ne:** Projenin kalbi. Hem `streamlit run HukukAsistan.py` ile çalışan uygulama, hem de `tools/` altındaki tüm betiklerin `import HukukAsistan as ha` diyerek kullandığı kütüphane.

**İçinde ne var (sırayla):**

1. **Ayarlar**: `PDF_DIR`, `INDEX_DIR`, `CHUNK_SIZE` (600), `TOP_K` (8), `GENERAL_K` (10), `EMBEDDING_MODEL`, `CHAT_MODEL`, `QUERY_REWRITE` gibi sabitler. Davranışı değiştirmek için ilk bakılacak yer.
2. **Prompt'lar**: `QA_PROMPT` (cevap üreten modele talimat) ve `REWRITE_PROMPT` (soruyu kanun diline çeviren talimat).
3. **PDF → kanun ve madde etiketi**: Sayfa başlığından kanun adı/numarası çıkarma, metni "Madde 17 –" sınırlarından bölme.
4. **İndeks**: Parçaları embed edip FAISS'e yazma, diskten yükleme, imza kontrolü.
5. **Arama**: Soruda kanun adı tespiti, filtreli vektör arama, iki sorguyu RRF ile birleştirme.
6. **Cevap**: LangChain zinciriyle gpt-4o-mini'den kaynaklı cevap alma, kaynak listesini biçimleme.
7. **Sohbet geçmişi**: Her sohbeti `chats/` klasörüne JSON olarak kaydetme, listeleme, açma, silme.
8. **Arayüz**: CSS, karşılama kartı, örnek sorular, sohbet balonları, yan panel (Yeni sohbet, sohbet listesi, yüklü mevzuat).

**Ne zaman açarım:** Ayar değiştirmek (parça boyutu, model, k), yeni kanun kısaltması eklemek (`LAW_ALIASES`), prompt'u düzenlemek, farklı PDF düzeni için başlık desenini (`TITLE_RE`, `ARTICLE_RE`) güncellemek istediğinizde.

**Ayrıntı:** [HUKUKASISTAN_FONKSIYONLAR.md](HUKUKASISTAN_FONKSIYONLAR.md)

### `README.md`

**Ne:** Projeyi ilk kez gören birine yönelik tanıtım. Özellikler, Mermaid mimari diyagramı, PDF ekleme, kurulum, çalıştırma, değerlendirme komutları tablosu, proje yapısı, ayarlar, telif notu, tez planı ile eşleme, sınırlamalar.

**Ne zaman açarım:** Projeyi yeni bir bilgisayara kurarken; GitHub'a yüklediğinizde ziyaretçilerin göreceği ilk sayfa budur.

### `requirements.txt`

**Ne:** Kurulması gereken 8 kütüphanenin adı. Sürüm aralıkları gevşektir, yani `pip install -r requirements.txt` her zaman en güncel uyumlu sürümü getirir.

| Kütüphane | Projede ne için |
|---|---|
| `streamlit` | Web arayüzü (sohbet balonları, butonlar, yan panel) |
| `langchain`, `langchain-community` | RAG zinciri, PDF yükleyici, metin bölücü, FAISS sarmalayıcı |
| `langchain-openai` | OpenAI sohbet ve embedding modellerine bağlantı |
| `pypdf` | PDF'den metin çıkarma |
| `faiss-cpu` | Vektör benzerlik araması (indeks) |
| `tiktoken` | Token sayımı (OpenAI istek sınırları için) |
| `python-dotenv` | `.env` dosyasındaki anahtarı ortam değişkenine yükleme |

### `requirements.lock.txt`

**Ne:** Yukarıdaki 8 kütüphane ve onların çektiği tüm alt bağımlılıkların (toplam 83 paket) **birebir sürüm numaraları** (`langchain==0.3.30`, `faiss-cpu==1.15.1` gibi). Tez savunmasında "hangi sürümlerle çalıştı" sorusunun cevabıdır.

**Ne zaman kullanırım:** Sonuçları birebir tekrarlamak istediğinizde `pip install -r requirements.lock.txt`. Normal kurulumda `requirements.txt` yeter.

### `.env` ve `.env.example`

**Ne:** `.env` tek satır içerir: `OPENAI_API_KEY=sk-...`. Program açılırken `load_dotenv()` bu dosyayı okur ve anahtarı ortam değişkeni yapar. `.env.example` aynı dosyanın anahtarsız şablonudur; yeni kuran kişi kopyalayıp kendi anahtarını yazar.

**Dikkat:** `.env` git dışıdır (`.gitignore` sayesinde). Hiçbir zaman commit etmeyin, ekran görüntüsünde paylaşmayın. Anahtar sızarsa OpenAI panelinden iptal edin.

### `.gitignore`

**Ne:** Git'in takip etmeyeceği dosya ve klasörlerin listesi. Her satırın nedeni:

| Satır | Neden git dışı |
|---|---|
| `.env` | API anahtarı içerir |
| `.venv/` | Yüzlerce MB kütüphane; her bilgisayar kendi kurar |
| `__pycache__/` | Otomatik önbellek |
| `vectorstore/` | PDF'lerden yeniden üretilebilir, 6 MB ikili dosya |
| `chats/` | Kullanıcının kişisel sohbetleri; depoya konmaz |
| `eval/indexes/` | Deney indeksleri, 21 MB, yeniden üretilebilir |
| `eval/results*.json`, `eval/answers*.json`, `eval/experiments.json` | Betik çıktıları; her koşuda değişir (Markdown özetleri ise takip edilir) |
| `.idea/` | PyCharm ayar klasörü |
| `PDFs/Kira Hukuku.pdf` | Ders sunumu, telif nedeniyle depoya konmaz (resmi kanun metinleri serbesttir, bu değil) |

### `__pycache__/`

**Ne:** Python'un `HukukAsistan.py` dosyasını ilk içe aktardığında ürettiği derlenmiş kopya (`.pyc`). Hız için tutulur. Silerseniz bir sonraki çalıştırmada yeniden oluşur; hiçbir veri kaybolmaz.

### `.venv/`

**Ne:** Projeye özel sanal Python ortamı (Python 3.12). `requirements.txt` ile kurulan tüm kütüphaneler buradadır; bilgisayarınızdaki genel Python'a dokunulmaz. Çalıştırmadan önce etkinleştirilir:

```
.venv\Scripts\activate
```

Silinirse yeniden kurmak gerekir (`python -m venv .venv` ve `pip install -r requirements.txt`). Git dışıdır.

---

## 4. `PDFs/` klasörü: girdi verisi

Program bu klasördeki **tüm** `.pdf` dosyalarını okur. Dosya adı alfabetik sıralanır, her sayfa tek tek işlenir. Buraya dosya eklemek, çıkarmak veya değiştirmek indeksin otomatik yeniden kurulmasına yol açar (bkz. `vectorstore/signature.json`).

### `PDFs/README.md`

Kullanıcıya yönelik kısa talimat: PDF mevzuat.gov.tr'den nasıl indirilir, iki yerleşim düzeni (tek birleşik dosya veya kanun başına dosya), `tools/inspect_pdf.py` ile kontrol.

### Resmi kanun PDF'leri

Üç dosya mevzuat.gov.tr'den indirilmiş resmi metinlerdir. Dosya adındaki `1.5.NNNN` kısmı sitenin kendi adlandırmasıdır: `1` kanun türünü, `5` Düstur tertibini, son sayı kanun numarasını gösterir.

| Dosya | Kanun | Sayfa | Madde | Mülga | İndeksteki parça |
|---|---|---|---|---|---|
| `İş Kanunu 1.5.4857.pdf` | 4857 İş Kanunu | 55 | 136 | 18 | 347 |
| `Tüketici Kanunu 1.5.6502.pdf` | 6502 Tüketicinin Korunması Hakkında Kanun | 53 | 91 | 0 | 312 |
| `KVKK 1.5.6698.pdf` | 6698 Kişisel Verilerin Korunması Kanunu | 21 | 36 | 0 | 116 |

Program bu dosyaların ilk sayfasındaki "KİŞİSEL VERİLERİN KORUNMASI KANUNU / Kanun Numarası : 6698" künyesinden kanun adını ve numarasını kendisi çıkarır; dosya adına bakmaz.

### `Kira Hukuku.pdf`

Bir ders sunumu. İçinde "Madde 17 –" biçiminde madde başlığı olmadığı için program onu tek bir "Giriş" bloğu olarak işler ve kanun adı olarak **dosya adını** kullanır (`Kira Hukuku`, numara yok, 0 madde, 132 parça). Kira sorularında aramaya girer ama madde düzeyinde kaynak gösteremez. Telif nedeniyle git dışıdır; tez için önerilen çözüm yerine 6098 sayılı Türk Borçlar Kanunu PDF'inin eklenmesidir.

---

## 5. `vectorstore/` klasörü: arama indeksi

Uygulama ilk açıldığında (veya `python tools/build_index.py` çalıştırılınca) PDF'lerden üretilir. Her soruda bu indeks sorgulanır. Git dışıdır; silinirse yeniden kurulur (yaklaşık 20 saniye ve bir miktar OpenAI embedding maliyeti).

| Dosya | İçerik | Boyut |
|---|---|---|
| `index.faiss` | 907 parçanın her biri için 1536 sayılık vektör. FAISS kütüphanesinin ikili biçimi. | ~5.5 MB |
| `index.pkl` | Parçaların metinleri ve metadata'sı (kanun, madde, başlık, sayfa). Python pickle biçimi. Vektörden metne dönüşü bu dosya sağlar. | ~0.7 MB |
| `signature.json` | İndeksin parmak izi: indeks sürümü, her PDF'in adı/boyutu/değişiklik tarihi, parça boyutu, örtüşme, embedding modeli. | < 1 KB |

**`signature.json` nasıl çalışır:** Uygulama açılırken bu dosyadaki bilgiyi şu anki PDF'ler ve ayarlarla karşılaştırır. Birebir aynıysa indeksi diskten yükler (1 saniyeden az). Herhangi bir şey farklıysa (PDF eklendi, `CHUNK_SIZE` değişti, `INDEX_VERSION` artırıldı) indeksi sıfırdan kurar.

Örnek içerik:

```json
{"version": 2,
 "files": [{"name": "KVKK 1.5.6698.pdf", "size": 465042, "mtime": 1794144994}, ...],
 "chunk_size": 600, "chunk_overlap": 80, "embedding_model": "text-embedding-3-small"}
```

**İndeksi zorla yenilemek için:** `vectorstore/` klasörünü silin veya `HukukAsistan.py` içindeki `INDEX_VERSION` sayısını bir artırın.

---

## 5b. `chats/` klasörü: sohbet geçmişi

Günlük sohbet uygulamalarındaki geçmiş paneline karşılık gelir. İlk soru cevaplandığı anda oluşur; her sohbet ayrı bir JSON dosyasıdır. Uygulama açılışında bu klasör okunur ve yan panelde sohbetler tarihe göre gruplanmış ("Bugün", "Dün", "Son 7 gün", "Daha eski") listelenir. Bir sohbete tıklamak onu kaldığı yerden açar; sonraki sorular aynı dosyaya eklenir.

| Öğe | Açıklama |
|---|---|
| Dosya adı | `YYYYAAGG-SSDDss-xxxxxx.json`: oluşturulma zamanı + 6 karakter rastgele ek (ör. `20261112-132448-8094e2.json`) |
| `id` | Dosya adıyla aynı kimlik |
| `title` | Yan panelde görünen başlık: ilk sorunun en fazla 48 karakterlik hali |
| `created`, `updated` | ISO tarih-saat; `updated` sıralama ve gruplama için kullanılır |
| `messages` | Arayüzdeki mesaj listesi aynen: `role`, `content`, asistan mesajlarında ayrıca `sources`, `law`, `rewrite` |

Örnek dosya (kısaltılmış):

```json
{
 "id": "20261112-132448-8094e2",
 "title": "KVKK'ya göre veri sorumlusu başvuruma en geç ka…",
 "created": "2026-11-12T13:24:48",
 "updated": "2026-11-12T13:25:31",
 "messages": [
  {"role": "user", "content": "KVKK'ya göre veri sorumlusu başvuruma en geç kaç günde cevap vermeli?"},
  {"role": "assistant", "content": "Veri sorumlusu ... en geç otuz gün içinde ... (KVKK m. 13/2).",
   "sources": ["KİŞİSEL VERİLERİN KORUNMASI KANUNU · Madde 13 · s. 7"],
   "law": "KİŞİSEL VERİLERİN KORUNMASI KANUNU", "rewrite": "Veri sorumlusuna başvuru, cevap süresi"}
 ]
}
```

Git dışıdır (kişisel içerik). Bir sohbeti arayüzden silmek dosyayı siler; klasörü elle silmek tüm geçmişi sıfırlar. Konumu `HUKUK_CHAT_DIR` ortam değişkeniyle değiştirilebilir.

---

## 6. `tools/` klasörü: ölçüm betikleri

Hepsi proje kökünden `python tools/<ad>.py` biçiminde çalıştırılır. Hepsi başta şu üç satırla ana dosyayı bulur ve içe aktarır:

```python
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); os.chdir(ROOT)
import HukukAsistan as ha
```

Böylece uygulamayla **aynı** parçalama, arama ve cevap fonksiyonlarını kullanırlar; ölçülen şey gerçekten uygulamanın davranışıdır.

### `tools/inspect_pdf.py`: etiketleme kontrolü

| | |
|---|---|
| **Ne yapar** | PDF'leri okur, her kanun için numara, sayfa aralığı, madde sayısı ve mülga madde sayısını tablo halinde yazar. Sonunda toplam parça sayısını verir. |
| **Komut** | `python tools/inspect_pdf.py` |
| **OpenAI çağrısı** | Yok (ücretsiz) |
| **Çıktı** | Yalnızca ekrana |
| **Ne zaman** | Yeni PDF ekledikten hemen sonra. Tabloda `Bilinmiyor` satırı görürseniz o sayfalarda kanun başlığı algılanmamıştır. |

Örnek çıktı:

```
Dosyalar: KVKK 1.5.6698.pdf, Kira Hukuku.pdf, Tüketici Kanunu 1.5.6502.pdf, İş Kanunu 1.5.4857.pdf

Kanun / Yönetmelik                                             No       Sayfa  Madde  Mülga
--------------------------------------------------------------------------------------------
KİŞİSEL VERİLERİN KORUNMASI KANUNU                           6698        1-21     36      0
Kira Hukuku                                                     -        1-65      0      0
TÜKETİCİNİN KORUNMASI HAKKINDA KANUN                         6502        1-53     91      0
İŞ KANUNU                                                    4857        1-55    136     18
--------------------------------------------------------------------------------------------
Toplam: 194 sayfa, 263 madde, 907 parça (indeks boyutu)
```

"Kira Hukuku" satırında madde sayısının 0 olması beklenen bir durumdur: ders sunumunda "Madde N –" biçiminde başlık yoktur.

### `tools/build_index.py`: indeksi komut satırından kur

| | |
|---|---|
| **Ne yapar** | Uygulamayı açmadan `vectorstore/` indeksini kurar veya günceller; kanun başına madde ve parça sayısını yazar. |
| **Komut** | `python tools/build_index.py` |
| **OpenAI çağrısı** | Embedding (yalnızca indeks eskiyse; güncelse hiç çağrı yapmaz) |
| **Ne zaman** | Sunucuya kurulumda ilk açılışın uzun sürmesini istemediğinizde; PDF değiştirdikten sonra. |

### `tools/evaluate.py`: geri getirim ölçümü

| | |
|---|---|
| **Ne yapar** | Her soru için indeksten ilk k parçayı çeker ve doğru kanun / doğru madde ilk k içinde mi diye bakar. Üç ölçüt: **Kanun@k**, **Madde@k**, **MRR** (doğru maddenin sırasının tersi). |
| **Komut** | `python tools/evaluate.py eval/questions.json --k 5` |
| **Seçenekler** | `--k 5` (kaç parça değerlendirilecek), `--no-rewrite` (sorgu yeniden yazımını kapat), `--out eval/results.json` |
| **Girdi** | Soru dosyası (varsayılan `eval/questions.json`; yoksa `eval/questions.example.json` kopyalanır) |
| **Çıktı** | Ekrana soru başına ✓/✗ satırı ve özet; ayrıntılar `eval/results.json` |
| **OpenAI çağrısı** | Embedding sorgusu + yeniden yazım açıksa soru başına 1 kısa sohbet çağrısı |

### `tools/experiments.py`: ablasyon deneyleri

| | |
|---|---|
| **Ne yapar** | Aynı soruları farklı yapılandırmalarla çalıştırıp hangisinin daha iyi getirdiğini tablolar. Değişkenler: parçalama (`madde` vs `fixed`, isteğe bağlı boyut: `madde:600`, `fixed:500`), kanun filtresi (açık/kapalı), sorgu yeniden yazımı (açık/kapalı), embedding modeli, k değerleri. |
| **Komut** | `python tools/experiments.py eval/questions.json --k 1,3,5,10 --chunking madde,madde:600,fixed,fixed:500 --rewrite off,on` |
| **Çıktı** | `eval/experiments.md` (Markdown tablo) ve `eval/experiments.json`; `--out` ile ad değiştirilebilir (parça boyutu deneyinde `--out eval/experiments_chunksize` kullanıldı) |
| **Yan etki** | Her parçalama × embedding kombinasyonu için `eval/indexes/` altında ayrı bir indeks kurar ve saklar; PDF'ler değişmedikçe yeniden kurmaz. |
| **OpenAI çağrısı** | Embedding (ilk kurulumda) + yeniden yazım açıksa soru başına 1 çağrı (tüm yapılandırmalarda paylaşılır) |

### `tools/answer_eval.py`: cevap düzeyinde ölçüm

| | |
|---|---|
| **Ne yapar** | Her soru için iki cevap üretir: **RAG** (uygulamanın kendisi) ve **salt LLM** (aynı model, mevzuat alıntısı olmadan). Cevaplardaki madde atıflarını ("m. 17", "17 nci madde") çıkarır ve ölçer: **atıf doğruluğu** (altın madde atfedilmiş mi), **desteksiz atıf** (indekste olmayan maddeye atıf = halüsinasyon). `--judge` ile modele RAG cevabının alıntılara sadakatini 1–5 puanlatır. |
| **Komut** | `python tools/answer_eval.py eval/questions.json --judge --limit 20` |
| **Çıktı** | Ekrana soru başına satır ve özet; `eval/answers.json` |
| **OpenAI çağrısı** | Soru başına 2 (RAG + LLM), `--judge` ile 3; ayrıca yeniden yazım çağrısı. En maliyetli betik budur; `--limit` ile sınırlayın. |

### `tools/baseline_naive.py`: karşılaştırma tabanı

| | |
|---|---|
| **Ne yapar** | Tezdeki "önce" durumu: her soruda tüm PDF'leri yeniden okur, 1000 karakterlik sabit parçalara böler, hepsini yeniden embed eder, etiketsiz ve filtresiz arar, cevap verir. Her adımın süresini ölçer. |
| **Komut** | `python tools/baseline_naive.py "2 yıl çalışan işçinin ihbar süresi ne kadar?"` |
| **Çıktı** | Ekrana cevap, kullanılan sayfalar, adım süreleri (pdf_okuma, parcalama, embedding, arama, cevap) |
| **OpenAI çağrısı** | Her çalıştırmada tüm parçaların embedding'i + 1 sohbet çağrısı (pahalıdır; sadece karşılaştırma için) |

---

## 7. `eval/` klasörü: değerlendirme verileri

İki tür dosya vardır: **girdi** (soru setleri, protokol) ve **çıktı** (betiklerin yazdığı sonuçlar).

### Girdi dosyaları

#### `eval/questions.example.json`

8 örnek soru. Altın soru setinin **şemasını** gösterir; kendi setinizi aynı biçimde `eval/questions.json` olarak kaydetmeniz beklenir (bu dosya henüz yok; betikler varsayılan olarak onu arar).

```json
{"question": "2 yıl çalışan bir işçinin ihbar süresi ne kadardır?", "law": "İŞ KANUNU", "madde": [17]}
```

| Alan | Anlamı |
|---|---|
| `question` | Kullanıcının soracağı biçimde soru |
| `law` | Doğru kanun adının bir parçası; büyük/küçük harf önemsiz, kanun adının içinde geçmesi yeter |
| `madde` | Doğru madde numaraları (liste). Boş bırakılırsa o soruda yalnızca kanun isabeti ölçülür |

Not: 8. soru (kira) 6098 sayılı Türk Borçlar Kanunu'nu bekler; o PDF yüklü olmadığı için bu soru hep başarısız görünür.

#### `eval/INSAN_DEGERLENDIRME.md`

Otomatik ölçütlerin yakalayamadığı "cevap hukuken doğru ve yeterli mi" sorusu için insan değerlendirme protokolü: en az 2 değerlendirici, kör değerlendirme, 5 ölçütlü Likert (doğruluk, atıf, eksiksizlik, anlaşılırlık, uyarı uygunluğu), halüsinasyon var/yok, Cohen kappa ile uyum, Wilcoxon testi. Belge, `eval/insan_degerlendirme_sablon.csv` adlı bir form dosyasından söz eder; bu form henüz oluşturulmamıştır.

### Çıktı dosyaları

| Dosya | Hangi betik yazdı | İçerik | Git |
|---|---|---|---|
| `experiments.md` | `experiments.py` | 32 satır: madde vs fixed × filtre on/off × yeniden yazım off/on × k=1,3,5,10 | takip edilir |
| `experiments.json` | `experiments.py` | Aynı 32 satırın JSON hali | git dışı |
| `experiments_chunksize.md` | `experiments.py --out eval/experiments_chunksize` | 16 satır: madde, madde:600, fixed, fixed:500 × filtre × k=5,10 (yeniden yazım açık). Parça boyutunun 600'e düşürülmesine bu tablo yol açtı. | takip edilir |
| `experiments_chunksize.json` | aynı | JSON hali | takip edilir |
| `results.json` | `evaluate.py --k 10` | 8 soru, yeniden yazım açık: Kanun@10 %88, Madde@10 %88, MRR 0.48. Her soru için getirilen parçalar listelenir. | git dışı |
| `results_norewrite.json` | `evaluate.py --k 5 --no-rewrite` | Aynı 8 soru, yeniden yazım kapalı: Madde@5 %62, MRR 0.46 | git dışı |
| `answers.json` | `answer_eval.py --judge` | 7 soru: RAG atıf doğruluğu %86, halüsinasyon %0, sadakat 5.0; salt LLM atıf %71, halüsinasyon %29. Tam cevap metinleri içinde. | git dışı |
| `answers_check.json` | `answer_eval.py --limit 2 --judge` | Prompt düzeltmesinden sonra ihbar süresi ve m. 24 sorularının kontrol koşusu | git dışı |

Markdown dosyaları tezde doğrudan tablo olarak kullanılabilir; JSON dosyaları aynı verinin program tarafından okunabilir halidir.

### `eval/indexes/`

`experiments.py` her parçalama biçimi için ayrı bir FAISS indeksi kurar ve burada saklar. Klasör adı `parçalama__embeddingmodeli` biçimindedir. Her birinde `vectorstore/` ile aynı üç dosya bulunur (`index.faiss`, `index.pkl`, `signature.json`).

| Klasör | Parçalama | Parça sayısı |
|---|---|---|
| `madde__text-embedding-3-small` | Madde tabanlı, uygulamanın o anki varsayılanı (bu indeks `CHUNK_SIZE` 1200 iken kuruldu; imzada parça boyutu tutulmadığı için yeniden kurulmaz) | 577 |
| `madde-600__text-embedding-3-small` | Madde tabanlı, 600/75 | 902 |
| `fixed__text-embedding-3-small` | Sabit boyut, 1000/200 | 538 |
| `fixed-500__text-embedding-3-small` | Sabit boyut, 500/100 | 1060 |

Git dışıdır; silinirse bir sonraki `experiments.py` koşusunda yeniden kurulur (embedding maliyeti).

---

## 8. `docs/` klasörü: belgeler

| Dosya | İçerik |
|---|---|
| `PROJE_5N1K.md` | Tez danışmanı için hazırlanan 5N1K dokümanı: proje nedir, neden yapılıyor, nasıl çalışıyor, dosyalar nerede, takvim, roller, plan ile karşılaştırma, test sonuçları. Canlı (etkileşimli) sürümünün bağlantısı başında yazar. |
| `DOSYA_REHBERI.md` | Bu belge. |
| `HUKUKASISTAN_FONKSIYONLAR.md` | `HukukAsistan.py` içindeki her sabit, desen, sınıf ve fonksiyonun parametreleri, dönüş değerleri ve örneklerle açıklaması. |

---

## 9. Dosyalar birbirini nasıl kullanır?

```
.env ──(OPENAI_API_KEY)──► HukukAsistan.py ◄──(import)── tools/*.py
                                 │                            │
          PDFs/*.pdf ──(okur)────┤                            │ okur: eval/questions.json
                                 │                            │ yazar: eval/results.json, answers.json,
          vectorstore/ ◄─(yazar/okur)┘                        │        experiments.md/.json, eval/indexes/
```

- `HukukAsistan.py` tek başına çalışır; `PDFs/` ve `.env` dışında hiçbir şeye ihtiyacı yoktur. `vectorstore/` ve `chats/` klasörlerini kendisi üretir.
- `tools/` betikleri `HukukAsistan.py` olmadan çalışmaz; onun fonksiyonlarını çağırır.
- `eval/` içindeki çıktı dosyaları yalnızca `tools/` betikleri tarafından yazılır; uygulama bunları okumaz.
- Belgeler (`README.md`, `docs/`, `*.md`) hiçbir program tarafından okunmaz; yalnızca insanlar için.

---

## 10. Hangi dosyayı silebilirim?

| Dosya / klasör | Silinirse | Geri gelir mi |
|---|---|---|
| `__pycache__/` | Hiçbir şey olmaz | Evet, otomatik |
| `vectorstore/` | Uygulama bir sonraki açılışta indeksi yeniden kurar (~20 s, embedding maliyeti) | Evet, otomatik |
| `eval/indexes/` | `experiments.py` bir sonraki koşuda yeniden kurar | Evet, otomatik |
| `chats/` | Tüm sohbet geçmişi silinir; uygulama boş listeyle açılır | Hayır (kişisel veri); tek sohbet için arayüzdeki 🗑️ düğmesini kullanın |
| `eval/results*.json`, `eval/answers*.json`, `eval/experiments*.json` | Deney sonuçları gider; betikleri yeniden çalıştırmak gerekir (API maliyeti) | Yeniden koşunca |
| `.venv/` | Hiçbir şey çalışmaz; kütüphaneleri yeniden kurmanız gerekir | Elle: `pip install -r requirements.txt` |
| `.env` | Uygulama "OPENAI_API_KEY bulunamadı" hatası verir | Elle: anahtarı yeniden yazın |
| `PDFs/*.pdf` | O kanun aramadan çıkar; indeks otomatik yenilenir | Elle: mevzuat.gov.tr'den indirin |
| `HukukAsistan.py`, `tools/*.py` | Proje çalışmaz | Yalnızca git geçmişinden (`git checkout`) |
| `eval/experiments.md`, `*_chunksize.*` | Tez tabloları gider | Git geçmişinden veya yeniden koşarak |

---

## 11. "Şunu yapmak istiyorum, hangi dosyaya bakmalıyım?"

| İstek | Dosya |
|---|---|
| Uygulamayı çalıştırmak | Proje klasöründe `.venv\Scripts\streamlit run HukukAsistan.py` (sanal ortamı etkinleştirmeye gerek yok) |
| Yeni bir kanun eklemek | PDF'i `PDFs/` klasörüne koy, `python tools/inspect_pdf.py` ile kontrol et |
| Kanun kısaltması eklemek ("TBK" gibi) | `HukukAsistan.py` → `LAW_ALIASES` sözlüğü |
| Cevap tarzını değiştirmek | `HukukAsistan.py` → `QA_PROMPT` |
| Parça boyutunu, k değerini, modeli değiştirmek | `HukukAsistan.py` → dosya başındaki ayarlar; sonra `INDEX_VERSION` artır veya `vectorstore/` sil |
| Sorgu yeniden yazımını kapatmak | `HukukAsistan.py` → `QUERY_REWRITE = False` |
| Örnek soruları değiştirmek | `HukukAsistan.py` → `EXAMPLE_QUESTIONS` |
| Eski bir sohbete dönmek | Yan panel → "Sohbetler" listesinde tıkla; dosyası `chats/` klasöründe |
| Sohbet başlığının uzunluğunu değiştirmek | `HukukAsistan.py` → `CHAT_TITLE_LEN` |
| Arayüz renklerini değiştirmek | `HukukAsistan.py` → `CSS` içindeki `--ha-accent` |
| Altın soru seti hazırlamak | `eval/questions.example.json` biçiminde `eval/questions.json` oluştur |
| Tez için geri getirim tablosu üretmek | `python tools/experiments.py ...` → `eval/experiments.md` |
| Tez için halüsinasyon oranı üretmek | `python tools/answer_eval.py ... --judge` → `eval/answers.json` |
| İnsan değerlendirmesi düzenlemek | `eval/INSAN_DEGERLENDIRME.md` |
| Hangi sürümlerle çalıştığını belgelemek | `requirements.lock.txt` |
| Projeyi başkasına anlatmak | `README.md`, `docs/PROJE_5N1K.md` |
| Bir fonksiyonun ne yaptığını öğrenmek | `docs/HUKUKASISTAN_FONKSIYONLAR.md` |
