# Hukuk Asistan Chatbot: 5N1K Proje Dokümanı

8 Kasım 2026 · Canlı sürüm: https://claude.ai/artifact/NGTzn92QX4hrfNz44qrpXJ

## Ne? Proje nedir

Hukuk Asistan Chatbot, mevzuat.gov.tr'den indirilen kanun ve yönetmelik PDF'lerini okuyup soruları yalnızca bu metinlere dayanarak, kanun adı ve madde numarası atfıyla cevaplayan Türkçe bir RAG (Retrieval Augmented Generation) sohbet uygulamasıdır. Medicine Hospital QA projesinin aynı mimarisi üzerine kuruludur; "ilaç" yerine "kanun", "prospektüs bölümü" yerine "madde" etiketi kullanır.

| Bileşen | Dosya | Ne yapar |
| --- | --- | --- |
| Sohbet arayüzü | HukukAsistan.py (main, render_message) | Karşılama kartı, 4 örnek soru, kanun rozeti, "Kaynaklar" açılır listesi, sohbeti temizleme, yüklü mevzuat listesi |
| İndeksleyici | HukukAsistan.py (load_pages, _segment_articles, build_chunks) | Sayfa başlığından kanun adı ve numarası, madde sınırlarından bölme, kalıcı FAISS indeksi |
| Soru yönlendirici | detect_laws, MevzuatRetriever | Kanun adı, kısaltma (KVKK, TBK) ve numara ("4857 sayılı") algılama; soruyu kanun diline çeviren yeniden yazım (rewrite_query); filtreli veya genel arama, RRF birleştirme |
| Cevap üretici | create_answer, QA_PROMPT | gpt-4o-mini ile yalnızca alıntılara dayalı, madde atıflı cevap |
| PDF kontrolü | tools/inspect_pdf.py | Kanun, sayfa aralığı, madde ve mülga sayımı (API çağrısı yapmaz) |
| Geri getirim ölçümü | tools/evaluate.py | Kanun@k, Madde@k, MRR |
| Ablasyon deneyleri | tools/experiments.py | Madde tabanlı ve sabit boyutlu parçalama, filtreli ve filtresiz arama, embedding modeli, k taraması |
| Cevap ölçümü | tools/answer_eval.py | Atıf doğruluğu, desteksiz atıf (halüsinasyon) oranı, RAG ve salt LLM karşılaştırması, model tabanlı sadakat puanı |
| Karşılaştırma tabanı | tools/baseline_naive.py | Her soruda tüm PDF'i yeniden okuyan, etiketsiz ve filtresiz basit RAG |

Örnek akış, soru "KVKK'ya göre veri sorumlusu başvuruma kaç günde cevap vermeli?":

1. "kvkk" kısaltması LAW_ALIASES tablosuyla Kişisel Verilerin Korunması Kanunu'na eşlenir; arama yalnızca bu kanunun parçalarıyla sınırlanır.
2. En yakın parça "[KİŞİSEL VERİLERİN KORUNMASI KANUNU | Madde 13 | Veri sorumlusuna başvuru]" bağlam etiketiyle gelir.
3. Model alıntıya dayanarak cevap verir: veri sorumlusu talebi en geç otuz gün içinde sonuçlandırır, dayanak Madde 13.
4. Cevabın üstünde kanun rozeti, altında "Kaynaklar" satırı görünür: KİŞİSEL VERİLERİN KORUNMASI KANUNU · Madde 13 · s. 7.
5. Takip sorusu "Peki Kurula şikâyet süresi?" kanun adı içermese de sohbet geçmişinden aynı kanuna yönlendirilir.

## Neden? Problem ve motivasyon

Vatandaş hakkını ilgili kanun ve maddeden öğrenmek ister; mevzuat dili ve binlerce sayfaya dağılmış yapı buna engeldir. Genel amaçlı sohbet modelleri ise kaynak göstermez ve madde numarası uydurabilir. Proje iki sorunu birlikte ele alır: cevaplar yalnızca resmi metne dayanır, her iddia madde atfı taşır ve doğruluk sayıyla ölçülür.

