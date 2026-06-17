# Sprint Change Proposal — Gap Detection Backend (FR7) cho Epic 4

- **Ngày:** 2026-06-17
- **Người đề xuất:** Dat
- **Workflow:** correct-course (BMad)
- **Mode review:** Batch
- **Phân loại phạm vi:** **Major** — bổ sung 3 story backend hiện thực hóa cả một hệ con (GraphRAG Engine + Graph Extraction + Gap Analyst Agent) vốn đã có trong `architecture.md` nhưng **chưa từng được phân rã thành story**. Chạm pipeline ingestion, ontology Neo4j mới, và topology LangGraph mới.

---

> **🔢 CẬP NHẬT SAU CHỐT (Architect review + gộp story 2026-06-17):** Đã chốt áp dụng, sau đó **gộp 8→5 story** để giảm số lần vibecode. Nguồn sự thật = `epics.md` (Story 4.1–4.5). Ánh xạ từ ID đề xuất ban đầu:
>
> | ID đề xuất ban đầu | Story | ID cuối (epics.md) |
> |---|---|---|
> | Sync Postgres→Neo4j **+ Soft-delete & GC** | gộp | **4.1** Sync + GC |
> | Cytoscape draw **+** Node Detail Card | gộp | **4.2** Knowledge Map UI |
> | Graph Extraction (ontology) | (giữ) | **4.3** |
> | GraphRAG Engine **+** Tô viền gap | gộp | **4.4** Gap Detection trên Map |
> | Gap Analyst Agent + Supervisor | (giữ) | **4.5** |
>
> Logic gộp: (4.1) GC cùng module sync/Neo4j-lifecycle, ride-along không chặn; (4.2) cùng component Cytoscape FE; (4.4) vertical slice BE endpoint + FE tiêu thụ. Giữ riêng: 4.3 (LLM extraction nặng), 4.5 (đụng orchestrator, rủi ro tích hợp cao).
> **Vá lỗ hổng tab Graph (Architect):** Story 4.2 đổi [Frontend]→[BE+FE] + endpoint đọc đồ thị (150/300+has_more, expand), phân biệt node toàn-văn/metadata, mạng tác giả [:AUTHORED], legend, sync-indicator, nút "Hỏi AI về bài này". Cầu nối Gap→Chat nhúng AC 4.4/4.5.
> **Cập nhật phạm vi (2026-06-17):** **Leiden community detection + community summaries chuyển sang Phase 2** (quyết định Dat). Gap detection MVP (Story 4.4) dùng Cypher traversal — đủ FR7. `graph_search` giữ ở MVP cho Story 4.5.
> 3 điều chỉnh Architect đã ngấm vào epics.md: (a) Story 4.3 (extraction) *extends* arq worker Story 2.5 + **AC backfill bắt buộc**; (b) Story 4.5 dùng **router nhẹ/lazy** giữ SM-3; (c) chốt version model khi create-story (doc lệch 1.5 §7 vs 2.5 §6.2).

---

## Section 1 — Issue Summary

### Vấn đề
Rà soát Epic 4 (2026-06-17) phát hiện: Epic 4 cam kết phủ **FR7 (Phát hiện khoảng trống & mâu thuẫn)** và **FR9 (Trực quan hóa)**, nhưng 4 story hiện tại chỉ phủ **FR9** (sync + vẽ Cytoscape). **Phần "bộ não" tính toán khoảng trống của FR7 không có story nào sinh ra dữ liệu** — Story 4.4 ([Frontend]) chỉ *tô viền* đỏ/vàng dựa trên dữ liệu không tồn tại.

### Bằng chứng từ `architecture.md`
Architecture định nghĩa rất chi tiết hệ con này nhưng không được "storied":

| Thành phần architecture | Vị trí | Story phủ? |
|---|---|---|
| **Giai đoạn 2 — Graph Extraction** (`gemini-2.5-pro` bóc tách Finding/Limitation/Method + edges học thuật) | §6.2 | ❌ Không |
| **Ontology học thuật**: `Finding`, `Limitation`, `[:CONTRADICTS]`, `[:SUPPORTS]`, `[:HAS_LIMITATION]`, `[:FILLS_GAP]` | §5.2 (L147–150) | ❌ Không (4.1 chỉ MERGE Paper/CITES từ outbox) |
| **Module 1 GraphRAG Engine**: `gap_detection(project_id)->GapContext`, `graph_search`, `community_summary_search` | §5.2 (L152–155) | ❌ Không |
| **Leiden Community Detection** + summaries (`gemini-1.5-flash`) | §5.2 (L151) | ❌ Không |
| **Gap Analyst Agent + Supervisor routing** + `gap_detection_tool`/`graph_search_tool` | §7.1–7.2 (L209–217) | ❌ Không (orchestrator hiện chỉ là single RAG node — Story 3.2/3.6) |
| **Context Fusion** (gộp vector_search + graph_search) | §7.4 (L228–229) | ❌ Không (Story 3.6 chỉ pgvector thuần) |

