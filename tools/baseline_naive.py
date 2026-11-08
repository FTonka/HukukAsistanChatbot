"""Karşılaştırma tabanı (baseline): her soruda tüm PDF'leri yeniden okuyan, sabit boyutlu parçalama kullanan,
kanun/madde etiketi ve filtre içermeyen basit RAG. Tezdeki karşılaştırmaların başlangıç noktasıdır
(Medicine Hospital projesinin ilk sürümüyle aynı yaklaşım).

Kullanım (proje kökünden):
  python tools/baseline_naive.py "2 yıl çalışan işçinin ihbar süresi ne kadar?"
Çıktı: cevap, kullanılan sayfalar ve adım süreleri (PDF okuma, parçalama, embedding, arama, cevap).
Not: Her çalıştırmada tüm parçalar yeniden embed edilir; süre ve maliyet asıl uygulamayla karşılaştırmak için ölçülür.
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import HukukAsistan as ha  # noqa: E402
from langchain_community.document_loaders import PyPDFLoader  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_core.prompts import ChatPromptTemplate  # noqa: E402
from langchain_openai import ChatOpenAI  # noqa: E402
from langchain.text_splitter import RecursiveCharacterTextSplitter  # noqa: E402

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Aşağıdaki mevzuat alıntılarına dayanarak Türkçe cevap ver; alıntılarda cevap yoksa bunu söyle.\n\n{context}"),
    ("human", "{question}"),
])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    question = " ".join(sys.argv[1:])
    files = ha._pdf_files()
    if not files:
        print(f"'{ha.PDF_DIR}/' klasöründe PDF yok.")
        return 1

    times = {}
    t0 = time.time()
    pages = []
    for path in files:
        pages += PyPDFLoader(path).load()
    times["pdf_okuma"] = time.time() - t0

    t0 = time.time()
    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(pages)
    times["parcalama"] = time.time() - t0

    t0 = time.time()
    db = FAISS.from_documents(chunks, ha._make_embeddings())      # her soruda yeniden: baseline'ın asıl maliyeti
    times["embedding"] = time.time() - t0

    t0 = time.time()
    docs = db.similarity_search(question, k=5)
    times["arama"] = time.time() - t0

    t0 = time.time()
    llm = ChatOpenAI(model=ha.CHAT_MODEL, temperature=0.2)
    answer = (PROMPT | llm).invoke({"context": "\n\n".join(d.page_content for d in docs), "question": question}).content
    times["cevap"] = time.time() - t0

    print(answer)
    pages_used = sorted({f"{os.path.basename(d.metadata.get('source', ''))} s.{int(d.metadata.get('page', 0)) + 1}" for d in docs})
    print("\nKaynak sayfalar:", ", ".join(pages_used))
    print(f"Parça sayısı: {len(chunks)} | Süreler (s): " + ", ".join(f"{k}={v:.1f}" for k, v in times.items())
          + f" | toplam={sum(times.values()):.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
