"""Hukuk Asistanı: kanun ve yönetmelik PDF'lerine dayalı Türkçe soru-cevap asistanı (RAG).

Akış: PDF sayfaları -> kanun etiketi (sayfa başlığından) -> madde sınırlarından bölme -> FAISS indeksi (diskte)
      -> soru: kanun tespiti + filtreli vektör arama -> sohbet modeliyle kaynak gösteren cevap.
"""
import os
import re
import glob
import json
import logging
from typing import Any, Dict, List

import streamlit as st
from dotenv import load_dotenv
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS

load_dotenv()  # OPENAI_API_KEY .env dosyasından okunur
logging.getLogger("pypdf").setLevel(logging.ERROR)  # "fontTools is required" gibi zararsız uyarıları gizler

# --------------------------------------------------------------------------- ayarlar
PDF_DIR = os.getenv("HUKUK_PDF_DIR", "PDFs")             # klasördeki tüm PDF'ler okunur: tek birleştirilmiş dosya ya da kanun başına bir dosya
INDEX_DIR = os.getenv("HUKUK_INDEX_DIR", "vectorstore")  # FAISS indeksi ve imza dosyası burada saklanır
INDEX_VERSION = 2                # parçalama/etiketleme mantığı değişince artırın; indeks yeniden kurulur
CHUNK_SIZE = 600                 # uzun maddeler bu uzunlukta (karakter) parçalanır; gerçek veri deneyinde 1200'den iyi çıktı
CHUNK_OVERLAP = 80
TOP_K = 8                        # soruda kanun geçiyorsa o kanundan alınan parça sayısı
GENERAL_K = 10                   # kanun geçmiyorsa (durum soruları) tüm mevzuattan alınan parça sayısı
EMBEDDING_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"
UNKNOWN_LAW = "Bilinmiyor"
MAX_HISTORY_TURNS = 6            # modele gönderilen en fazla soru-cevap çifti
QUERY_REWRITE = True             # günlük dildeki soruyu kanun terimlerine çeviren ikinci arama sorgusu (1 kısa LLM çağrısı)
RRF_K = 60                       # Reciprocal Rank Fusion sabiti (iki sorgunun sonuç listeleri birleştirilirken)

EXAMPLE_QUESTIONS = [
    "İşten çıkarıldım, kıdem ve ihbar tazminatı alabilir miyim?",
    "Ev sahibi kira sözleşmesini hangi şartlarda feshedebilir?",
    "Aldığım ürün ayıplı çıktı, hangi haklarım var?",
    "KVKK'ya göre kişisel verilerimin silinmesini isteyebilir miyim?",
]

# Sık kullanılan kısaltma ve kısa adlar -> kanun adında aranacak ifade (ikisi de _fold ile karşılaştırılır).
LAW_ALIASES = {
    "kvkk": "kişisel verilerin korunması",
    "tbk": "borçlar kanunu",
    "tmk": "medeni kanun",
    "tck": "ceza kanunu",
    "tkhk": "tüketicinin korunması",
    "hmk": "hukuk muhakemeleri",
    "iik": "icra ve iflas",
    "ttk": "ticaret kanunu",
    "sgk": "sosyal sigortalar",
    "anayasa": "anayasa",
    "iş hukuku": "iş kanunu",
    "tüketici kanunu": "tüketicinin korunması",
    "kira kanunu": "borçlar kanunu",
}