### Hệ quả
- **FR7 không đạt:** PRD FR-7 yêu cầu *"AI Agent cung cấp phân tích so sánh chéo, chỉ ra mâu thuẫn... câu trả lời phải chỉ rõ nguồn"*. Không có agent/engine nào làm việc này.
- **FR9 chế độ "Tìm khoảng trống" rỗng:** PRD FR-9 yêu cầu *"phân tích cấu trúc đồ thị (cụm cô lập) kết hợp RAG để highlight"*. Story 4.4 render viền nhưng không có API/dữ liệu nguồn → tính năng trống.

---

## Section 2 — Impact Analysis

### Epic Impact
- **Epic 4** (`backlog`): bổ sung **3 story backend mới** (4.5, 4.6, 4.7). Vẫn giữ FR covered = FR7, FR9 nhưng nay được phủ thực chất.
- **Epic 2** (ingestion): ranh giới — Graph Extraction (Story 4.5) là Giai đoạn 2 của pipeline ingest. Đặt ở Epic 4 vì là **nguồn dữ liệu cốt lõi cho graph/gap**, nhưng **phụ thuộc** pipeline Story 2.5 (đã done) và worker arq.
- **Epic 3** (chat): Story 4.7 (Gap Analyst Agent + Supervisor) **mở rộng orchestrator** xây ở Story 3.2/3.6 — biến single RAG node thành topology Router-Worker. Không mở lại Epic 3; coi như tiến hóa kiến trúc agent thuộc Epic 4.

### Story Impact
| Story | Ảnh hưởng |
|---|---|
| 4.1 (Sync Neo4j) | Không đổi logic, nhưng nay phải đồng bộ thêm **node/edge ontology** (Finding/Limitation + academic edges) do 4.5 ghi vào `sync_outbox`, không chỉ Paper/CITES/Author. |
| 4.3 (Cytoscape draw) | Không đổi — vẫn vẽ Paper/CITES; có thể hiển thị thêm Author/Topic nếu muốn. |
| 4.4 (Node Detail + visual gap) | **Nay có nguồn dữ liệu thật**: tiêu thụ endpoint `GET /api/projects/{id}/graph/gaps` của Story 4.6 để tô viền đỏ (CONTRADICTS) / vàng (cụm cô lập). |
| 3.6 (Real RAG) | Story 4.7 mở rộng: thêm `graph_search` vào fusion context (ARCH §7.4) bên cạnh pgvector. Citation Guardrail tái dùng nguyên trạng. |

### Artifact Conflicts (cần cập nhật)
- `epics.md`: thêm 3 story 4.5/4.6/4.7; thêm dòng "Khuyến nghị thứ tự thực thi" cho Epic 4; cập nhật ghi chú phụ thuộc ở 4.1/4.4; cập nhật dòng tổng số story; cập nhật mục "Khoảng trống đã biết".
- `sprint-status.yaml`: thêm `4-5`, `4-6`, `4-7` = backlog.
- `architecture.md`: **không cần đổi** — đã mô tả đầy đủ; đây là hiện thực hóa thiết kế đã có.

### Technical Impact
- **Mới:** Neo4j driver + Cypher MERGE cho ontology học thuật; thuật toán Leiden (community detection); 3 API Module 1; LangGraph Supervisor + Gap Analyst node; entity resolution tác giả (Jaccard ≥0.3 / cosine ≥0.5, ưu tiên ORCID).
- **NFR:** Giai đoạn 2 dùng `gemini-2.5-pro` — nặng token; chạy trong worker arq (concurrency_limit=2, OMP/OPENBLAS=1). Leiden chạy ngầm sau ingest. Tôn trọng RAM Neo4j 8GB (ARCH-1).

---

## Section 3 — Recommended Approach

**Direct Adjustment** — thêm 3 story backend mới vào Epic 4 (không rollback, không cắt scope). Giữ 4.3/4.4 nguyên, bổ sung phụ thuộc.