| Gerekçe | Projedeki karşılığı (örnek) |
| --- | --- |
| Doğruluk nesnel ölçülür | "2 yıl çalışan işçinin ihbar süresi" sorusunun doğru cevabı İş Kanunu m. 17'dir; tools/evaluate.py bu maddenin ilk k parçada gelme oranını (Madde@k) ölçer |
| Veri resmi, ücretsiz ve telif dışı | PDF'ler mevzuat.gov.tr'den alınır; 5846 sayılı FSEK m. 31 kanun, yönetmelik ve kararların çoğaltılmasını serbest bırakır |
| Yapı makineye uygun | "Kanun Numarası : 4857" künyesi ve "Madde 17 –" başlıkları TITLE_RE ve ARTICLE_RE desenleriyle yakalanır; test PDF'inde 30 maddenin 30'u doğru etiketlendi |
| Gerçek teknik zorluk | "Geçici Madde 2 – (Mülga: ...)" mülga olarak işaretlenir; aynı adlı iki kanun "İŞ KANUNU" ve "İŞ KANUNU (1475)" olarak ayrılır |
| Halüsinasyon kontrolü | QA_PROMPT "madde numarası veya hüküm uydurma" der; tools/answer_eval.py cevaptaki her atıfı indeksteki maddelerle karşılaştırıp desteksiz atıfları sayar |
| Toplumsal fayda | Örnek sorular günlük hayattan: kıdem ve ihbar tazminatı, kira feshi, ayıplı mal, kişisel verinin silinmesi |
| Literatür boşluğu | İngilizce için LegalBench ve LexGLUE var; Türkçe mevzuat için madde düzeyinde açık bir RAG ölçütü yaygın değil (literatür taramasında doğrulanacak) |

Tezin araştırma soruları ve projedeki ölçüm yeri:

1. Madde tabanlı parçalama sabit boyutlu parçalamaya göre doğru maddeyi daha sık getirir mi? tools/experiments.py, "madde" ve "fixed" satırları.
2. Kanun yönlendirmeli filtreli arama genel aramaya göre Madde@k ve MRR'yi artırır mı? tools/experiments.py, "filtre on/off" satırları.
3. RAG, salt LLM'e göre desteksiz madde atfını ne kadar azaltır? tools/answer_eval.py, RAG ve Salt LLM özeti.
4. Farklı embedding modelleri Türkçe hukuki metinde nasıl sıralanır? tools/experiments.py --embeddings parametresi.
5. Mülga ve değişik maddeler cevap doğruluğunu nasıl etkiler? metadata "mulga" alanı ve hata analizi (gelecek çalışma: yürürlük tarihine duyarlı arama).

## Nasıl? Mimari ve yöntem

Sistem iki aşamada çalışır: PDF'ler bir kez okunup kanun ve madde etiketli bir FAISS indeksine dönüştürülür; her soruda ise kanun tespiti, filtreli vektör arama ve yalnızca alıntılara dayalı cevap üretimi yapılır.

