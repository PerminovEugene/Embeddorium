# Embeddorium

**Feature Spec: Retrieval, Hybrid Search, Chunk Context & RAG Evaluation**

Версия 0.1 · 29 июня 2026
/

> **Цель документа**
>
> Собрать продуктово-технический backlog фич для Embeddorium: что поддерживать после наивного RAG, как объяснять фичи пользователю, что хранить в данных и в каком порядке реализовывать.

# Короткое позиционирование

Embeddorium — локально запускаемый open-source playground для построения, сравнения и отладки embedding/RAG-баз из разных источников. Ключевая ценность не просто “загрузить документы и спросить”, а понять, какие настройки ingestion, chunking, retrieval, reranking и context building дают лучший результат.

# 1. Product principle

> **Главная продуктовая идея**
>
> Не продавать набор “алгоритмов ради алгоритмов”. Продавать сравнение retrieval strategies: пользователь видит, какие чанки были найдены, почему они попали в контекст, какая стратегия дала лучший ответ и какие настройки использовались.

- Любая фича должна быть воспроизводимой: настройки сохраняются как Processing Variant или Retrieval Profile.
- Любой ответ должен быть объяснимым: видны chunks, ranks, scores, source, pipeline run и final context.
- Любая стратегия должна сравниваться с baseline: dense only, lexical only, hybrid, hybrid + reranker.
- Сначала делать дешевые и понятные улучшения: BM25, heading path, neighbor expansion, parent-child retrieval.
- Продвинутые вещи вроде SPLADE, ColBERT, HyDE и late chunking — позже, когда есть compare/eval UI.

# 2. Core entities

| **Entity**         | **Описание**                                                                                                                | **Зачем нужно**                                                                  |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Dataset            | Логическая группа источников и документов: например “Estonian Tax Acts”, “Project Docs”, “Customer Support Knowledge Base”. | Нужен как верхний уровень для сравнения индексов, запусков и retrieval-профилей. |
| Source             | Оригинальный источник: URL, sitemap, файл, папка, markdown repo, PDF, XML dump, API source.                                 | Позволяет трекать provenance и повторять ingestion.                              |
| Document           | Нормализованный документ после fetch/parse. Хранит title, text, metadata, source_url, hashes.                               | Отделяет raw source от обработанного текста.                                     |
| Processing Variant | Конкретный способ обработки dataset: parser config, chunking, enrichment, embedding model, vector collection.               | Ключ к честному сравнению разных способов построения базы.                       |
| Chunk              | Минимальная retrieval-единица. Хранит original text, enriched text, heading path, token count, parent section.              | Один и тот же документ может породить разные chunks в разных variants.           |
| Index              | Dense vector index, lexical index, sparse index, summary index. Индексы должны быть привязаны к variant.                    | Без этого dense/BM25 сравнение будет нечестным.                                  |
| Retrieval Profile  | Настройки runtime-поиска: retriever, top-k, fusion, reranker, context expansion, context packing.                           | Пользователь сравнивает не только ingestion, но и поиск.                         |
| Retrieval Run      | Один запуск поиска по query. Хранит query, profile, candidates, ranks, scores, final context.                               | Основа debug/compare UI.                                                         |

# 3. Feature backlog by area

> **Приоритеты**
>
> P0 — must-have для сильного MVP. P1 — следующая продуктовая глубина. P2 — advanced/lab-фичи после появления нормального compare/eval слоя.

## 3.1 Ingestion and provenance

| **Feature**          | **Описание**                                                                              | **Ценность**                                              | **Priority** |
| -------------------- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------- | ------------ |
| Source connectors    | Поддержка разных входов: URL, sitemap, local files, markdown repo, PDFs, XML/HTML dumps.  | Дает “anything-to-embeddings” позиционирование.           | P0           |
| Parser profiles      | Сохраняемые настройки парсинга: HTML cleanup, PDF mode, XML mapping, boilerplate removal. | Позволяет повторить обработку и сравнить качество текста. | P0           |
| Processing variants  | Один dataset можно обработать разными chunking/enrichment/embedding settings.             | Главная сущность для экспериментов.                       | P0           |
| Pipeline run history | История запусков ingestion: status, durations, errors, actor logs, counts.                | Нужна отладка pipeline и доверие к базе.                  | P0           |
| Provenance per chunk | Каждый chunk знает source, document, URL/path, heading, offsets, variant.                 | Нужно для цитирования, debug и удаления/переиндексации.   | P0           |
| Rebuild / reindex    | Пересборка индексов для выбранного variant без потери истории.                            | Нужна для playground и продакшн-экспериментов.            | P1           |

