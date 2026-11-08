"""PDF klasöründeki mevzuatın nasıl etiketlendiğini gösterir; indeks kurmaz, OpenAI'ye istek göndermez.

Kullanım (proje kökünden):  python tools/inspect_pdf.py
Çıktı: her kanun/yönetmelik için numara, sayfa aralığı, madde sayısı ve mülga madde sayısı.
       "Bilinmiyor" satırı varsa o sayfalarda kanun başlığı algılanamamıştır (bkz. README > Ayarlar).
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import HukukAsistan as ha  # noqa: E402


def main():
    files = ha._pdf_files()
    if not files:
        print(f"'{ha.PDF_DIR}/' klasöründe PDF yok. mevzuat.gov.tr'den indirdiğiniz PDF'leri bu klasöre koyun.")
        return 1
    print("Dosyalar:", ", ".join(os.path.basename(f) for f in files))
    pages = ha.load_pages()
    segments = ha._segment_articles(pages)

    stats = {}
    for p in pages:
        s = stats.setdefault(p.metadata["law"], {"no": p.metadata["law_no"], "pages": [], "madde": set(), "mulga": set()})
        s["pages"].append(p.metadata["page"] + 1)
    for seg in segments:
        s = stats[seg.metadata["law"]]
        if seg.metadata["madde_no"]:
            s["madde"].add(seg.metadata["madde"])
            if seg.metadata["mulga"]:
                s["mulga"].add(seg.metadata["madde"])

    print(f"\n{'Kanun / Yönetmelik':<58} {'No':>6} {'Sayfa':>11} {'Madde':>6} {'Mülga':>6}")
    print("-" * 92)
    for law, s in stats.items():
        pg = f"{min(s['pages'])}-{max(s['pages'])}" if s["pages"] else "-"
        print(f"{law[:58]:<58} {s['no'] or '-':>6} {pg:>11} {len(s['madde']):>6} {len(s['mulga']):>6}")
    chunks = ha.build_chunks(pages)
    print("-" * 92)
    print(f"Toplam: {len(pages)} sayfa, {sum(len(s['madde']) for s in stats.values())} madde, "
          f"{len(chunks)} parça (indeks boyutu)")
    if ha.UNKNOWN_LAW in stats:
        print(f"\nUYARI: {len(stats[ha.UNKNOWN_LAW]['pages'])} sayfada kanun başlığı algılanamadı ('{ha.UNKNOWN_LAW}'). "
              "Bu sayfalar aramaya girer ama kanun filtresi ve kaynak gösterimi eksik kalır.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