QA_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Sen Türk mevzuatına dayalı bir hukuk bilgi asistanısın. Yalnızca aşağıdaki kanun ve yönetmelik "
     "alıntılarına dayanarak Türkçe, anlaşılır ve tarafsız cevap ver; uygunsa kısa maddeler kullan. "
     "Her hukuki ifadeyi dayandığı kanun adı ve madde numarasıyla belirt (örnek: \"İş Kanunu m. 17\"). "
     "Alıntılarda cevap yoksa bunu açıkça söyle; madde numarası veya hüküm uydurma. "
     "Alıntı \"(Mülga\" ile başlıyorsa hükmün yürürlükten kaldırıldığını belirt.\n\n"
     "Kullanıcı somut bir durum anlatıp haklarını veya ne yapabileceğini sorarsa: alıntılardaki hükümlere göre "
     "uygulanabilecek kanun ve maddeleri somut olarak say; her biri için hükmün koşullarını, istisnalarını, "
     "varsa süre ve miktar bilgisini bir iki cümleyle açıkla; kullanıcının verdiği bilgileri (çalışma süresi, "
     "sözleşme türü, tarih gibi) hesaba kat. Süre, yaş, miktar gibi eşiklere bağlı hükümlerde önce hükümdeki "
     "tüm aralıkları alıntıdan aynen listele, sonra kullanıcının verdiği değerin hangi aralığa girdiğini adım adım "
     "belirle ve yalnızca o aralığın sonucunu yaz (örnek: 2 yıl çalışma, 'birbuçuk yıldan üç yıla kadar' aralığına "
     "girer). Sonunda kesin değerlendirme için bir avukata ya da baroların adli "
     "yardım bürosuna danışılmasını kısaca hatırlat; bu hatırlatma cevabın yerine geçmesin.\n\n"
     "Mevzuat alıntıları:\n{context}"),
    ("human", "{question}"),
])

# Günlük dil ile kanun dili arasındaki boşluk geri getirimi düşürür: kullanıcı "ihbar süresi" der, İş Kanunu m. 17
# "bildirim süresi" yazar. Soru, mevzuat terimleriyle kısa bir arama sorgusuna çevrilir; özgün soru ve çeviri ayrı ayrı
# aranır, iki liste RRF ile birleştirilir (bkz. search_documents).
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Günlük dille yazılmış hukuki soruyu, Türk mevzuatında geçen resmi terimlerle tek satırlık kısa bir arama "
     "sorgusuna çevir (en fazla 25 kelime; madde numarası yazma; açıklama ekleme). Günlük ifadeleri kanun diline "
     "aktar, örnekler: ihbar süresi -> bildirim süresi; işten çıkarıldım -> iş sözleşmesinin işveren tarafından "
     "feshi; ev sahibi -> kiraya veren; ürün bozuk çıktı -> ayıplı mal, tüketicinin seçimlik hakları; verilerimin "
     "silinmesi -> kişisel verilerin silinmesi, ilgili kişinin hakları. Sorunun konusunu ve ilgili olabilecek "
     "hukuki kavramları da ekle."),
    ("human", "{question}"),
])


def rewrite_query(question, llm=None):
    """Soruyu kanun diline çevrilmiş tek satırlık arama sorgusuna dönüştürür."""
    llm = llm or ChatOpenAI(model=CHAT_MODEL, temperature=0)
    text = (REWRITE_PROMPT | llm).invoke({"question": question}).content.strip()
    return text.splitlines()[0].strip().strip('"') if text else ""

# --------------------------------------------------------------------------- PDF -> kanun ve madde etiketi
# mevzuat.gov.tr PDF'lerinde her kanun büyük harfli başlıkla başlar ("İŞ KANUNU"), hemen altında
# "Kanun Numarası : 4857", "Kabul Tarihi", "Yayımlandığı Resmî Gazete" satırları gelir. Yönetmeliklerde
# "Resmî Gazete Tarihi/Sayısı" satırı ve "... YÖNETMELİĞİ" başlığı bulunur. Başlık yalnızca bu künye
# satırlarından biriyle aynı sayfada görülürse kabul edilir; böylece metin içi büyük harfli atıflar eşleşmez.
TITLE_RE = re.compile(
    r"((?:[A-ZÇĞİÖŞÜ0-9][A-ZÇĞİÖŞÜ0-9'’.,()\-]*\s+){0,14}"
    r"(?:KANUN HÜKMÜNDE KARARNAME|CUMHURBAŞKANLIĞI KARARNAMESİ|KARARNAMESİ|ANAYASASI|KANUNU|KANUN|"
    r"YÖNETMELİĞİ|YÖNETMELİK|TÜZÜĞÜ|TÜZÜK|TEBLİĞİ|TEBLİĞ))(?![A-ZÇĞİÖŞÜa-zçğıöşü])"
)
META_RE = re.compile(r"Kanun\s+Numaras[ıi]|Kabul\s+Tarihi|Resm[îi]\s+Gazete|Yay[ıi]mland[ıi]ğ[ıi]|Karar\s+Say[ıi]s[ıi]", re.I)
LAW_NO_RE = re.compile(r"Kanun\s+Numaras[ıi]\s*:?\s*(\d+)", re.I)