*(Mimari diyagram: README.md içindeki Mermaid şeması; etkileşimli sürüm Claude Doc'ta.)*

Üst hat PDF değiştiğinde bir kez çalışır; alt hat her soruda çalışır ve vurgulu FAISS indeksi iki hattı bağlar.

**1. Kanun etiketi (load_pages).** Her sayfanın ilk 1500 karakterinde künye satırı (Kanun Numarası, Kabul Tarihi, Resmî Gazete) aranır; varsa büyük harfli başlık kanun adı olur ve sonraki sayfalara taşınır. Aynı adlı iki kanun numarayla ayrılır.

```python
TITLE_RE = re.compile(r"((?:[A-ZÇĞİÖŞÜ0-9][A-ZÇĞİÖŞÜ0-9'’.,()\-]*\s+){0,14}"
                      r"(?:KANUN HÜKMÜNDE KARARNAME|...|KANUNU|KANUN|YÖNETMELİĞİ|YÖNETMELİK|...))")
META_RE  = re.compile(r"Kanun\s+Numaras[ıi]|Kabul\s+Tarihi|Resm[îi]\s+Gazete|...", re.I)
# "8423  İŞ KANUNU  Kanun Numarası : 4857"  ->  law="İŞ KANUNU", law_no="4857"
```

**2. Madde sınırlarından bölme (_segment_articles).** "Madde 17 –", "MADDE 1-", "Ek Madde 2 –", "Geçici Madde 6 –" başlıkları kesme noktasıdır; başlığın üstündeki kısa satır madde başlığı ("Süreli fesih") olur; "(Mülga" ile başlayan gövde mülga işaretlenir. Sayfa sonunda biten madde sonraki sayfada devam eder.

```python
ARTICLE_RE = re.compile(r"(?<!\w)((?:EK|Ek|GEÇİCİ|Geçici|MÜLGA|Mülga)\s+)?(MADDE|Madde)\s+(\d+)\s*[-–—]")
# metadata: law="İŞ KANUNU", law_no="4857", madde="Madde 17", madde_no=17, baslik="Süreli fesih", mulga=False, page=1
```

**3. Parçalama ve bağlam etiketi (build_chunks).** 600 karakteri aşan maddeler 80 karakter örtüşmeyle bölünür (gerçek veri deneyinde 1200 yerine 600 seçildi; bkz. Test sonuçları). Her parçanın başına etiket eklenir, böylece embedding kanun ve madde bilgisini de görür:

```text
[İŞ KANUNU | Madde 17 | Süreli fesih]
Belirsiz süreli iş sözleşmelerinin feshinden önce durumun diğer tarafa bildirilmesi gerekir. ...
```

**4. Kalıcı indeks (load_or_build_index).** text-embedding-3-small ile embed edilen parçalar vectorstore/ klasörüne yazılır. signature.json dosyası PDF adı, boyutu, değişiklik zamanı, parçalama ayarları ve embedding modelini tutar; biri değişince indeks kendiliğinden yenilenir. Embedding istekleri 200 parçalık gruplarla gönderilir (OpenAI'nin istek başına 300 bin token sınırı).

**5. Soru yönlendirme (detect_laws, MevzuatRetriever).** Soruda kanun adı ("İş Kanunu'na göre"), kısaltma ("KVKK", "TBK") veya numara ("4857 sayılı") geçiyorsa arama o kanunla sınırlanır (TOP_K = 8). Geçmiyorsa ve soru bir durum sorusuysa ("haklarım neler", "hangi kanun") tüm mevzuatta aranır (GENERAL_K = 10). Takip sorusunda ("Peki ihbar süresi?") sohbette en son geçen kanun kullanılır. Ayrıca soru kısa bir LLM çağrısıyla kanun diline çevrilir ("ihbar süresi" → "bildirim süresi"); özgün soru ve çeviri ayrı aranır, iki liste Reciprocal Rank Fusion ile birleştirilir (QUERY_REWRITE, rrf_merge). Kullanılan çeviri arayüzde Kaynaklar altında görünür.

```python
detect_laws("KVKK'ya göre verilerim silinir mi", catalog)   # ['KİŞİSEL VERİLERİN KORUNMASI KANUNU']
detect_laws("1475 sayılı kanun kıdem", catalog)             # ['İŞ KANUNU (1475)']
detect_laws("borçlarımı ödeyemiyorum ne olur", catalog)      # []  (tek sözcüklü çekirdek kullanılmaz, yanlış eşleşme yok)
db.similarity_search(q, k=6, fetch_k=db.index.ntotal, filter=lambda md: md.get("law") in wanted)
```

**6. Cevap üretimi (create_answer, QA_PROMPT).** ConversationalRetrievalChain takip sorusunu geçmişle birleştirip bağımsız soruya çevirir, parçaları getirir ve gpt-4o-mini'ye (temperature 0.2) verir. Sistem istemi: yalnızca alıntılara dayan, her iddiada kanun adı ve madde numarası ver, uydurma, mülga ise söyle, durum sorusunda uygulanabilecek kanun ve maddeleri koşullarıyla say, sonda kısa avukat ve adli yardım hatırlatması yap.

**7. Arayüz (main).** Streamlit sohbet bileşenleri; kanun rozeti, "Kaynaklar" açılır listesi ("İŞ KANUNU · Madde 17, Madde 18 · s. 2"), yan panelde yüklü mevzuat ve madde sayıları, 640 piksel altı ekranlar için CSS medya sorgusu.

**8. Değerlendirme.**

| Komut | Ölçtüğü | LLM çağrısı |
| --- | --- | --- |
| python tools/inspect_pdf.py | Kanun, sayfa, madde, mülga sayımları | Yok |
| python tools/evaluate.py eval/questions.json --k 5 | Kanun@k, Madde@k, MRR | Yok (yalnızca embedding) |
| python tools/experiments.py eval/questions.json --k 1,3,5,10 | Parçalama, filtre, embedding modeli ve k ablasyonu | Yok |
| python tools/answer_eval.py eval/questions.json --judge | Atıf doğruluğu, desteksiz atıf oranı, RAG ve salt LLM, sadakat puanı | Soru başına 3 |
| python tools/baseline_naive.py "soru" | Her soruda tüm PDF'i okuyan tabanın cevabı ve süreleri | 1 + embedding |
| eval/INSAN_DEGERLENDIRME.md | 5 ölçütlü Likert rübriği, kör değerlendirme, kappa | Yok |

## Nerede? Dosyalar, veri ve ortamlar

Proje bilgisayarda C:\\Users\\Fetta\\Desktop\\HukukAsistanChatbot klasöründedir. Mevzuat PDF'leri PDFs/ altına konur, indeks vectorstore/ altında saklanır, ölçüm betikleri tools/ ve soru setleri eval/ altındadır.

| Yol | İçerik |
| --- | --- |
| HukukAsistan.py | Uygulama, indeksleme ve arama; tek dosya, ayarlar dosyanın başında (PDF_DIR, CHUNK_SIZE, TOP_K, CHAT_MODEL) |
| PDFs/ | 4857 İş Kanunu, 6502 TKHK ve 6698 KVKK resmi PDF'leri (eklendi, 194 sayfa) ve "Kira Hukuku.pdf" ders sunumu (telif nedeniyle git dışı); 6098 TBK eklenmesi önerilir |
| vectorstore/ | FAISS indeksi (index.faiss, index.pkl) ve signature.json; git dışı, ilk çalıştırmada oluşur |
| tools/ | inspect_pdf.py, build_index.py, evaluate.py, experiments.py, answer_eval.py, baseline_naive.py |
| eval/ | questions.example.json (soru şeması), INSAN_DEGERLENDIRME.md (protokol); çalıştırınca results.json, experiments.md, answers.json |
| requirements.txt, requirements.lock.txt | Bağımlılıklar ve sabitlenmiş sürümler (streamlit 1.67.0, langchain 0.3.30, faiss-cpu 1.15.1, pypdf 7.0.0) |
| .env, .env.example | OPENAI_API_KEY; .env git dışıdır ve kopyalanmıştır |
| README.md | Kurulum, çalıştırma, mimari diyagram, veri kaynağı ve telif notu |
| .venv/ | Python 3.12.16 sanal ortam (uv ile kuruldu); git dışı |

**Veri nerede bulunur.** Kanunlar mevzuat.gov.tr'de kanun sayfasının üstündeki PDF bağlantısından, yönetmelikler aynı siteden veya Resmî Gazete'den indirilir. Tez kapsamı için önerilen dört metin: 4857 sayılı İş Kanunu, 6098 sayılı Türk Borçlar Kanunu kira hükümleri, 6502 sayılı Tüketicinin Korunması Hakkında Kanun, 6698 sayılı Kişisel Verilerin Korunması Kanunu.

**Nerede çalışır.** Yerel bilgisayarda "streamlit run HukukAsistan.py" ile http://localhost:8501 adresinde; aynı Wi-Fi ağındaki telefonda "--server.address 0.0.0.0 --server.port 8502" seçenekleri ve güvenlik duvarı izniyle; tarayicıda 640 piksel altı ekranlar için ayrı stil kuralları vardır. Embedding ve sohbet modelleri OpenAI API'de çalışır; indeks kurulurken PDF metni OpenAI'ye gönderilir (kamuya açık resmi metin).

**Kod nerede saklanır.** Proje klasörü yerel bir git deposudur (.gitignore: .env, .venv/, vectorstore/, eval/indexes/). GitHub'a yükleme kullanıcının isteğiyle yapılır; önceki proje https://github.com/FTonka/MedicineHospitalQA-Chatbot-LLM-Project adresindedir.

## Ne zaman? Takvim ve süreler

Plan dört aya (haftalık sıkıştırılmış sürümde dört haftaya) yayılır. 8 Kasım 2026 itibarıyla dört aşamanın yazılım tarafı hazırdır; sırada gerçek mevzuat PDF'lerinin eklenmesi, literatür taraması, altın soru seti, deneylerin koşulması ve tez yazımı vardır.

*(Plan diyagramı Claude Doc'ta; metin karşılığı aşağıdaki "Plan ile karşılaştırma" tablosudur.)*

Alt band her aşamanın bugünkü durumunu gösterir: kod ve betikler tamamlandı, veri ve deney adımları kullanıcıya kalmıştır.

| Olay | Ne zaman olur | Not |
| --- | --- | --- |
| İndeks kurulumu | Yalnızca ilk çalıştırmada; PDF değişince, INDEX_VERSION artınca veya vectorstore/ silinince yeniden | Gerçek mevzuat (194 sayfa, 907 parça) 18.8 saniyede kuruldu; 10 sayfalık sentetik PDF 10.8 saniye |
| İndeks yükleme | Her sunucu başlangıcında diskten | 1 saniyenin altında |
| Filtreli arama | Soruda kanun adı, kısaltma veya "... sayılı" numara geçtiğinde | Örnek: "KVKK'ya göre" sorusu yalnızca 6698 sayılı kanunda aranır |
| Sohbet bağlamından kanun | Kanun adı geçmeyen ve durum sorusu olmayan takip sorularında | Örnek: "Peki Kurula şikâyet süresi?" |
| Cevap üretimi | Her soruda: arama + gpt-4o-mini | Süre ölçümü Test sonuçları bölümünde |
| Avukat ve adli yardım hatırlatması | Her cevabın sonunda, kısa | Prompt gereği cevabın yerine geçmez |

## Kim? Roller ve kullanıcılar

Projeyi tez öğrencisi olarak siz geliştirir ve savunursunuz; danışman araştırma sorularını ve kapsamı onaylar; son kullanıcı hukukçu olmayan vatandaştır.

| Rol | Kim | Projedeki örnek |
| --- | --- | --- |
| Geliştirici ve tez öğrencisi | Proje sahibi (GitHub: FTonka) | Mevzuat PDF'lerini ekler, altın soru setini hazırlar, deneyleri koşar, tezi yazar |
| Danışman öğretim görevlisi | Tez danışmanı | Kapsamı (4 kanun), araştırma sorularını ve değerlendirme tasarımını onaylar; bu doküman ikna materyalidir |
| Son kullanıcı | Vatandaş, işçi, kiracı, tüketici | "İşten çıkarıldım, kıdem ve ihbar tazminatı alabilir miyim?" sorusuna kanun ve madde atfıyla cevap alır |
| Kurumsal kullanıcı | İK uzmanı, KOBİ sahibi, müşteri hizmetleri | "4857 sayılı kanuna göre yıllık izin süresi" gibi mevzuat kontrolü |
| Hukuk öğrencisi | Lisans ve hazırlık öğrencileri | Madde bulma ve kaynak gösterimiyle çalışma aracı |
| İnsan değerlendirici | 2 veya daha fazla hukuk öğrencisi, araştırma görevlisi ya da avukat | eval/INSAN_DEGERLENDIRME.md protokolüyle kör değerlendirme, kappa uyumu |
| Veri sağlayıcı | mevzuat.gov.tr (Cumhurbaşkanlığı Mevzuat Bilgi Sistemi), Resmî Gazete | Resmi kanun ve yönetmelik PDF'leri; FSEK m. 31 ile serbest kullanım |
| Teknoloji bileşenleri | OpenAI (gpt-4o-mini, text-embedding-3-small), Streamlit, LangChain, FAISS, pypdf | Cevap üretimi, embedding, arayüz, zincir, vektör arama, PDF okuma |
| Geliştirme yardımcısı | Claude Code (Claude Fable 5.1) | Kodun ve betiklerin yazımı, sentetik veriyle test, bu doküman |

Kime yönelik değildir: acil hukuki işlem, süre kaçırma riski olan dava veya başvuru kararları. Her cevap bu nedenle avukata ya da baroların adli yardım bürosuna yönlendirmeyle biter; arayüzde kalıcı uyarı notu vardır.

## Plan ile karşılaştırma

Planın 21 maddesinden 14'ü projede hazırdır, 4'ü kısmen (yazılım tarafı hazır, gerçek veri veya kullanıcı adımı bekliyor), 3'ü doğası gereği kullanıcıya aittir (literatür taraması, altın soru havuzu, tez yazımı). Durum sütunu değiştirilebilir; ilerledikçe güncelleyin.

| Hafta | Plan maddesi | Projedeki karşılığı | Durum |
| --- | --- | --- | --- |
| 1 | Literatür taraması, araştırma soruları ve hipotezler | Bu dokümanda 5 araştırma sorusu ve ölçüt adları (LegalBench, LexGLUE); tarama yapılacak | Kullanıcıda |
| 1 | Kapsam: en çok sorulan 4 kanun | README ve PDFs/README: 4857 İş K., 6098 TBK kira, 6502 TKHK, 6698 KVKK | Hazır |
| 1 | Veri toplama, birleştirme, FSEK 31 belgesi | Üç resmi kanun PDF'i PDFs/ klasöründe (4857, 6502, 6698); README telif bölümü; kira için 6098 TBK eklenecek | Kısmen |
| 1 | Geliştirme ortamı: Python 3.12, venv, sabitleme, .env, git | .venv (3.12.16, uv), requirements.lock.txt, .env kopyalandı, yerel git deposu (a1c87e0) ve v0.1.0 etiketi | Hazır |
| 1 | PDF yapı analizi betiği | tools/inspect_pdf.py: kanun, sayfa aralığı, madde ve mülga sayımı | Hazır |
| 1 | Her soruda tüm PDF'i okuyan basit prototip | tools/baseline_naive.py: süre ve cevap karşılaştırma tabanı | Hazır |
| 1 | Tez önerisi | Bu doküman ve bir önceki sohbetteki gerekçe listesi | Hazır |
| 2 | Kanun ve madde etiketleme, harf katlama, mülga işareti | load_pages, _segment_articles, _fold; metadata law, law_no, madde, baslik, mulga | Hazır |
| 2 | Madde tabanlı parçalama ve bağlam ön eki | build_chunks: "[KANUN · Madde N · Başlık]" ön eki | Hazır |
| 2 | Kalıcı FAISS indeksi, imza, toplu embedding | load_or_build_index, _index_signature, chunk_size=200 | Hazır |
| 2 | Soru yönlendirme: ad, kısaltma, numara; filtreli, genel, takip | detect_laws, LAW_ALIASES, is_situation_question, MevzuatRetriever | Hazır |
| 2 | Prompt tasarımı | QA_PROMPT; test sırasında eklenen "aralıkları önce listele" kuralı | Hazır |
| 3 | Sohbet arayüzü | main: karşılama kartı, örnek sorular, rozet, Kaynaklar, temizleme, yüklü mevzuat | Hazır |
| 3 | Mobil uyum, yerel ağ, telefon testi, güvenlik duvarı | CSS medya sorgusu ve 0.0.0.0 komutu hazır; telefon testi ve güvenlik duvarı izni kullanıcıda | Kısmen |
| 3 | Altın veri seti | eval/questions.example.json şeması ve 8 örnek; SSS ve karar havuzu kullanıcıda | Kullanıcıda |
| 3 | Değerlendirme kodu: Recall@k, MRR, atıf, halüsinasyon, model ve insan değerlendirmesi | tools/evaluate.py, tools/answer_eval.py (--judge), eval/INSAN_DEGERLENDIRME.md | Hazır |
| 4 | Deneyler: parçalama, filtre, RAG vs LLM, embedding, k | Gerçek veriyle ilk koşu yapıldı (8 soru): parça boyutu 600 ve sorgu yeniden yazımı seçildi; tam altın setle tekrarlanacak | Kısmen |
| 4 | Hata analizi | Bulgular: aralık seçim hatası (prompt kuralı), kelime boşluğu ihbar/bildirim (yeniden yazım), m. 24 ile m. 25 karışması (parça boyutu) | Kısmen |
| 4 | Dokümantasyon, mimari diyagram, GitHub, sürüm etiketi | README (Mermaid diyagram), kod yorumları, .env.example, v0.1.0; GitHub'a yükleme isteğe bağlı | Kısmen |
| 4 | Tez yazımı | Yöntem ve deney tasarımı bu dokümandan alınabilir | Kullanıcıda |
| 4 | Sunum ve demo | Uygulama demo için hazır; sunum kullanıcıda | Kısmen |

## Test sonuçları ve hızlı başlangıç

Boru hattı önce 10 sayfalık sentetik bir PDF ile, ardından kullanıcının eklediği gerçek mevzuatla test edildi: 4857 İş Kanunu (55 sayfa, 136 madde, 18 mülga), 6502 TKHK (53 sayfa, 91 madde), 6698 KVKK (21 sayfa, 36 madde) ve madde yapısı olmayan bir kira hukuku ders sunumu (65 sayfa). Üç resmi metinde her sayfa ve her madde doğru etiketlendi. Gerçek veri sonuçları hemen aşağıda, sentetik ön test onun altındadır; 8 soruluk örnek set tez sonucu değil, yöntem seçimi için ilk kanıttır.

**Gerçek mevzuat, geri getirim (eval/questions.example.json, 8 soru).** Kira sorusunun altın kaynağı TBK yüklenmediği için bulunamaz; diğer 7 soru cevaplanabilir. İlk koşuda iki İş Kanunu sorusu başarısızdı: soru "ihbar süresi" derken kanun "bildirim süresi" yazıyordu (kelime boşluğu); "ücret ödenmezse derhal fesih" sorusunda işverenin m. 25'i işçinin m. 24'ünü gölgeliyordu. Sorgu yeniden yazımı ilkini, 600 karakterlik parçalar ve k = 10 ikincisini çözdü.

| Yapılandırma | k | Kanun@k | Madde@k | MRR |
| --- | --- | --- | --- | --- |
| madde 1200, yeniden yazım kapalı | 5 | %88 | %62 | 0.46 |
| madde 1200, yeniden yazım açık | 5 | %88 | %75 | 0.54 |
| madde 600, yeniden yazım açık | 10 | %88 | %88 | 0.48 |
| fixed 500, yeniden yazım açık | 5 | %88 | %88 | 0.54 |

Sabit boyutlu 500 karakterlik parçalama bu küçük sette madde tabanlı parçalamadan geri kalmadı; RQ1 bu nedenle açık bir sorudur ve tam altın setle sınanmalıdır. Filtre açık veya kapalı fark yaratmadı, çünkü 8 sorunun yalnızca birinde kanun adı geçiyordu. Tüm satırlar eval/experiments.md ve eval/experiments_chunksize.md dosyalarındadır.

**Gerçek mevzuat, cevap düzeyi (7 soru, --judge).** RAG 7 sorunun 6'sında altın maddeyi atfetti ve hiçbir cevapta desteksiz atıf üretmedi; salt LLM 5'inde doğru atfetti ve 2 cevapta indekste bulunmayan maddelere atıf yaptı (bir Tüketici Kanunu cevabında 4 uydurma madde). Başarısız RAG cevabı m. 24 sorusuydu; parça boyutu değişikliğinden sonra aynı soru m. 24 atfıyla doğru cevaplandı. Model tabanlı hakem her cevaba 5/5 verdi; hatalı cevabı da yakalamadı, bu yüzden insan değerlendirmesi şarttır.

**Sentetik ön test (10 sayfa).** Aşağıdaki sayılar gerçek veriden önce, mevzuat.gov.tr düzenini taklit eden sentetik PDF ile alındı.

**Etiketleme (tools/inspect_pdf.py).** 10 sayfanın 10'u doğru kanuna, 30 maddenin 30'u doğru numaraya bağlandı; 35 parça oluştu.

| Kanun / yönetmelik | No | Sayfa | Madde | Mülga |
| --- | --- | --- | --- | --- |
| İŞ KANUNU | 4857 | 1-4 | 11 | 1 |
| İŞ KANUNU (1475) | 1475 | 5 | 2 | 0 |
| KİŞİSEL VERİLERİN KORUNMASI KANUNU | 6698 | 6-7 | 6 | 0 |
| TÜKETİCİNİN KORUNMASI HAKKINDA KANUN | 6502 | 8-9 | 5 | 0 |
| İŞ KANUNUNA İLİŞKİN FAZLA ÇALIŞMA ... YÖNETMELİĞİ | - | 10 | 6 | 0 |

**Geri getirim (tools/evaluate.py, 10 soru, k = 5).** Kanun@5 %100, Madde@5 %100, MRR 0.82. Beş soruda kanun algılandı ve filtre devreye girdi ("İş Kanunu'na göre", "KVKK'ya göre", "1475 sayılı", "Tüketici kanununa göre"); beş durum sorusu tüm mevzuatta arandı ve yine doğru maddeyi buldu.

**Ablasyon (tools/experiments.py).** 10 soruda madde tabanlı ve sabit boyutlu parçalama arasındaki fark tek soru düzeyindedir; k = 3'te madde tabanlı %100, sabit boyutlu %90 Madde@k verdi, k = 1'de ise tersi. Bu kadar küçük sette hipotez sınanamaz; gerçek veri ve 200-300 soruluk altın set gerekir.

| Parçalama | k | Madde@k | MRR@k |
| --- | --- | --- | --- |
| madde | 1 | %70 | 0.70 |
| madde | 3 | %100 | 0.82 |
| fixed | 1 | %80 | 0.80 |
| fixed | 3 | %90 | 0.85 |

**Cevap düzeyi (tools/answer_eval.py, 3 soru, --judge).** İlk koşuda RAG üç soruda da doğru maddeyi atfetti ve desteksiz atıf üretmedi; salt LLM bir cevapta indekste bulunmayan "TBK m. 34" atfı yaptı (3 cevapta 1 halüsinasyon). Buna karşın RAG, 2 yıl çalışan işçinin ihbar süresini "4 hafta" diye yanlış verdi (doğrusu 6 hafta; m. 17 getirilmiş ama yanlış aralık seçilmişti) ve model tabanlı hakem buna 5/5 sadakat puanı verdi. İki sonuç çıkar: atıf ölçütleri tek başına yetmez, insan değerlendirmesi gerekir; gpt-4o-mini aralık seçiminde zorlanır. Prompt'a "önce hükümdeki tüm aralıkları listele, sonra aralığı seç" kuralı eklendi; sonraki koşuda ve arayüzde cevap "6 hafta" oldu. Aynı soruda gpt-4o düzeltme olmadan da doğru cevap verdi; model seçimi tezde bir deney değişkeni olabilir (CHAT_MODEL sabiti).

**Karşılaştırma tabanı (tools/baseline_naive.py).** Her soruda 24 parçayı yeniden embed etti (10 sayfada toplam 3.9 saniye, embedding 1.5 saniye) ve aynı ihbar sorusuna "4 hafta" dedi. Aynı yaklaşım 485 sayfalık ilaç PDF'inde soru başına yaklaşık 85 saniye sürmüştü; kalıcı indeksle cevap 2-4 saniyeye iner.

**Süreler.** İndeks kurulumu 10.8 saniye (35 parça). Filtreli KVKK sorusu 1.9 saniye, filtresiz durum sorusu (ayıplı mal) 4.0 saniye.

**Arayüz.** Chrome'da doğrulandı: karşılama kartı ve 4 örnek soru, "İŞ KANUNU, İŞ KANUNU (1475)" rozeti, cevap, "Kaynaklar" açılır listesi ve sorumluluk notu. Dar ekran görünümü tasarımla sağlanır, telefonda henüz denenmedi.

**Hızlı başlangıç**

1. mevzuat.gov.tr'den indirdiğiniz PDF'leri PDFs/ klasörüne koyun (tek birleşik dosya veya kanun başına bir dosya).
2. python tools/inspect_pdf.py ile kanun ve madde sayılarını kontrol edin; "Bilinmiyor" satırı varsa bana bildirin, başlık desenini ayarlarım.
3. streamlit run HukukAsistan.py; ilk açılış indeksi kurar, sonrakiler diskten yükler.
4. eval/questions.example.json şemasıyla altın soru setini eval/questions.json olarak hazırlayın; sırayla evaluate.py, experiments.py ve answer_eval.py --judge çalıştırın; çıktılar tezin sonuç tablolarıdır.
5. GitHub'a yüklemek istediğinizde söyleyin; yerel depo (commit a1c87e0, etiket v0.1.0) hazırdır.