- **Lý do:** Thiết kế đã đầy đủ trong architecture; đây là phần triển khai bị bỏ sót khi phân rã story. Không thể "tô viền khoảng trống" (4.4) nếu không có engine sinh dữ liệu.
- **Hướng thay thế đã cân nhắc & loại bỏ:**
  - *MVP Review (cắt FR7):* Không nên — FR7 + SM (citation accuracy) là giá trị lõi của sản phẩm ("phát hiện khoảng trống nghiên cứu" nằm ngay trong tên đề tài AI20K-031).
  - *Gộp vào 1 story:* Không nên — 3 quan tâm tách bạch (ETL ontology / engine truy vấn / agent hội thoại), mỗi phần đủ lớn; gộp sẽ phá vỡ vertical-slice và khó test.
- **Effort:** Cao. 4.5 (LLM extraction + sync ontology) và 4.6 (engine + Leiden) là nặng nhất; 4.7 (agent topology) trung bình nhưng rủi ro tích hợp cao.
- **Rủi ro chính:** (a) Chất lượng/độ ổn định JSON của Graph Extraction (`gemini-2.5-pro`); (b) Chi phí/latency LLM Pro; (c) Refactor orchestrator từ single-node sang Supervisor-Worker chạm Story 3.2/3.6; (d) Hiệu năng Leiden trên VM 32GB.

### Khuyến nghị thứ tự thực thi (do phụ thuộc dữ liệu)
```
4.1 (sync) → 4.5 (extraction ontology) → 4.6 (engine gap_detection) → 4.3 (vẽ) → 4.4 (visual gap) → 4.7 (Gap Analyst Agent chat)
```

---

## Section 4 — Detailed Change Proposals

### 4.A — Story mới (thêm vào `epics.md`, sau Story 4.4)

```
### Story 4.5: [Backend] Graph Extraction — Trích xuất Ontology Học thuật (Stage-2 Ingestion) — ⏳ backlog

Hiện thực Giai đoạn 2 pipeline ingest (gemini-2.5-pro): từ Markdown đã cấu trúc hóa (GĐ1 Story 2.5),
bóc tách Nodes học thuật (Finding{confidence_score}, Limitation, Method, Dataset, Topic, Problem)
và Edges học thuật ([:HAS_FINDING], [:HAS_LIMITATION], [:CONTRADICTS], [:SUPPORTS], [:FILLS_GAP]),
kèm Author entity resolution (chuẩn hóa tên + Jaccard co-author ≥0.3 / cosine topic ≥0.5, ưu tiên ORCID).
Ghi các thực thể/quan hệ này vào sync_outbox để Story 4.1 đẩy sang Neo4j.

- **Gộp từ kế hoạch cũ:** Phát sinh trong thực thi (correct-course 2026-06-17). Hiện thực hóa ARCH §6.2 (GĐ2 Graph Extraction) + §5.2 (Graph Schema).
- **Phụ thuộc:** Story 2.5 (pipeline ingest + worker arq) đã done; Story 4.1 (sync) để hiển thị.
- **FRs:** FR7, FR9. (ARCH §5.2, §6.2.)

**AC nháp (chi tiết hóa khi create-story):**
1. Node worker arq nhận Markdown cấu trúc + metadata, gọi gemini-2.5-pro sinh JSON {nodes, edges} theo schema ontology.
2. Sinh Finding kèm confidence_score (0.0–1.0); Limitation gắn [:HAS_LIMITATION] vào Paper.
3. Suy luận quan hệ [:CONTRADICTS]/[:SUPPORTS] giữa các Finding xuyên tài liệu trong cùng project.
4. Author entity resolution theo heuristic ARCH §5.2 (ORCID ưu tiên, fallback Jaccard/cosine), tránh gộp nhầm trùng tên.
5. Ghi event vào sync_outbox (idempotent, scope project_id) để 4.1 MERGE vào Neo4j; retry/Tenacity khi LLM rate-limit (ARCH §6.2 độc lập Stage retry).
6. Tôn trọng tài nguyên: chạy trong worker arq concurrency_limit=2; không chặn thread chính.
```

