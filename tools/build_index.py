"""FAISS indeksini uygulamayı açmadan kurar veya günceller (OpenAI embedding isteği yapar).

Kullanım (proje kökünden):  python tools/build_index.py
PDF'ler değişmemişse mevcut indeks yüklenir ve yalnızca özet yazdırılır.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import HukukAsistan as ha  # noqa: E402


def main():
    if not ha._pdf_files():
        print(f"'{ha.PDF_DIR}/' klasöründe PDF yok.")
        return 1
    t0 = time.time()
    db = ha.load_or_build_index()
    catalog = ha.law_catalog(db)
    print(f"İndeks hazır ({time.time() - t0:.1f} s): {db.index.ntotal} parça, {len(catalog)} kanun/yönetmelik -> {ha.INDEX_DIR}/")
    for law, info in catalog.items():
        print(f"  - {law} (No. {info['law_no'] or '-'}): {info['madde_count']} madde, {info['chunks']} parça")
    return 0


if __name__ == "__main__":
    sys.exit(main())