# Madde başlıkları: "Madde 17 –", "MADDE 1-", "Ek Madde 2 –", "Geçici Madde 6 –". Metin içi "17 nci maddesi"
# gibi atıflar küçük harfli olduğu ve tire içermediği için eşleşmez.
ARTICLE_RE = re.compile(r"(?<!\w)((?:EK|Ek|GEÇİCİ|Geçici|MÜLGA|Mülga)\s+)?(MADDE|Madde)\s+(\d+)\s*[-–—]")
PREFIX_MAP = {"ek": "Ek", "geçici": "Geçici", "mülga": "Mülga"}

# Kanun adından ayırt edici çekirdek üretirken atılan genel sözcükler (_fold biçiminde).
GENERIC_WORDS = {"kanunu", "kanun", "hakkinda", "türk", "türkiye", "cumhuriyeti", "ve", "ile", "dair", "ilişkin",
                 "bazi", "hükmünde", "kararname", "kararnamesi", "yönetmeliği", "yönetmelik", "tüzüğü", "tüzük",
                 "tebliği", "tebliğ", "sayili"}


def _fold(text):
    """Türkçe'ye uygun küçük harf; i/ı/İ/I farklarını tek biçime indirger."""
    return text.replace("İ", "i").replace("I", "i").lower().replace("ı", "i")


def _law_from_header(text):
    """Sayfa başındaki künyeden (kanun adı, kanun numarası) döndürür; bu sayfa bir kanunun ilk sayfası değilse (None, '')."""
    head = re.sub(r"\s+", " ", text[:1500])
    if not META_RE.search(head):
        return None, ""
    m = TITLE_RE.search(head)
    if not m:
        return None, ""
    tokens = m.group(1).split()
    while tokens and not re.search(r"[A-ZÇĞİÖŞÜ]", tokens[0]):   # Düstur sayfa numarası gibi öndeki sayıları at
        tokens.pop(0)
    title = " ".join(tokens)
    if not 5 <= len(title) <= 160:
        return None, ""
    no = LAW_NO_RE.search(head)
    return title, (no.group(1) if no else "")


def _pdf_files():
    files = {p for pattern in ("*.pdf", "*.PDF") for p in glob.glob(os.path.join(PDF_DIR, pattern))}
    return sorted(files)


def load_pages():
    """PDF klasöründeki tüm dosyaları sayfa sayfa okur; her sayfaya metadata['law'] ve ['law_no'] yazar."""
    files = _pdf_files()
    pages, seen_no = [], {}
    for path in files:
        docs = PyPDFLoader(path).load()
        stem = os.path.splitext(os.path.basename(path))[0].replace("_", " ").replace("-", " ").strip()
        # Kanun başına bir dosya kullanılıyorsa başlık bulunamayan dosyada dosya adı kanun adı olur.
        current, current_no = (stem if len(files) > 1 else UNKNOWN_LAW), ""
        for doc in docs:
            title, no = _law_from_header(doc.page_content)
            if title:
                if title in seen_no and no and seen_no[title] != no:
                    title = f"{title} ({no})"          # aynı adlı iki kanun (ör. 1475 ve 4857 sayılı İş Kanunu)
                else:
                    seen_no.setdefault(title, no)
                current, current_no = title, no
            doc.metadata.update({"law": current, "law_no": current_no, "source": os.path.basename(path)})
            pages.append(doc)
    return pages


