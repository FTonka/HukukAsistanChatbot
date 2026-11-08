"""Madde düzeyinde geri getirim değerlendirmesi (LLM çağrısı yapmaz; yalnızca embedding sorgusu).

Soru dosyası (JSON listesi), örnek: eval/questions.example.json
  [{"question": "2 yıl çalışan işçinin ihbar süresi ne kadar?", "law": "İŞ KANUNU", "madde": [17]}, ...]
  - "law": doğru kanun adının bir parçası (büyük/küçük harf önemsiz)
  - "madde": doğru madde numaraları; boş bırakılırsa o soru için yalnızca kanun isabeti ölçülür

Kullanım (proje kökünden):
  python tools/evaluate.py eval/questions.json --k 5

Ölçütler: Kanun@k (doğru kanundan en az bir parça ilk k içinde), Madde@k (doğru madde ilk k içinde),
MRR (doğru maddenin sırasının tersi, ortalama). Ayrıntılar eval/results.json dosyasına yazılır.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import HukukAsistan as ha  # noqa: E402


def retrieve(db, catalog, question, k):
    """Uygulamadaki MevzuatRetriever ile aynı mantık; k dışarıdan verilir."""
    laws = ha.detect_laws(question, catalog)
    if laws:
        wanted = set(laws)
        docs = db.similarity_search(question, k=k, fetch_k=db.index.ntotal, filter=lambda md: md.get("law") in wanted)
    else:
        docs = db.similarity_search(question, k=k)
    return laws, docs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("questions", nargs="?", default="eval/questions.json", help="soru dosyası (JSON)")
    ap.add_argument("--k", type=int, default=5, help="değerlendirilen parça sayısı")
    ap.add_argument("--out", default="eval/results.json", help="ayrıntılı sonuç dosyası")
    args = ap.parse_args()

    if not os.path.exists(args.questions):
        print(f"Soru dosyası yok: {args.questions}\n"
              "eval/questions.example.json dosyasını kopyalayıp kendi mevzuatınıza göre düzenleyin.")
        return 1
    with open(args.questions, encoding="utf-8") as f:
        items = json.load(f)

    db = ha.load_or_build_index()
    catalog = ha.law_catalog(db)

    rows, law_hits, madde_hits, rr_sum, n_madde = [], 0, 0, 0.0, 0
    for item in items:
        laws, docs = retrieve(db, catalog, item["question"], args.k)
        want_law = ha._fold(item.get("law", ""))
        want_madde = {int(x) for x in item.get("madde", [])}
        law_rank = madde_rank = None
        for rank, doc in enumerate(docs, 1):
            md = doc.metadata
            law_ok = bool(want_law) and want_law in ha._fold(md.get("law", ""))
            if law_ok and law_rank is None:
                law_rank = rank
            if law_ok and md.get("madde_no") in want_madde and madde_rank is None:
                madde_rank = rank
        law_hits += law_rank is not None
        if want_madde:
            n_madde += 1
            madde_hits += madde_rank is not None
            rr_sum += 1 / madde_rank if madde_rank else 0.0
        rows.append({
            "question": item["question"], "law": item.get("law"), "madde": sorted(want_madde),
            "filter": laws, "law_rank": law_rank, "madde_rank": madde_rank,
            "retrieved": [f"{d.metadata.get('law')} | {d.metadata.get('madde')} | s.{int(d.metadata.get('page', 0)) + 1}" for d in docs],
        })
        mark = "✓" if (madde_rank if want_madde else law_rank) else "✗"
        print(f"{mark} {item['question'][:62]:<62} kanun@{args.k}: {law_rank or '-':<3} "
              f"madde@{args.k}: {madde_rank or '-':<3} filtre: {', '.join(laws) or '—'}")

    n = len(items)
    print("-" * 100)
    print(f"Soru sayısı: {n}   Kanun@{args.k}: {law_hits / n:.0%}" +
          (f"   Madde@{args.k}: {madde_hits / n_madde:.0%}   MRR: {rr_sum / n_madde:.2f}" if n_madde else ""))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"k": args.k, "n": n, "law_at_k": law_hits / n,
                   "madde_at_k": (madde_hits / n_madde) if n_madde else None,
                   "mrr": (rr_sum / n_madde) if n_madde else None, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"Ayrıntılar: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
