A. Dataset / ingestion
Dataset versioning
Один и тот же набор документов фиксируется как версия: dataset_v1, dataset_v2. Потом можно честно сравнивать пайплайны на одинаковом корпусе.
Document groups / collections
Группы типа knowledge-base-a, stripe-docs, my-project-docs. Это база для экспериментов и ACL.
Source adapters
Поддержка разных источников: URL crawl, sitemap, локальные PDF/XML/HTML/Markdown, GitHub repo, npm package docs, raw text paste.
Crawl policy presets
Настройки глубины, allowed domains, deny patterns, max pages, content-type filter, canonical URL normalization.
Raw artifact storage
Сохранять raw HTML/PDF/XML отдельно от parsed text. Потом можно перепарсить документ новым парсером без повторного crawling.
Parser comparison mode
Один документ прогнать через разные парсеры: naive HTML text, Readability, markdown extraction, PDF text parser, OCR fallback.
Boilerplate removal toggle
Включать/выключать удаление навигации, footer, cookie banners, sidebars. Очень важная фича для web docs.
Content deduplication
Найти near-duplicate pages/chunks по hash/simhash/minhash, чтобы не забивать Qdrant повторяющимся мусором.
Language detection
Автоопределение языка документа/чанка. Потом можно выбирать embedding model по языку.
Document structure extraction
Сохранять заголовки, section hierarchy, таблицы, списки, ссылки, anchors. Для RAG это часто важнее, чем просто plain text.
B. Chunking
Fixed token chunking
Базовая стратегия: N tokens + overlap. Нужна как baseline.
Recursive character/token chunking
Делить сначала по секциям, потом по абзацам, потом по предложениям, потом по токенам. Хороший default для большинства docs.
Semantic chunking
Делить по semantic shift: когда соседние предложения резко меняют тему.
Heading-aware chunking
Чанк наследует путь заголовков: Tax Act > Chapter 2 > VAT rate. Это сильно помогает retrieval.
Paragraph-first chunking
Для законов, документации и markdown часто лучше не резать абзацы пополам.
Sentence-window chunking
Чанк — центральное предложение плюс окно соседних предложений. Хорошо для QA и factual retrieval.
Table-aware chunking
Таблицы не должны разваливаться на случайные строки. Можно хранить таблицу как отдельный chunk type.
Code-aware chunking
Для репозиториев: функция/класс/файл как boundary, а не просто 512 токенов.
XML/HTML node-aware chunking
Для законов и structured docs: chunk по XML node, article, paragraph, subsection.
Late chunking mode
Сначала long-context transformer, потом pooling по chunk boundaries. Это отдельный advanced режим, не замена всем стратегиям.
Long late chunking
Когда документ длиннее context window модели: sliding document windows + stitching/pooling. Это прям hardcore-фича.
Chunk overlap strategy selector
Overlap by tokens, sentences, headings, semantic window. Не просто число 128, а разные политики.
Chunk size sweep
Автоматически прогнать один dataset на размерах, например 128/256/512/1024/2048 tokens, и сравнить retrieval.
Chunk preview UI
До embedding показать пользователю, как реально порезался документ. Это must-have для playground.
Chunk quality warnings
Подсветка плохих чанков: слишком короткий, слишком длинный, без заголовка, только меню, только legal boilerplate, broken table.
C. Embeddings
Embedding provider abstraction
OpenAI, Cohere, Voyage, Jina, local TEI, sentence-transformers, Ollama-like local endpoint, custom HTTP endpoint.
Embedding model registry
Модель хранится как entity: name, dimension, max tokens, pooling, normalization, language support, provider, cost.
Dimension validation
Нельзя случайно отправить 1024-dim vectors в коллекцию на 768-dim. Банальная, но критичная фича.
Matryoshka dimension selector
Для моделей, которые поддерживают reduced dimensions: сравнить 1024 vs 512 vs 256 vs 128 по качеству/стоимости.
Embedding normalization toggle
Включать/выключать L2 normalization. Важно при сравнении cosine vs dot product.
Batch size tuning
UI для batch size, concurrency, retry policy. На локальной 3060 это прямо влияет на throughput.
Embedding cache
Hash от (text + model + config) → reuse embedding. Иначе эксперименты будут постоянно пересчитывать одно и то же.
Token usage / cost accounting
Для каждого variant показывать tokens, price estimate, latency, vectors count, storage size.
Dense + sparse embeddings
Например dense vectors + BM25/sparse vector. Это база для hybrid retrieval.
Multi-vector embeddings
Поддержка ColBERT-like или BGE-M3 multi-vector режима. Это уже уровень “серьезный IR”, не игрушечный RAG.
D. Vector index / storage
Similarity metric selector
Cosine, dot product, euclidean. В Qdrant distance задается на уровне vector config/collection, поэтому разные distance обычно означают разные коллекции или named vectors.
Named vectors per chunk
Один chunk может иметь несколько vectors: dense_bge, dense_jina, sparse_bm25, title_vector, summary_vector.
Collection-per-variant mode
Простой режим: каждый pipeline variant пишет в свою Qdrant collection.
Shared collection with named vectors
Продвинутый режим: один logical dataset, но разные vector spaces внутри point payload/named vectors.
Index parameter tuning
HNSW params, quantization, on-disk payload, optimizer settings. Не для новичка, но очень прокачивает понимание vector DB.
Payload schema editor
Настраивать, какие metadata попадут в Qdrant: source URL, title path, language, date, section, document type.
Payload filter builder
Retrieval с фильтрами: только country=EE, только doc_type=law, только year>=2024.
Vector lifecycle tools
Re-embed, delete stale chunks, migrate collection, rebuild index, compare old/new embeddings.
Storage diff view
После изменения chunking показать: было 10k chunks, стало 6k; storage −35%; avg chunk length +42%.
E. Retrieval strategies
Top-k tuning
Сравнить top_k=3/5/10/20/50. Часто качество RAG ломается не моделью, а слишком маленьким или слишком большим k.
Score threshold tuning
Минимальный similarity score, ниже которого chunk не попадает в context.
MMR retrieval
Maximal Marginal Relevance: выбирать не только самые похожие chunks, но и разнообразные, чтобы не получить 10 почти одинаковых результатов.
Hybrid search
Dense vector + keyword/BM25/sparse. Для законов, API docs и exact terms это почти обязательно.
Reranker stage
После top-50 retrieval прогнать cross-encoder/reranker и взять top-5. Это один из самых заметных апгрейдов качества RAG.
Query rewriting / expansion
Перед retrieval генерировать несколько вариантов запроса: original, keyword-heavy, legal-style, synonyms, translated query.
Еще 25, если захочешь сделать прям monster playground