def _segment(doc, text, article):
    label, no, baslik, mulga = article
    return Document(page_content=text,
                    metadata={**doc.metadata, "madde": label, "madde_no": no, "baslik": baslik, "mulga": mulga})


def _segment_articles(pages):
    """Sayfa metinlerini madde sınırlarından böler. Her parça kanun, madde etiketi ("Madde 17"), madde başlığı
    ("Süreli fesih") ve mülga bilgisini taşır; sayfa sonunda biten madde sonraki sayfada devam eder."""
    segments, current_by_law = [], {}
    for doc in pages:
        text, law = doc.page_content, doc.metadata["law"]
        current = current_by_law.get(law, ("Giriş", 0, "", False))
        cuts = []
        for m in ARTICLE_RE.finditer(text):
            start, baslik = m.start(), ""
            before = text[:start].rstrip()
            line_start = before.rfind("\n") + 1
            prev = before[line_start:].strip()
            # Mevzuatta madde başlığı ("Süreli fesih") madde satırının hemen üstündeki kısa satırdır.
            if prev and len(prev) <= 90 and prev[-1] not in ".;:," and not prev[0].isdigit() \
                    and prev[0] != "(" and not ARTICLE_RE.search(prev):
                baslik, start = prev, line_start
            prefix = PREFIX_MAP.get(_fold(m.group(1) or "").strip(), "")
            no = int(m.group(3))
            mulga = bool(re.match(r"\s*\(?\s*Mülga", text[m.end():m.end() + 40]))
            cuts.append((start, (f"{prefix} Madde {no}".strip(), no, baslik, mulga)))
        pos = 0
        for start, article in cuts:
            start = max(start, pos)
            if start > pos:                       # önceki maddenin devamı
                segments.append(_segment(doc, text[pos:start], current))
            current, pos = article, start
        segments.append(_segment(doc, text[pos:], current))
        current_by_law[law] = current
    return [s for s in segments if s.page_content.strip()]


def build_chunks(pages=None, chunk_size=None, chunk_overlap=None):
    """Sayfaları madde parçalarına böler, uzun maddeleri CHUNK_SIZE'a göre ayırır ve her parçanın başına
    "[KANUN | Madde N | Başlık]" bağlam etiketi ekler (embedding bu etiketi de görür).
    chunk_size / chunk_overlap verilirse varsayılanların yerine geçer (deney betikleri için)."""
    segments = _segment_articles(pages if pages is not None else load_pages())
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size or CHUNK_SIZE,
                                              chunk_overlap=CHUNK_OVERLAP if chunk_overlap is None else chunk_overlap)
    chunks = splitter.split_documents(segments)
    for chunk in chunks:
        md = chunk.metadata
        header = f"[{md['law']} | {md['madde']}" + (f" | {md['baslik']}" if md.get("baslik") else "") + "]"
        chunk.page_content = header + "\n" + chunk.page_content.strip()
    return chunks


# --------------------------------------------------------------------------- indeks
def _index_signature():
    files = [{"name": os.path.basename(p), "size": os.path.getsize(p), "mtime": int(os.path.getmtime(p))}
             for p in _pdf_files()]
    return {
        "version": INDEX_VERSION,
        "files": files,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
    }


def _make_embeddings():
    # chunk_size burada istek başına gönderilen parça sayısıdır; OpenAI'nin 300k token/istek sınırı için düşük tutulur.
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, chunk_size=200)


def build_index(embeddings):
    """PDF'leri okur, kanun ve madde etiketleriyle parçalar, embed eder ve diske kaydeder (tek seferlik)."""
    chunks = build_chunks()
    if not chunks:
        raise RuntimeError(f"'{PDF_DIR}/' klasöründeki PDF'lerden metin çıkarılamadı (taranmış görüntü olabilir).")
    db = FAISS.from_documents(chunks, embeddings)
    os.makedirs(INDEX_DIR, exist_ok=True)
    db.save_local(INDEX_DIR)
    with open(os.path.join(INDEX_DIR, "signature.json"), "w", encoding="utf-8") as f:
        json.dump(_index_signature(), f)
    return db