```
### Story 4.6: [Backend] GraphRAG Engine — gap_detection, graph_search & Leiden Communities — ⏳ backlog

Module 1 (GraphRAG Engine) trên Neo4j cung cấp: gap_detection(project_id)->GapContext (phân tích cấu
trúc đồ thị: cụm node cô lập/thiếu liên kết trích dẫn + truy vấn [:CONTRADICTS] + Limitation chưa
[:FILLS_GAP], kết hợp tín hiệu RAG), graph_search(entities, project_id)->GraphContext, và
community_summary_search. Worker ngầm chạy Leiden community detection + sinh Hierarchical Community
Summaries (gemini-1.5-flash) lưu ngược Neo4j. Expose endpoint trình bày
GET /api/projects/{project_id}/graph/gaps trả danh sách node/edge bị gắn cờ (mâu thuẫn/cô lập) cho frontend.

- **Gộp từ kế hoạch cũ:** Phát sinh trong thực thi (correct-course 2026-06-17). Hiện thực hóa ARCH §5.2 (Module 1 API + Leiden Indexing).
- **Phụ thuộc:** Story 4.1 (Neo4j có dữ liệu), Story 4.5 (ontology Finding/Limitation/edges).
- **FRs:** FR7, FR9. (ARCH §5.2.)

**AC nháp:**
1. gap_detection(project_id) trả GapContext: danh sách CONTRADICTS, Limitation chưa được FILLS_GAP, và cụm node cô lập (ít/không có cạnh CITES nối với phần còn lại).
2. graph_search(entities, project_id) truy vấn quan hệ 1–2 hop quanh thực thể khóa, scope project_id.
3. community_summary_search(query, project_id) tìm trên tóm tắt cộng đồng.
4. Worker Leiden gom Community + gemini-1.5-flash tóm tắt phân cấp, chạy ngầm sau ingest (arq/cron).
5. Endpoint GET /api/projects/{id}/graph/gaps (JWT + owner scoping) trả {nodes_flagged, edges_flagged, reason} cho UI 4.4.
6. Truy vấn Cypher có scope project_id chống rò rỉ chéo dự án (IDOR). Tôn trọng RAM Neo4j 8GB (ARCH-1).
```

```
### Story 4.7: [BE+FE] Gap Analyst Agent & Supervisor Routing trong LangGraph — ⏳ backlog

Tiến hóa orchestrator (sau Story 3.6) từ single RAG node sang topology Router-Worker (ARCH §7.1):
Supervisor Agent (gemini-1.5-flash) định tuyến tin nhắn + ui_context tới Research&RAG Agent hoặc
Gap Analyst Agent. Gap Analyst Agent (gemini-1.5-pro) gọi gap_detection_tool + graph_search_tool
(Module 1, Story 4.6) phân tích mâu thuẫn/hạn chế/cơ hội nghiên cứu, sinh câu trả lời CHỈ RÕ NGUỒN
[N] (FR7), qua Citation Guardrail (Story 3.4) trước khi stream SSE. Research&RAG Agent bổ sung
graph_search vào fusion context (ARCH §7.4) bên cạnh pgvector của Story 3.6.

- **Gộp từ kế hoạch cũ:** Phát sinh trong thực thi (correct-course 2026-06-17). Hiện thực hóa ARCH §7.1, §7.2, §7.4.
- **Phụ thuộc:** Story 3.6 (real RAG node + SSE protocol), Story 4.6 (gap_detection/graph_search tools).
- **FRs:** FR6, FR7. (ARCH §7.)

**AC nháp:**
1. Supervisor node (gemini-1.5-flash) phân loại intent → route tới RAG Agent / Gap Analyst Agent / trả lời giao tiếp thường.
2. Gap Analyst Agent gọi gap_detection_tool + graph_search_tool, tổng hợp câu trả lời mâu thuẫn/hạn chế kèm thẻ [N] trỏ tài liệu nguồn thực tế.
3. Research&RAG Agent fusion graph_search vào context (giới hạn ~8000 token, ARCH §7.4 Bước 2).
4. Mọi câu trả lời đi qua Citation Guardrail (tái dùng Story 3.4) + citation_map (tái dùng Story 3.6) → tooltip thật.
5. Stream sự kiện tiến trình {"event":"agent_thinking","status":...} trước khi stream text (ARCH §7.4 Bước 4).
6. LLM call qua LLMRouter (user key → fallback system key), rate-limit cách ly (ARCH §7.3).
7. Empty/không đủ dữ liệu đồ thị → trả lời an toàn, không bịa mâu thuẫn (chống hallucination).
```

### 4.B — Cập nhật ghi chú phụ thuộc ở Story 4.1 và 4.4 (`epics.md`)