Я бы добавил сверх списка еще вот это, потому что оно реально делает продукт сильнее:

Фича Зачем
Contextual retrieval Добавлять к каждому chunk краткий контекст документа/секции перед embedding. Альтернатива late chunking.
Parent-child retrieval Искать по маленьким chunks, но отдавать в LLM родительскую секцию.
Small-to-big retrieval Сначала найти точный маленький chunk, потом расширить контекст вокруг него.
Graph retrieval Связи document → section → concept → formula → citation. Особенно для законов.
Citation extraction Автоматически вытаскивать ссылки на статьи, параграфы, законы, external references.
Entity extraction Компании, налоги, ставки, даты, роли, продукты, API names.
Concept map Автоматически строить карту понятий из корпуса. Для твоих tax docs — очень полезно.
Answerability test Проверять, можно ли ответить на вопрос по найденным chunks.
Golden dataset builder UI, где ты руками создаешь вопросы и отмечаешь правильные chunks.
Retrieval metrics Recall@k, Precision@k, MRR, nDCG, hit rate.
LLM-as-judge eval LLM оценивает answer faithfulness, context relevance, hallucination risk.
Side-by-side variant comparison Один query → результаты из 2–5 pipeline variants рядом.
A/B experiment reports “BGE-M3 + semantic chunks лучше на 12% Recall@10, но дороже на 30%”.
Failure explorer Показывает queries, где variant провалился.
Chunk attribution heatmap Какие chunks реально использовались в ответах.
Embedding drift detection При смене модели показать, насколько изменилось пространство nearest neighbors.
Cluster visualization UMAP/t-SNE карта chunks по embedding space.
Outlier detection Найти chunks, которые выглядят как мусор или не вписываются в corpus.
Duplicate answer detector Когда retrieval возвращает много одинакового смысла из разных pages.
Prompt template variants Compare prompt styles: strict citations, concise answer, legal reasoning, JSON extraction.
Context packing strategy Как упаковывать chunks в LLM context: by score, by document order, by section grouping.
Token budget optimizer Автоматически выбирать chunks под лимит 4k/8k/32k context.
MCP server mode Поднять dataset как MCP tool: search_docs, get_chunk, list_sources, explain_retrieval.
Export pipeline config YAML/JSON export/import, чтобы люди могли шарить experiments.
Reproducibility snapshot Dataset hash + parser version + chunker config + model version + Qdrant settings.