def load_or_build_index(embeddings=None):
    """İndeks diskte varsa ve PDF'ler değişmemişse yükler; yoksa bir kez kurar."""
    embeddings = embeddings or _make_embeddings()
    sig_path = os.path.join(INDEX_DIR, "signature.json")
    if os.path.exists(sig_path):
        with open(sig_path, encoding="utf-8") as f:
            if json.load(f) == _index_signature():
                # Dosyalar bu uygulama tarafından yazıldığı için pickle yüklemesi güvenlidir.
                return FAISS.load_local(INDEX_DIR, embeddings, allow_dangerous_deserialization=True)
    return build_index(embeddings)


@st.cache_resource(show_spinner="Mevzuat indeksi hazırlanıyor (yalnızca ilk çalıştırmada, birkaç dakika sürebilir)...")
def get_vectorstore():
    return load_or_build_index()


def law_catalog(db) -> Dict[str, dict]:
    """Kanun adı -> {'law_no', 'madde_count', 'chunks'} (indeksteki parçaların metadata'sından)."""
    catalog = {}
    for doc in db.docstore._dict.values():
        md = doc.metadata
        law = md.get("law", UNKNOWN_LAW)
        if law == UNKNOWN_LAW:
            continue
        entry = catalog.setdefault(law, {"law_no": md.get("law_no", ""), "maddeler": set(), "chunks": 0})
        entry["chunks"] += 1
        if md.get("madde_no"):
            entry["maddeler"].add(md["madde"])
    return {law: {"law_no": e["law_no"], "madde_count": len(e["maddeler"]), "chunks": e["chunks"]}
            for law, e in sorted(catalog.items())}


@st.cache_resource
def get_law_catalog():
    return law_catalog(get_vectorstore())


# --------------------------------------------------------------------------- arama
# Somut durum soruları ("haklarım neler?", "hangi kanun?"): kanun adı geçmese de takip sorusu sayılmaz, tüm mevzuatta aranır.
SITUATION_RE = re.compile(r"hangi kanun|hangi madde|hangi mevzuat|hakkim|haklarim|ne yapabilir|ne yapmali|yasal mi|hukuki mi|dava aç|suç mu")
LAW_NO_IN_TEXT_RE = re.compile(r"(?<!\d)(\d{3,5})\s*sayili")


def is_situation_question(text):
    return bool(SITUATION_RE.search(_fold(text)))


def _law_keys(name):
    """Bir kanun adı için soruda aranacak anahtarlar: tam ad, 'türk' öneksiz ad ve en az iki sözcüklü ayırt edici çekirdek."""
    folded = re.sub(r"\s+", " ", _fold(re.sub(r"\(.*?\)", " ", name))).strip()
    keys = {folded}
    if folded.startswith("türk "):
        keys.add(folded[5:])
    core = [w for w in folded.split() if w not in GENERIC_WORDS]
    if len(core) >= 2 and " ".join(core) in folded:      # çekirdek adın içinde ardışık geçiyorsa
        keys.add(" ".join(core))
    return keys


def _mentions(folded_text, key):
    # Yalnızca sol sınır aranır; böylece "iş kanununa", "kvkk'ya" gibi ekli biçimler de eşleşir.
    return re.search(r"(?<![a-zçğöşü0-9])" + re.escape(key), folded_text) is not None


def detect_laws(text, catalog):
    """Metinde adı, kısaltması ("KVKK") veya numarası ("4857 sayılı") geçen kanunları döndürür."""
    folded = _fold(text)
    found = set()
    for law in catalog:
        if any(_mentions(folded, key) for key in _law_keys(law)):
            found.add(law)
    for alias, target in LAW_ALIASES.items():
        if _mentions(folded, _fold(alias)):
            found.update(law for law in catalog if _fold(target) in _fold(law))
    for no in LAW_NO_IN_TEXT_RE.findall(folded):
        found.update(law for law, info in catalog.items() if info.get("law_no") == no)
    return sorted(found)