## 3.2 Chunking strategies

| **Feature**            | **Описание**                                                                          | **Ценность**                                            | **Priority** |
| ---------------------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------- | ------------ |
| Fixed-size chunking    | Простой split по символам/токенам с overlap.                                          | Baseline. Быстро проверить end-to-end RAG.              | P0           |
| Recursive chunking     | Разбиение с попыткой сохранить paragraphs/sentences/semantic boundaries.              | Лучше fixed-size для обычных текстов.                   | P0           |
| Heading-based chunking | Разбиение по markdown/html/legal headings, chapters, sections.                        | Очень важно для docs/law/tax контента.                  | P0           |
| Semantic chunking      | Разбиение по смысловым границам через embeddings/LLM/heuristics.                      | Может улучшить retrieval, но дороже и сложнее дебажить. | P1           |
| Parent-child structure | Иерархия document → section → chunk. Искать можно по child, отдавать parent.          | Сильно улучшает context completeness.                   | P0           |
| Late chunking          | Сначала long-context encoding, потом chunk embeddings с учетом глобального контекста. | Advanced. Интересно для RAG lab, но не MVP.             | P2           |

## 3.3 Chunk context enrichment

| **Feature**                | **Описание**                                                                              | **Ценность**                                             | **Priority** |
| -------------------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------ |
| Heading path prefix        | Перед chunk добавляется document title + chapter/section/breadcrumbs.                     | Дешево, прозрачно, полезно для законов и документации.   | P0           |
| Metadata prefix            | В enriched text добавляются country, language, source type, effective date, product area. | Помогает retrieval и фильтрации без LLM.                 | P0           |
| Document summary prefix    | Короткое summary документа добавляется к chunks или хранится отдельно.                    | Дает локальному chunk больше глобального контекста.      | P1           |
| LLM contextualization      | LLM генерирует краткий контекст: “этот chunk про ... в документе ...”.                    | Может заметно улучшить retrieval, но стоит токены/время. | P1           |
| Glossary/entity enrichment | Извлечение терминов, сущностей, аббревиатур, статей закона и добавление к индексу.        | Полезно для tax/legal/technical docs.                    | P1           |
| Original vs enriched view  | UI показывает оригинальный chunk и текст, который реально был отправлен в embedding/BM25. | Дает explainability и убирает магию.                     | P0           |

## 3.4 Indexing and retrieval algorithms

| **Feature**                | **Описание**                                                               | **Ценность**                                                        | **Priority** |
| -------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------ |
| Dense retrieval            | Query embedding → vector search in Qdrant → top-k chunks.                  | Semantic baseline. Обязателен для любого RAG.                       | P0           |
| Lexical/BM25 retrieval     | Full-text/BM25 поиск по chunk text/enriched text.                          | Ловит exact terms: номера статей, формы, аббревиатуры, имена.       | P0           |
| Hybrid RRF                 | Dense top-k + BM25 top-k → Reciprocal Rank Fusion.                         | Лучший первый hybrid mode: robust, без сложной score normalization. | P0           |
| Weighted hybrid            | Dense score и lexical score смешиваются с alpha/beta weights.              | Дает UI-ползунок, но требует нормализации score.                    | P1           |
| Sparse neural / SPLADE     | Learned sparse representations вместо обычного BM25.                       | Advanced lexical-like retrieval с query/document expansion.         | P2           |
| ColBERT / late interaction | Multi-vector token-level matching вместо одного vector per chunk.          | Более точный retrieval, но тяжелее storage и инфраструктура.        | P2           |
| Summary index              | Отдельный dense index по summaries вместо original chunks или рядом с ним. | Может улучшить recall, но summary может терять детали.              | P1           |

## 3.5 Query transformation

