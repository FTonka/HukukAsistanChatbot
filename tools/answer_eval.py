"""Cevap düzeyinde değerlendirme: RAG cevabı ile salt LLM cevabını atıf doğruluğu ve halüsinasyon açısından karşılaştırır.

Her soru için iki cevap üretilir:
  - RAG      : uygulamanın kendisi (HukukAsistan.create_answer, aynı prompt ve indeks)
  - Salt LLM : aynı sohbet modeli, mevzuat alıntısı olmadan ("ilgili kanun ve maddeleri belirt" talimatıyla)
Cevaplardaki madde atıfları ("m. 17", "Madde 17", "17 nci madde") çıkarılır ve şu ölçütler hesaplanır:
  - Atıf doğruluğu : altın madde numaralarından en az biri cevapta atfedilmiş
  - Desteksiz atıf : atfedilen madde, cevapta adı geçen kanunda (geçmiyorsa altın kanunda) indekste yok -> halüsinasyon
  - --judge        : sohbet modeli RAG cevabının alıntılara sadakatini 1-5 puanlar (model tabanlı değerlendirme)

Kullanım (proje kökünden):
  python tools/answer_eval.py eval/questions.json [--limit 20] [--judge]
Çıktı: soru başına satır, özet oranlar ve eval/answers.json. Her soru 2 (judge ile 3) LLM çağrısı yapar.
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import HukukAsistan as ha  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402

# Katlanmış (küçük harf, ı->i) metinde madde atıfları: "m. 17", "md. 17", "madde 17", "17 nci madde", "17. madde"
CITE_RE = re.compile(r"(?:\bm\.|\bmd\.|\bmadde)\s*(\d{1,4})|(\d{1,4})\s*(?:\.|'?\s*(?:inci|nci|uncu|üncü))?\s*madde")

LLM_ONLY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Sen Türk hukuku konusunda bilgi veren bir asistansın. Soruyu Türkçe cevapla ve dayandığın kanun adı "
               "ile madde numaralarını belirt (örnek: \"İş Kanunu m. 17\")."),
    ("human", "{question}"),
])

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Sen titiz bir değerlendiricisin. Önce cevaptaki her sayısal iddiayı (süre, miktar, yaş, oran) "
               "alıntılardaki ilgili hükümle tek tek karşılaştır; kullanıcının durumu bir aralığa düşüyorsa doğru "
               "aralığın seçildiğini kontrol et. Sonra puan ver: cevaptaki her iddia alıntılarla destekleniyorsa 5, "
               "çoğu destekleniyorsa 4, yarısı 3, azı 2, hiçbiri veya alıntıyla çelişen bir iddia varsa 1. "
               "Yalnızca şu biçimde JSON döndür: {{\"sadakat\": <1-5>, \"gerekce\": \"<bir cümle>\"}}"),
    ("human", "Alıntılar:\n{context}\n\nCevap:\n{answer}"),
])


def cited_articles(text):
    return {int(a or b) for a, b in CITE_RE.findall(ha._fold(text))}


def existing_articles(db):
    exist = {}
    for doc in db.docstore._dict.values():
        md = doc.metadata
        if md.get("madde_no"):
            exist.setdefault(md.get("law"), set()).add(md["madde_no"])
    return exist


def score(answer, want_law, want_madde, catalog, exist):
    cited = cited_articles(answer)
    laws = ha.detect_laws(answer, catalog) or [law for law in catalog if want_law and want_law in ha._fold(law)]
    known = set().union(*(exist.get(law, set()) for law in laws)) if laws else set()
    unsupported = sorted(c for c in cited if c not in known)
    return {"cited": sorted(cited), "laws": laws, "gold_cited": bool(cited & want_madde) if want_madde else None,
            "unsupported": unsupported}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("questions", nargs="?", default="eval/questions.json")
    ap.add_argument("--limit", type=int, default=0, help="ilk N soru (maliyeti sınırlamak için)")
    ap.add_argument("--judge", action="store_true", help="RAG cevabı için model tabanlı sadakat puanı")
    ap.add_argument("--out", default="eval/answers.json")
    args = ap.parse_args()

    with open(args.questions, encoding="utf-8") as f:
        items = json.load(f)
    if args.limit:
        items = items[:args.limit]

    db = ha.load_or_build_index()
    catalog = ha.law_catalog(db)
    exist = existing_articles(db)
    llm = ChatOpenAI(model=ha.CHAT_MODEL, temperature=0.2)

    rows = []
    for item in items:
        q, want_law = item["question"], ha._fold(item.get("law", ""))
        want_madde = {int(x) for x in item.get("madde", [])}
        rag_answer, docs, _, rewritten = ha.create_answer(q, [], db=db, catalog=catalog)
        llm_answer = (LLM_ONLY_PROMPT | llm).invoke({"question": q}).content
        row = {"question": q, "gold_law": item.get("law"), "gold_madde": sorted(want_madde), "rewritten": rewritten,
               "rag": {"answer": rag_answer, **score(rag_answer, want_law, want_madde, catalog, exist)},
               "llm": {"answer": llm_answer, **score(llm_answer, want_law, want_madde, catalog, exist)}}
        if args.judge:
            context = "\n\n".join(d.page_content for d in docs)
            verdict = (JUDGE_PROMPT | llm).invoke({"context": context, "answer": rag_answer}).content
            m = re.search(r'"sadakat"\s*:\s*([1-5])', verdict)
            row["rag"]["judge"] = int(m.group(1)) if m else None
            row["rag"]["judge_raw"] = verdict
        rows.append(row)
        fmt = lambda s: f"atıf={'✓' if s['gold_cited'] else '✗'} desteksiz={len(s['unsupported'])}"
        print(f"{q[:58]:<58} RAG: {fmt(row['rag'])}   LLM: {fmt(row['llm'])}"
              + (f"   sadakat={row['rag'].get('judge')}" if args.judge else ""))

    n = len(rows)
    n_gold = sum(1 for r in rows if r["gold_madde"])
    summary = {}
    for side in ("rag", "llm"):
        summary[side] = {
            "gold_cited_rate": (sum(1 for r in rows if r[side]["gold_cited"]) / n_gold) if n_gold else None,
            "hallucination_rate": sum(1 for r in rows if r[side]["unsupported"]) / n,
        }
    if args.judge:
        scores = [r["rag"]["judge"] for r in rows if r["rag"].get("judge")]
        summary["rag"]["judge_mean"] = (sum(scores) / len(scores)) if scores else None
    print("-" * 100)
    for side, label in (("rag", "RAG     "), ("llm", "Salt LLM")):
        s = summary[side]
        gold = "-" if s["gold_cited_rate"] is None else f"{s['gold_cited_rate']:.0%}"
        print(f"{label}: atıf doğruluğu {gold} | desteksiz atıf içeren cevap {s['hallucination_rate']:.0%}"
              + (f" | sadakat ort. {s.get('judge_mean'):.2f}" if s.get("judge_mean") else ""))
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"n": n, "summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"Ayrıntılar: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