def _similarity(db, query, k, laws):
    if laws:
        wanted = set(laws)
        # fetch_k tüm indeks olduğu için filtre sonrası k parça garanti edilir (düz indeks, maliyet düşük).
        return db.similarity_search(query, k=k, fetch_k=db.index.ntotal, filter=lambda md: md.get("law") in wanted)
    return db.similarity_search(query, k=k)


def _doc_key(doc):
    md = doc.metadata
    return (md.get("law"), md.get("madde"), md.get("page"), doc.page_content[:80])


def rrf_merge(result_lists, k, c=RRF_K):
    """Reciprocal Rank Fusion: birden fazla sıralı sonuç listesini tek listede birleştirir (puan = toplam 1/(c+sıra))."""
    scores, docs = {}, {}
    for results in result_lists:
        for rank, doc in enumerate(results, 1):
            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + 1.0 / (c + rank)
            docs.setdefault(key, doc)
    return [docs[key] for key, _ in sorted(scores.items(), key=lambda kv: -kv[1])[:k]]


def search_documents(db, query, k, laws=(), rewritten=None):
    """Özgün soruyla (ve verildiyse kanun diline çevrilmiş sorguyla) arar; iki listeyi RRF ile birleştirir.
    laws boş değilse arama o kanunlarla sınırlıdır. Değerlendirme betikleri de bu fonksiyonu kullanır."""
    if rewritten and _fold(rewritten) != _fold(query):
        return rrf_merge([_similarity(db, query, k, laws), _similarity(db, rewritten, k, laws)], k)
    return _similarity(db, query, k, laws)


class MevzuatRetriever(BaseRetriever):
    """Kanun verildiyse yalnızca o kanunların parçalarında arar; verilmediyse tüm mevzuatta arar.
    rewrite açıksa soru kanun diline de çevrilir ve iki sorgunun sonuçları birleştirilir."""

    vectorstore: Any
    laws: List[str] = []
    rewrite: bool = QUERY_REWRITE
    llm: Any = None
    last_rewrite: str = ""

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        rewritten = ""
        if self.rewrite:
            try:
                rewritten = rewrite_query(query, self.llm)
            except Exception:
                rewritten = ""          # çeviri başarısızsa yalnızca özgün soruyla aranır
        self.last_rewrite = rewritten
        return search_documents(self.vectorstore, query, TOP_K if self.laws else GENERAL_K, self.laws, rewritten)


def create_answer(question, chat_history, db=None, catalog=None):
    """Soruyu cevaplar. Dönüş: (cevap, kaynak parçalar, filtrelenen kanunlar, kanun diline çevrilmiş sorgu).
    db/catalog verilmezse Streamlit önbelleğindeki indeks kullanılır (değerlendirme betikleri kendi indeksini verir)."""
    db = db if db is not None else get_vectorstore()
    catalog = catalog if catalog is not None else get_law_catalog()

    laws = detect_laws(question, catalog)
    if not laws and not is_situation_question(question):   # takip sorusu: sohbette en son geçen kanun
        for past_q, past_a in reversed(chat_history):
            laws = detect_laws(past_q, catalog) or detect_laws(past_a, catalog)
            if laws:
                break

    llm = ChatOpenAI(model=CHAT_MODEL, temperature=0.2)
    retriever = MevzuatRetriever(vectorstore=db, laws=laws, llm=ChatOpenAI(model=CHAT_MODEL, temperature=0))
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
        combine_docs_chain_kwargs={"prompt": QA_PROMPT},
    )
    result = chain.invoke({"question": question, "chat_history": chat_history[-MAX_HISTORY_TURNS:]})
    return result["answer"], result.get("source_documents", []), laws, retriever.last_rewrite