| **Feature**           | **Описание**                                                                                  | **Ценность**                                                              | **Priority** |
| --------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ------------ |
| No transform baseline | Оригинальный query без rewrite.                                                               | Нужен как честный baseline.                                               | P0           |
| Query rewrite         | LLM/heuristic переписывает query в более retrieval-friendly форму.                            | Может улучшить короткие/грязные вопросы.                                  | P1           |
| Multi-query retrieval | Генерация 3–5 альтернативных запросов, результаты сливаются через RRF.                        | Повышает recall, особенно в сложной терминологии.                         | P1           |
| HyDE                  | LLM пишет hypothetical answer/document, embedding этого текста используется для dense search. | Иногда помогает абстрактным query, но может занести hallucinated framing. | P2           |
| Metadata-aware query  | Query parser выделяет filters: country, language, source, date, document type.                | Для legal/tax это часто важнее, чем “умный” embedding.                    | P0           |

## 3.6 Reranking and result selection

| **Feature**            | **Описание**                                                              | **Ценность**                                              | **Priority** |
| ---------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------- | ------------ |
| Cross-encoder reranker | После retrieval модель оценивает пары query/chunk и сортирует candidates. | Обычно дает сильный quality bump после hybrid.            | P1           |
| Provider reranker      | Cohere/Voyage/other API reranker as optional provider.                    | Быстро добавить quality mode без локального ML ops.       | P1           |
| Local reranker         | Локальная модель reranking на GPU/CPU.                                    | Соответствует local/open-source позиционированию.         | P1           |
| LLM reranker           | LLM выбирает/оценивает chunks по релевантности.                           | Гибко, но дороже и медленнее; лучше как eval/debug mode.  | P2           |
| MMR diversity          | Выбор релевантных, но не дублирующих друг друга chunks.                   | Уменьшает повторение одинаковых соседних chunks в prompt. | P1           |
| Deduplication          | Near-duplicate detection между retrieved chunks.                          | Чистит контекст, особенно при overlapping chunking.       | P0           |

## 3.7 Context building

| **Feature**                   | **Описание**                                                                   | **Ценность**                                                             | **Priority** |
| ----------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ | ------------ |
| Top-k context                 | Просто взять final top-k chunks.                                               | Baseline для сравнения.                                                  | P0           |
| Neighbor expansion            | К найденному chunk добавить ±N соседних chunks.                                | Закрывает случаи, когда условие/определение рядом, но не в том же chunk. | P0           |
| Parent section context        | Искать по small chunks, но отдавать parent section.                            | Часто лучше для legal/docs, где смысл распределен по section.            | P0           |
| Context packing               | Выбор, порядок и группировка chunks в prompt с учетом token budget.            | Отдельная стадия качества ответа.                                        | P1           |
| Lost-in-middle aware ordering | Класть самые важные chunks в начало/конец контекста, а не случайно в середину. | Повышает шанс, что LLM использует важный факт.                           | P1           |
| Context compression           | Сжать retrieved context перед answer generation.                               | Полезно при длинных documents, но может потерять детали.                 | P2           |
| Citation context              | Хранить source spans/offsets для цитирования и explainability.                 | Критично для trust в legal/tax сценариях.                                | P0           |

## 3.8 Evaluation, comparison and debugging

| **Feature**             | **Описание**                                                                                | **Ценность**                                                | **Priority** |
| ----------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------- | ------------ |
| Retrieval trace         | Для каждого query показывать dense_rank, bm25_rank, fused_rank, reranker_score, final_rank. | Главная explainability-фича.                                | P0           |
| Compare page            | Сравнение Dense vs BM25 vs Hybrid vs Hybrid+Reranker на одном query.                        | Делает Embeddorium retrieval debugger, а не просто chatbot. | P0           |
| Manual relevance labels | Пользователь помечает chunks как relevant/irrelevant/partially relevant.                    | Создает eval dataset без сложной автоматизации.             | P1           |
| Golden queries          | Набор тестовых вопросов для dataset/variant.                                                | Позволяет регрессионно сравнивать изменения pipeline.       | P1           |
| Metrics dashboard       | Recall@k, MRR, nDCG, hit rate, answer groundedness notes.                                   | Нужно для серьезного сравнения retrieval quality.           | P1           |
| Answer comparison       | Показывать не только retrieved chunks, но и финальные ответы разных profiles.               | Продуктово понятно пользователю.                            | P0           |
| Run diff                | Diff между двумя retrieval runs: что добавилось/пропало/переехало в rank.                   | Очень полезно для настройки profiles.                       | P1           |

