"""Geri getirim ablasyon deneyleri (LLM çağrısı yok; yalnızca embedding sorgusu).

Karşılaştırılanlar:
  - parçalama : madde (yapısal, "[KANUN | Madde N]" bağlam etiketli)  vs  fixed (sabit boyut 1000/200, etiketsiz)
  - filtre    : on (soruda kanun algılanırsa arama o kanunla sınırlı)   vs  off (tüm mevzuat)
  - embedding : --embeddings ile virgülle ayrılmış model listesi (her model için ayrı indeks kurulur)
  - k         : --k ile virgülle ayrılmış liste

Kullanım (proje kökünden):
  python tools/experiments.py eval/questions.json --k 1,3,5,10 --embeddings text-embedding-3-small
Çıktı: eval/experiments.md (markdown tablo) ve eval/experiments.json. İndeksler eval/indexes/ altında saklanır
ve PDF'ler değişmediği sürece yeniden kurulmaz.
"""
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import HukukAsistan as ha  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_openai import OpenAIEmbeddings  # noqa: E402
from langchain.text_splitter import RecursiveCharacterTextSplitter  # noqa: E402

INDEX_ROOT = os.getenv("HUKUK_EXP_INDEX_DIR", os.path.join("eval", "indexes"))


def madde_chunks(pages):
    chunks = ha.build_chunks(pages)
    for c in chunks:
        c.metadata["madde_nos"] = [c.metadata["madde_no"]] if c.metadata.get("madde_no") else []
    return chunks


def fixed_chunks(pages):
    """Sabit boyutlu parçalama. Madde bilgisi yalnızca puanlama için sonradan çıkarılır: parçanın içinde
    başlayan maddeler ve parçanın başında devam eden önceki madde (madde_nos)."""
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(pages)
    current = {}
    for c in chunks:
        law = c.metadata["law"]
        nos = [current.get(law, 0)] + [int(m.group(3)) for m in ha.ARTICLE_RE.finditer(c.page_content)]
        current[law] = nos[-1]
        c.metadata["madde_nos"] = sorted({n for n in nos if n})
    return chunks


def get_index(chunking, model, pages):
    path = os.path.join(INDEX_ROOT, f"{chunking}__{model}")
    emb = OpenAIEmbeddings(model=model, chunk_size=200)
    sig = {"version": 1, "chunking": chunking, "model": model, "files": ha._index_signature()["files"]}
    sig_path = os.path.join(path, "signature.json")
    if os.path.exists(sig_path):
        with open(sig_path, encoding="utf-8") as f:
            if json.load(f) == sig:
                return FAISS.load_local(path, emb, allow_dangerous_deserialization=True)
    chunks = (madde_chunks if chunking == "madde" else fixed_chunks)(pages)
    print(f"  indeks kuruluyor: {chunking} / {model} ({len(chunks)} parça)")
    db = FAISS.from_documents(chunks, emb)
    os.makedirs(path, exist_ok=True)
    db.save_local(path)
    with open(sig_path, "w", encoding="utf-8") as f:
        json.dump(sig, f)
    return db


def ranks(docs, want_law, want_madde):
    law_rank = madde_rank = None
    for rank, d in enumerate(docs, 1):
        md = d.metadata
        law_ok = bool(want_law) and want_law in ha._fold(md.get("law", ""))
        if law_ok and law_rank is None:
            law_rank = rank
        if law_ok and want_madde & set(md.get("madde_nos", [])) and madde_rank is None:
            madde_rank = rank
    return law_rank, madde_rank


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("questions", nargs="?", default="eval/questions.json")
    ap.add_argument("--k", default="1,3,5,10")
    ap.add_argument("--embeddings", default=ha.EMBEDDING_MODEL)
    ap.add_argument("--chunking", default="madde,fixed")
    ap.add_argument("--out", default="eval/experiments")
    args = ap.parse_args()

    with open(args.questions, encoding="utf-8") as f:
        items = json.load(f)
    ks = [int(k) for k in args.k.split(",")]
    kmax = max(ks)
    pages = ha.load_pages()

    results = []
    for model in args.embeddings.split(","):
        for chunking in args.chunking.split(","):
            db = get_index(chunking, model.strip(), pages)
            catalog = ha.law_catalog(db)
            for use_filter in (True, False):
                per_k = {k: {"law": 0, "madde": 0, "rr": 0.0} for k in ks}
                n_madde = 0
                for item in items:
                    laws = ha.detect_laws(item["question"], catalog) if use_filter else []
                    if laws:
                        wanted = set(laws)
                        docs = db.similarity_search(item["question"], k=kmax, fetch_k=db.index.ntotal,
                                                    filter=lambda md: md.get("law") in wanted)
                    else:
                        docs = db.similarity_search(item["question"], k=kmax)
                    want_madde = {int(x) for x in item.get("madde", [])}
                    law_rank, madde_rank = ranks(docs, ha._fold(item.get("law", "")), want_madde)
                    n_madde += bool(want_madde)
                    for k in ks:
                        per_k[k]["law"] += bool(law_rank and law_rank <= k)
                        if want_madde:
                            per_k[k]["madde"] += bool(madde_rank and madde_rank <= k)
                            per_k[k]["rr"] += (1 / madde_rank) if (madde_rank and madde_rank <= k) else 0.0
                for k in ks:
                    results.append({
                        "chunking": chunking, "filter": "on" if use_filter else "off", "embedding": model.strip(),
                        "k": k, "chunks": db.index.ntotal,
                        "law_at_k": per_k[k]["law"] / len(items),
                        "madde_at_k": (per_k[k]["madde"] / n_madde) if n_madde else None,
                        "mrr": (per_k[k]["rr"] / n_madde) if n_madde else None,
                    })

    header = "| Parçalama | Filtre | Embedding | k | Parça | Kanun@k | Madde@k | MRR@k |\n|---|---|---|---|---|---|---|---|"
    lines = [header]
    for r in results:
        pct = lambda v: "-" if v is None else f"{v:.0%}"
        mrr = "-" if r["mrr"] is None else f"{r['mrr']:.2f}"
        lines.append(f"| {r['chunking']} | {r['filter']} | {r['embedding']} | {r['k']} | {r['chunks']} | "
                     f"{pct(r['law_at_k'])} | {pct(r['madde_at_k'])} | {mrr} |")
    table = "\n".join(lines)
    print(table)
    with open(args.out + ".md", "w", encoding="utf-8") as f:
        f.write(f"# Geri getirim deneyleri\n\nSoru dosyası: {args.questions} ({len(items)} soru)\n\n{table}\n")
    with open(args.out + ".json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nKaydedildi: {args.out}.md, {args.out}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