```
Story 4.1 — thêm dòng:
  - **Lưu ý mở rộng:** Ngoài Paper/CITES/Author, worker còn đồng bộ ontology học thuật
    (Finding/Limitation + edges) do Story 4.5 ghi vào sync_outbox.

Story 4.4 — thêm dòng:
  - **Phụ thuộc:** Story 4.6 — tô viền dựa trên GET /api/projects/{id}/graph/gaps (đỏ=CONTRADICTS, vàng=cụm cô lập).
```

### 4.C — Thêm dòng thứ tự thực thi Epic 4 (`epics.md`, đầu phần Epic 4)

```
> **Thứ tự thực thi khuyến nghị (do phụ thuộc dữ liệu):**
> 4.1 → 4.5 → 4.6 → 4.3 → 4.4 → 4.7
```

### 4.D — Cập nhật dòng trạng thái tổng (`epics.md` dòng ~116–117)

```
OLD: Tổng: **27 story** ...
NEW: Tổng: **30 story** (+3 story Gap Detection backend 4.5/4.6/4.7, correct-course 2026-06-17) ...
```

### 4.E — `sprint-status.yaml` (thêm trong khối epic-4, trước `epic-4-retrospective`)

```
OLD:
  4-4-node-detail-card-tich-hop-phat-hien-khoang-trong-truc-quan: backlog
  epic-4-retrospective: optional
NEW:
  4-4-node-detail-card-tich-hop-phat-hien-khoang-trong-truc-quan: backlog
  4-5-graph-extraction-trich-xuat-ontology-hoc-thuat: backlog
  4-6-graphrag-engine-gap-detection-graph-search-leiden: backlog
  4-7-gap-analyst-agent-supervisor-routing-langgraph: backlog
  epic-4-retrospective: optional
```

### 4.F — Cập nhật "Khoảng trống đã biết" (`epics.md` cuối file)

```
Thêm mục:
- **Gap Detection Backend (FR7) — Graph Extraction / GraphRAG Engine / Gap Analyst Agent:**
  ✅ Đã tạo Story 4.5, 4.6, 4.7 (correct-course 2026-06-17) để hiện thực hóa hệ con
  ontology học thuật + gap_detection + agent phân tích. Trước đó Epic 4 chỉ phủ FR9 (vẽ),
  thiếu toàn bộ phần sinh dữ liệu khoảng trống. Xem sprint-change-proposal-2026-06-17-gap-detection.md.
```

---

## Section 5 — Implementation Handoff

- **Phân loại:** **Major** (triển khai một hệ con đã kiến trúc nhưng chưa storied; chạm ingestion + Neo4j ontology + LangGraph topology).
- **Người nhận:**
  - **Architect (Winston)** — review nhanh ranh giới Epic 2↔4 (Graph Extraction thuộc ingest), topology Supervisor-Worker, và ngân sách RAM/token trước khi create-story.
  - **PM (John)** — xác nhận FR7 vẫn in-scope MVP (khuyến nghị: có, là giá trị lõi).
  - **Developer (Amelia)** — sau khi chốt, chạy `bmad-create-story` lần lượt cho 4.5 → 4.6 → 4.7.
- **Bước kế tiếp:**
  1. Áp các sửa đổi 4.A–4.F vào `epics.md` + `sprint-status.yaml`.
  2. `bmad-create-story` sinh file story chi tiết tại `implementation-artifacts/4-5-...md`, `4-6-...md`, `4-7-...md`.
  3. `bmad-dev-story` triển khai theo thứ tự phụ thuộc.
- **Success criteria:** gap_detection trả CONTRADICTS/Limitation/cụm cô lập thật; chế độ "Tìm khoảng trống" (4.4) tô viền dựa trên dữ liệu thật; chatbot trả lời mâu thuẫn có nguồn `[N]` (FR7); SM citation accuracy giữ nguyên qua Guardrail.

---

## Phụ lục — Tóm tắt 3 story mới

| Story | Loại | Vai trò | Phụ thuộc | FRs |
|---|---|---|---|---|
| 4.5 | Backend | Trích xuất ontology học thuật (Finding/Limitation/edges) | 2.5, 4.1 | FR7, FR9 |
| 4.6 | Backend | GraphRAG Engine: gap_detection/graph_search/Leiden + endpoint /graph/gaps | 4.1, 4.5 | FR7, FR9 |
| 4.7 | BE+FE | Gap Analyst Agent + Supervisor routing trong LangGraph | 3.6, 4.6 | FR6, FR7 |