def format_sources(docs):
    """Kaynakları kanun bazında toplar: 'İŞ KANUNU · Madde 17, Madde 18 · s. 12, 13'."""
    by_law = {}
    for doc in docs:
        md = doc.metadata
        entry = by_law.setdefault(md.get("law", UNKNOWN_LAW), {"maddeler": {}, "pages": set()})
        entry["maddeler"][md.get("madde", "Giriş")] = md.get("madde_no", 0)
        entry["pages"].add(int(md.get("page", 0)) + 1)
    lines = []
    for law, e in by_law.items():
        maddeler = ", ".join(sorted(e["maddeler"], key=lambda k: (e["maddeler"][k], k)))
        pages = ", ".join(str(p) for p in sorted(e["pages"]))
        lines.append(f"{law} · {maddeler} · s. {pages}")
    return lines


def _history_pairs(messages):
    pairs, last_user = [], None
    for m in messages:
        if m["role"] == "user":
            last_user = m["content"]
        elif m["role"] == "assistant" and last_user is not None:
            pairs.append((last_user, m["content"]))
            last_user = None
    return pairs


# --------------------------------------------------------------------------- arayüz
CSS = """
<style>
:root { --ha-accent: #1e3a8a; --ha-accent-soft: rgba(30,58,138,.12); --ha-border: rgba(30,58,138,.32); --ha-muted: #64748b; }
.block-container { max-width: 820px; padding-top: 1rem; padding-bottom: 6rem; }
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { visibility: hidden; height: 0; }
header[data-testid="stHeader"] { background: transparent; }
.ha-hero { display: flex; align-items: center; gap: .8rem; margin: .2rem 0 1rem; }
.ha-logo { width: 46px; height: 46px; border-radius: 13px; background: var(--ha-accent); color: #fff;
           display: flex; align-items: center; justify-content: center; font-size: 1.45rem; flex: 0 0 auto; }
.ha-hero h1 { font-size: 1.45rem; margin: 0; line-height: 1.2; }
.ha-hero p { margin: 0; color: var(--ha-muted); font-size: .9rem; }
.ha-welcome { border: 1px solid var(--ha-border); background: var(--ha-accent-soft);
              border-radius: 14px; padding: 1rem 1.1rem; margin-bottom: .9rem; }
.ha-welcome h3 { margin: 0 0 .35rem; font-size: 1.05rem; }
.ha-welcome p { margin: 0; font-size: .92rem; }
.ha-badge { display: inline-block; font-size: .74rem; font-weight: 600; padding: .15rem .6rem; border-radius: 999px;
            background: var(--ha-accent-soft); color: var(--ha-accent); margin-bottom: .4rem; }
.ha-note { color: var(--ha-muted); font-size: .78rem; text-align: center; margin-top: .6rem; }
[data-testid="stChatMessage"] { border-radius: 14px; padding: .55rem .8rem; }
.stButton > button { border-radius: 999px; }
@media (max-width: 640px) {
  .block-container { padding: .5rem .75rem 6rem; }
  .ha-hero h1 { font-size: 1.2rem; }
  .ha-hero p { font-size: .82rem; }
  [data-testid="stChatMessage"] { padding: .45rem .6rem; }
}
</style>
"""

DISCLAIMER = ("Bu asistan hukuki tavsiye vermez; cevaplar yalnızca yüklü mevzuat metnine dayanır. "
              "Kesin değerlendirme için bir avukata danışın.")


def _badge(label):
    st.markdown(f'<span class="ha-badge">📖 {label}</span>', unsafe_allow_html=True)


def _sources_block(sources, rewrite):
    with st.expander("Kaynaklar"):
        st.markdown("\n".join(f"- {s}" for s in sources))
        if rewrite:
            st.caption(f"Arama sorgusu (kanun dili): {rewrite}")


def render_message(m):
    with st.chat_message(m["role"], avatar="⚖️" if m["role"] == "assistant" else "🧑"):
        if m.get("law"):
            _badge(m["law"])
        st.markdown(m["content"])
        if m.get("sources"):
            _sources_block(m["sources"], m.get("rewrite"))