# 4. Recommended implementation order

| **Phase**                      | **Что входит**                                                                                          | **Rationale**                                                 |
| ------------------------------ | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| Phase 1: honest baseline       | Dense retrieval, chunks in PostgreSQL, Qdrant index, processing_variant_id everywhere, retrieval trace. | Сначала доказать end-to-end и сохранение provenance.          |
| Phase 2: lexical baseline      | PostgreSQL FTS/BM25 over chunks, BM25-only mode, compare Dense vs BM25.                                 | Перед hybrid нужно увидеть отдельную ценность lexical search. |
| Phase 3: hybrid MVP            | Dense + BM25 candidates, RRF fusion, final top-k, UI badges: dense/bm25/both.                           | Первый настоящий hybrid search без лишней сложности.          |
| Phase 4: context improvements  | Heading path enrichment, metadata prefix, neighbor expansion, parent-child retrieval.                   | Дешевые фичи с большой практической отдачей.                  |
| Phase 5: reranking and packing | Cross-encoder/local/provider reranker, MMR, context packing, dedupe.                                    | Сильное улучшение качества после candidate retrieval.         |
| Phase 6: lab features          | Multi-query, contextual chunk enrichment, summary index, HyDE, SPLADE, ColBERT, late chunking.          | Advanced слой после compare/eval UI.                          |

# 5. Suggested MVP scope

- Processing Variants: сохранять chunking settings, embedding model, collection name, full-text index state.
- Retrieval Profiles: dense only, BM25 only, hybrid RRF.
- Chunk context: original text + heading path prefix + metadata prefix.
- Context builder: top-k, neighbor expansion, parent section context.
- Compare UI: один query, три стратегии, список chunks, ranks/scores, badges source=dense/bm25/both.
- Trace storage: retrieval_run и retrieval_run_results с rank/score/fusion details.
- Manual labels: relevant / not relevant для chunks в compare page.

# 6. Data model notes

| **Table**             | **Key fields**                                                                                                                       |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| chunks                | id, document_id, dataset_id, processing_variant_id, text, enriched_text, heading_path, token_count, parent_id, metadata_json         |
| processing_variants   | id, dataset_id, name, parser_config, chunking_config, enrichment_config, embedding_provider, embedding_model, vector_store_config    |
| retrieval_profiles    | id, name, dataset_id, variant_id, retriever_type, dense_top_k, lexical_top_k, fusion_method, reranker_config, context_builder_config |
| retrieval_runs        | id, query, dataset_id, variant_id, profile_id, created_at, latency_ms, final_context_tokens, answer_id                               |
| retrieval_run_results | retrieval_run_id, chunk_id, source, dense_rank, lexical_rank, dense_score, lexical_score, fused_score, reranker_score, final_rank    |
| manual_judgments      | id, retrieval_run_id, chunk_id, label, note, created_at                                                                              |

# 7. UI structure

- Datasets: список datasets, источники, ingestion status, количество documents/chunks/indexes.
- Processing Variants: настройки обработки, rebuild/reindex, lineage и сравнение variants.
- Retrieval Profiles: настройки query-time поиска и context building.
- Playground: задать query, выбрать variant/profile, увидеть answer + context.
- Compare: один query → несколько profiles/variants side-by-side.
- Trace view: подробный список candidates, ranks, scores, reasons, final context order.
- Evaluation: golden queries, manual labels, метрики, run diff.

# 8. Anti-goals for the next step

- Не тащить Elasticsearch/OpenSearch до проверки PostgreSQL FTS/BM25 baseline.
- Не делать SPLADE/ColBERT до появления retrieval trace и compare UI.
- Не делать LLM contextualization как default: сначала heading path + metadata prefix.
- Не смешивать chunks разных processing variants в одном retrieval сравнении.
- Не оценивать качество “на глаз” только по ответу LLM: нужно видеть retrieved chunks и ranks.
- Не строить agentic RAG раньше простого reproducible retrieval pipeline.

# 9. One-line feature positioning

> **Product sentence**
>
> Embeddorium lets users build the same RAG dataset in multiple ways and compare dense, lexical, hybrid, reranked and context-expanded retrieval strategies with full visibility into which chunks were selected, why they were selected, and how each pipeline setting affected the final answer.
