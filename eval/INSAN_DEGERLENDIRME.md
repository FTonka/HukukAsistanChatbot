# İnsan değerlendirme protokolü

Otomatik ölçütler (Kanun@k, Madde@k, MRR, atıf doğruluğu, desteksiz atıf oranı) geri getirimi ve atıfları ölçer;
cevabın hukuken doğru ve yeterli olup olmadığını insan değerlendirmesi belirler. Bu protokol tezde küçük ölçekli
(30–50 soru) bir çalışma için tasarlanmıştır.

## Katılımcılar

- En az 2 değerlendirici: hukuk fakültesi lisans son sınıf öğrencisi, araştırma görevlisi veya avukat.
- Değerlendiriciler cevabın hangi sistemden (RAG ya da salt LLM) geldiğini görmez (kör değerlendirme).
- Cevaplar karışık sırada sunulur; aynı soru için iki cevap art arda gösterilmez.

## Örneklem

- `eval/questions.json` içinden rastgele 30–50 soru; her kanundan en az 5 soru.
- Her soru için `tools/answer_eval.py` çıktısındaki (`eval/answers.json`) RAG ve salt LLM cevapları.

## Ölçütler (1–5 Likert, 5 en iyi)

| Ölçüt | Soru | 1 | 5 |
|---|---|---|---|
| Doğruluk | Cevap mevzuata göre doğru mu? | Yanlış veya yanıltıcı | Tamamen doğru |
| Atıf doğruluğu | Gösterilen kanun ve maddeler cevabı destekliyor mu? | Atıf yok veya yanlış | Her iddia doğru maddeyle |
| Eksiksizlik | Soruyu cevaplamak için gereken koşul, istisna ve süreler var mı? | Önemli eksikler | Eksiksiz |
| Anlaşılırlık | Hukukçu olmayan biri anlar mı? | Anlaşılmaz | Açık ve düzenli |
| Uyarı uygunluğu | Danışmanlık uyarısı var ama cevabın yerine geçmiyor mu? | Uyarı yok ya da cevabı boğuyor | Dengeli |

İkili ölçüt: **Halüsinasyon** (var/yok): Mevzuatta bulunmayan madde, süre veya hüküm uydurulmuş mu?

## Uygulama

1. Değerlendirme formu: `eval/insan_degerlendirme_sablon.csv` sütunları `soru_id, cevap_id, dogruluk, atif, eksiksizlik, anlasilirlik, uyari, halusinasyon, not`.
2. Her değerlendirici formu bağımsız doldurur; süre sınırı yoktur, mevzuat metnine bakabilir.
3. Değerlendiriciler arası uyum: Likert ölçütleri için ağırlıklı Cohen kappa (2 kişi) veya Krippendorff alfa (3+ kişi); halüsinasyon için Cohen kappa.
4. Raporlama: ölçüt başına ortalama ve standart sapma, RAG ile salt LLM farkı için Wilcoxon işaretli sıra testi.
5. Uyumsuzluk 2 puan ve üzerindeki örnekler birlikte tartışılır; nedenler hata analizine (yanlış kanun, mülga madde, eksik koşul) işlenir.

## Etik not

Sorular gerçek kişilere ait bilgi içermez; kamuya açık SSS ve karar özetlerinden türetilir. Değerlendiricilere
cevapların hukuki tavsiye olmadığı ve çalışmanın amacı açıklanır.