def handle_question(question):
    st.session_state.messages.append({"role": "user", "content": question})
    render_message({"role": "user", "content": question})
    history = _history_pairs(st.session_state.messages[:-1])
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("Mevzuat taranıyor..."):
            try:
                answer, docs, laws, rewrite = create_answer(question, history)
                sources = format_sources(docs)
                law_label = ", ".join(laws) if laws else None
            except Exception as exc:  # ağ/API hataları kullanıcıya okunur biçimde gösterilir
                answer, sources, law_label, rewrite = f"Üzgünüm, cevap üretilemedi: {exc}", [], None, ""
        if law_label:
            _badge(law_label)
        st.markdown(answer)
        if sources:
            _sources_block(sources, rewrite)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources,
                                      "law": law_label, "rewrite": rewrite})


def main():
    st.set_page_config(page_title="Hukuk Asistanı", page_icon="⚖️", layout="centered",
                       initial_sidebar_state="collapsed")
    st.markdown(CSS, unsafe_allow_html=True)

    if not os.getenv("OPENAI_API_KEY"):
        st.error("OPENAI_API_KEY bulunamadı. Proje klasöründeki .env dosyasına ekleyip uygulamayı yeniden başlatın.")
        st.stop()
    if not _pdf_files():
        st.warning(f"**{PDF_DIR}/** klasöründe PDF bulunamadı. mevzuat.gov.tr'den indirdiğiniz kanun ve yönetmelik "
                   "PDF'lerini bu klasöre koyup sayfayı yenileyin. Ayrıntılar için PDFs/README.md dosyasına bakın.")
        st.stop()
    if "messages" not in st.session_state:
        st.session_state.messages = []

    catalog = get_law_catalog()   # ilk çalıştırmada indeksi kurar (spinner gösterir)

    with st.sidebar:
        st.markdown("### ⚖️ Hukuk Asistanı")
        st.caption("Mevzuat tabanlı hukuk bilgi asistanı")
        if st.button("🗑️ Sohbeti temizle", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        with st.expander(f"Yüklü mevzuat ({len(catalog)})"):
            for law, info in catalog.items():
                no = f" · No. {info['law_no']}" if info["law_no"] else ""
                st.markdown(f"- **{law}**{no} · {info['madde_count']} madde")
        st.caption("Cevaplar yalnızca yüklü kanun ve yönetmelik metinlerine dayanır; hukuki tavsiye yerine geçmez.")

    st.markdown(
        '<div class="ha-hero"><div class="ha-logo">⚖️</div><div>'
        '<h1>Hukuk Asistanı</h1><p>Kanun ve yönetmeliklere dayalı soru-cevap asistanı</p></div></div>',
        unsafe_allow_html=True,
    )

    # chat_input ana alanda her zaman en alta sabitlenir; erken çağırmak sıralamayı bozmaz.
    question = st.chat_input("Mevzuat hakkında bir soru yazın...") or st.session_state.pop("pending_question", None)

    if not st.session_state.messages and not question:
        st.markdown(
            '<div class="ha-welcome"><h3>Merhaba 👋</h3><p>Yüklü kanun ve yönetmelikler hakkında soru sorun: '
            'bir maddenin ne dediği, süreler, koşullar ve istisnalar. Somut bir durum anlatırsanız ilgili '
            'kanun ve maddeleri kaynaklarıyla listeler.</p></div>',
            unsafe_allow_html=True,
        )
        st.caption("Örnek sorular")
        cols = st.columns(2)
        for i, q in enumerate(EXAMPLE_QUESTIONS):
            if cols[i % 2].button(q, use_container_width=True, key=f"example_{i}"):
                st.session_state.pending_question = q
                st.rerun()

    for m in st.session_state.messages:
        render_message(m)

    if question:
        handle_question(question)

    st.markdown(f'<p class="ha-note">{DISCLAIMER}</p>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
