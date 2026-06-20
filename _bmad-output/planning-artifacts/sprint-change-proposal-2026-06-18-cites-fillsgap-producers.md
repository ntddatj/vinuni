# Sprint Change Proposal — CITES & FILLS_GAP Producers + Tách màu Gap (kích hoạt thật Gap Detection)

- **Ngày:** 2026-06-18
- **Người đề xuất:** Dat
- **Workflow:** correct-course (BMad)
- **Mode review:** Batch
- **Phân loại phạm vi:** **Moderate** — bổ sung **3 story follow-up (4.6/4.7/4.8)** sau khi Epic 4 đã `done`. Hiện thực hóa hai cạnh đồ thị (`[:CITES]`, `[:FILLS_GAP]`) **đã được `architecture.md §5.2` định nghĩa** nhưng chưa story nào sinh ra; cộng một story FE nhỏ tách màu gap. Không viết lại architecture, không rollback, không refactor orchestrator.

---

## Section 1 — Issue Summary

### Vấn đề
Sau khi Epic 4 hoàn tất (4.1–4.5 `done`), kiểm thử trực quan chế độ **"Tìm khoảng trống"** (Story 4.4) cho thấy **gần như mọi Paper đều bị tô vàng**, không phản ánh khoảng trống thật. Truy nguyên trong code phát hiện hai lỗ hổng cấu trúc và một vấn đề UX:

1. **`[:CITES]` không có producer.** Handler `handle_cites` đã được viết sẵn trong `graph_rag/infrastructure/neo4j_adapter.py` (Story 4.1) nhưng **không sự kiện nào ghi `CITES` vào `sync_outbox`** — comment trong code ghi rõ: *"Bảng papers không lưu danh sách references → không có producer sự kiện này."* Hệ quả: **mọi Paper luôn có 0 cạnh CITES** → Query 2 của `gap_detection` (cụm cô lập) gắn cờ **toàn bộ** Paper là `isolated_cluster`.

2. **`[:FILLS_GAP]` không có producer.** Cạnh này chỉ xuất hiện trong **truy vấn** Query 3 của `gap_detection` (Story 4.4) — `WHERE NOT EXISTS { (:Paper)-[:FILLS_GAP]->(l) }` — nhưng **không nơi nào tạo** cạnh này. Hệ quả: **mọi Limitation đều bị coi là "chưa được lấp"** → mọi Paper có Limitation (gần như tất cả, vì Story 4.3 trích 1–5 Limitation/paper) bị gắn cờ `has_unfilled_limitation`.

3. **Hai loại gap khác nhau dùng chung một màu vàng.** Story 4.4 (AC#17, #20) cố tình gộp `isolated_cluster` + `has_unfilled_limitation` → cùng class `gap-isolated` (vàng), và chọn **không sửa GraphLegend** (Dev Notes §GraphLegend → "Option A"). Người dùng không phân biệt được node vàng là "cô lập" hay "limitation chưa giải quyết", và chú giải không ghi màu nào ↔ loại gap nào.

### Bằng chứng từ `architecture.md`
Hai cạnh này **đã nằm trong Graph Schema Phase 1** nhưng chưa được "storied" để **sinh dữ liệu**:

| Thành phần architecture | Vị trí | Đã produce? |
|---|---|---|
| `[:CITES]` (mạng lưới trích dẫn) | §5.2 (Edges) + §3.5 (Bản đồ Tri thức = "mạng lưới trích dẫn") | ❌ Handler có, **producer không** |
| `(:Paper)-[:FILLS_GAP]->(:Limitation)` | §5.2 (Tương tác học thuật) | ❌ Chỉ dùng trong query, **không ai tạo** |

> **Lưu ý quan trọng:** Story 4.3 (role-clarity) ghi `[:FILLS_GAP]` vào danh sách edge ontology mà Stage-2 extraction *nên* sinh, nhưng triển khai thực tế Story 4.3 chỉ sinh `HAS_FINDING/HAS_LIMITATION/CONTRADICTS/SUPPORTS` (intra-paper). `CITES` và `FILLS_GAP` (cross-paper) bị bỏ sót — đây là nợ kỹ thuật được proposal này trả.

### Hệ quả
- **FR7/FR9 chế độ "Tìm khoảng trống" cho tín hiệu nhiễu:** mọi node vàng → "khoảng trống" mất ý nghĩa phân biệt; chỉ node có CONTRADICTS nội-bài (đỏ) là tín hiệu thật.
- **`graph_search` / Gap Analyst Agent (4.5)** thiếu cạnh `CITES` → ngữ cảnh đồ thị nghèo (1-hop neighborhood gần như rỗng quan hệ trích dẫn).
- **UX gây nhầm lẫn:** 2 loại gap khác bản chất nhưng 1 màu + không chú giải.

---

## Section 2 — Impact Analysis

### Epic Impact
- **Epic 4** (`done`): **không mở lại story đã done.** 3 story mới là **follow-up (4.6/4.7/4.8)** nối tiếp Epic 4, đưa Epic 4 từ `done` → `in-progress` trở lại (có story mới chưa làm).
- **Epic 2 (ingestion):** ranh giới — producer `CITES` và `FILLS_GAP` đặt trong module `[ingestion]` (Stage-2, mở rộng worker Story 4.3), nhất quán nguyên tắc role-clarity *"producer sync_outbox = ingestion; consumer = graph_rag"*.
- **Epic 3 (chat):** không chạm. Gap Analyst Agent (4.5) **tự hưởng lợi** khi đồ thị giàu cạnh hơn, không cần sửa.

### Story Impact
| Story | Ảnh hưởng |
|---|---|
| 4.1 (Sync Neo4j) | **Không đổi.** Handler `handle_cites` đã có; thêm handler `FILLS_GAP` mới vào dispatch map (mở-rộng-được, đúng thiết kế 4.1). |
| 4.3 (Graph Extraction) | **Mở rộng:** Stage-2 thêm bước trích `references` (cho 4.6) và là nơi đặt producer; không sửa phần ontology cũ. |
| 4.4 (Gap Detection + tô viền) | **Nay có dữ liệu thật:** `gap_detection` cũ giữ nguyên (3 query không đổi) nhưng kết quả phản ánh đúng vì CITES/FILLS_GAP đã tồn tại. FE tách màu (4.8). |
| 4.5 (Gap Analyst Agent) | **Hưởng lợi gián tiếp:** `graph_search` trả 1-hop neighborhood giàu cạnh CITES hơn → câu trả lời gap chất lượng hơn. Không sửa code 4.5. |

### Artifact Conflicts (cần cập nhật)
- `epics.md`: thêm 3 story 4.6/4.7/4.8; cập nhật bảng "Thứ tự thực thi & ưu tiên" Epic 4; cập nhật dòng tổng số story; cập nhật mục "Khoảng trống đã biết".
- `sprint-status.yaml`: `epic-4` → `in-progress`; thêm `4-6`, `4-7`, `4-8` = backlog.
- `architecture.md`: **không cần đổi** — `[:CITES]`/`[:FILLS_GAP]` đã có ở §5.2; đây là hiện thực hóa.

### Technical Impact
- **Mới (BE):** trích `references` từ Markdown/metadata (Story 4.3 extension); thuật toán **khớp reference → Paper** (DOI exact → fuzzy title/embedding); producer outbox `CITES`; **LLM-judge FILLS_GAP** (cặp Paper×Limitation) + handler `FILLS_GAP`.
- **Mới (FE):** tách class Cytoscape `gap-unfilled` (cam) khỏi `gap-isolated` (xanh); legend gap có điều kiện.
- **NFR / Chi phí (quan trọng — chọn cách LLM-judge):**
  - FILLS_GAP = **N paper × M limitation lời gọi LLM** → chi phí/độ trễ tăng theo bình phương quy mô project. **Bắt buộc:**
    - Chạy **bất đồng bộ** trong worker arq (concurrency_limit=2), **KHÔNG** gắn vào nút "Tìm khoảng trống" (giữ `gap_detection` = Cypher read nhanh, đúng triết lý Story 4.4).
    - **Tiền lọc bằng embedding** trước khi gọi LLM: chỉ judge cặp (Limitation, Paper) có cosine(similarity) ≥ ngưỡng (vd 0.65) → cắt mạnh số lời gọi.
    - Dùng `gemini-1.5-flash` (rẻ) cho judge; cache kết quả theo `(limitation_id, candidate_paper_id)` để không judge lại.
    - Idempotent + scope `project_id`; tôn trọng RAM Neo4j 8GB (ARCH-1), LLM qua LLMRouter (user key → system fallback).

---

## Section 3 — Recommended Approach

**Direct Adjustment** — thêm 3 story follow-up, không rollback, không cắt scope. Giữ nguyên `gap_detection` (Story 4.4) — chỉ "đổ dữ liệu thật" vào.

- **Lý do:** `[:CITES]`/`[:FILLS_GAP]` đã là thiết kế architecture Phase 1; gap detection MVP đã chạy nhưng "đói dữ liệu". Đây là phần triển khai bị bỏ sót, không phải tính năng mới.
- **Hướng thay thế đã cân nhắc & loại bỏ:**
  - *Chạy FILLS_GAP đồng bộ khi bấm nút:* **Loại** — N×M lời gọi LLM sẽ làm nút trễ vài chục giây + tính lại dư thừa mỗi lần bấm; phá triết lý "gap_detection = Cypher read nhanh" của Story 4.4.
  - *FILLS_GAP bằng embedding-only (không LLM):* nhanh/rẻ hơn nhưng **độ chính xác thấp** (similarity ≠ "thực sự giải quyết"). **Dat đã chọn LLM-judge cho chính xác** → giữ embedding làm **tiền lọc**, LLM làm **phán quyết cuối**.
  - *Gộp 3 việc vào 1 story:* Loại — 3 quan tâm tách bạch (CITES cơ học / FILLS_GAP ngữ nghĩa-AI / FE màu), khác độ rủi ro & người làm.
- **Effort:** Trung bình. 4.7 (FILLS_GAP LLM-judge) nặng nhất (chi phí + tiền lọc + cache); 4.6 (CITES matching) trung bình; 4.8 (FE màu) nhỏ.
- **Rủi ro chính:** (a) độ chính xác khớp reference→Paper (false match/miss); (b) chi phí/độ trễ LLM-judge nếu không tiền lọc tốt; (c) false positive FILLS_GAP làm "mất" gap thật (cần ngưỡng thận trọng + log).

### Khuyến nghị thứ tự thực thi
```
4.8 (FE màu — nhỏ, độc lập, giá trị tức thì)
  ↘
4.6 (CITES producer) → 4.7 (FILLS_GAP producer)   ← cùng module ingestion, 4.7 tái dùng tiền-lọc embedding
```
4.8 làm trước được ngay (không phụ thuộc BE). 4.6 trước 4.7 vì cùng động vào Stage-2 extraction và 4.7 nặng hơn.

---

## Section 4 — Detailed Change Proposals

### 4.A — Story mới (thêm vào `epics.md`, sau Story 4.5)

```
### Story 4.6: [Backend] CITES Producer — Trích references & Khớp Paper (mở khóa "cụm cô lập") — ⏳ backlog 🟡

Bổ sung Stage-2 ingestion (mở rộng Story 4.3): trích danh sách references/trích dẫn từ Markdown đã
cấu trúc hóa + metadata, khớp mỗi reference với Paper hiện có trong project (DOI exact → fallback
fuzzy title / embedding), rồi ghi sự kiện CITES {citing_paper_id, cited_paper_id} vào sync_outbox để
Story 4.1 MERGE cạnh [:CITES] vào Neo4j. Mở khóa Query 2 của gap_detection (cụm cô lập) phản ánh thật.

- **Phát sinh:** correct-course 2026-06-18 (kiểm thử Story 4.4 lộ "mọi node vàng"). Hiện thực hóa ARCH §5.2 ([:CITES]) + §3.5 (mạng lưới trích dẫn).
- **🧭 Nhãn module/role:** [ingestion] producer CITES (mở rộng worker Stage-2 §6.2) · [graph_rag] handler handle_cites ĐÃ CÓ (Story 4.1) — chỉ cần producer.
- **Phụ thuộc:** Story 4.1 (handler + sync), Story 4.3 (Stage-2 worker để gắn vào).
- **FRs:** FR7, FR9. (ARCH §5.2.)

**AC nháp (chi tiết hóa khi create-story):**
1. Stage-2 trích references (title + DOI + năm nếu có) từ Markdown/metadata; rỗng → bỏ qua an toàn, không lỗi.
2. Khớp reference → Paper trong CÙNG project: ưu tiên DOI exact; fallback so khớp tiêu đề chuẩn hóa (lowercase/bỏ dấu) + ngưỡng tương đồng (vd cosine title ≥ 0.85). Không khớp → bỏ (không tạo Paper ma).
3. Ghi sync_outbox event CITES {citing_paper_id, cited_paper_id} — idempotent, scope project_id; KHÔNG tự-trích-dẫn (citing ≠ cited).
4. Handler handle_cites (Story 4.1) MERGE [:CITES]; chạy lại không nhân đôi cạnh.
5. Re-ingest / thêm paper mới → cập nhật cạnh CITES tăng dần (forward-compat, không cần backfill toàn bộ nhưng nêu rõ giới hạn nếu không backfill).
6. Tôn trọng worker arq (concurrency_limit=2); log số reference khớp/không-khớp để quan sát chất lượng matching.
```

```
### Story 4.7: [Backend] FILLS_GAP Producer — LLM-judge Limitation↔Paper (mở khóa "limitation chưa giải quyết") — ⏳ backlog 🟡

Worker bất đồng bộ xác định cạnh [:FILLS_GAP]: với mỗi Limitation chưa được lấp trong project, tiền lọc
ứng viên Paper bằng embedding (cosine ≥ ngưỡng), rồi gọi LLM judge (gemini-1.5-flash) "Bài X có giải
quyết hạn chế này của bài Y không?" → nếu CÓ, ghi sync_outbox FILLS_GAP {filler_paper_id, limitation_id}
để Story 4.1 MERGE (:Paper)-[:FILLS_GAP]->(:Limitation). Mở khóa Query 3 của gap_detection phản ánh thật.
CHẠY NGẦM (arq/cron) — KHÔNG đồng bộ với nút "Tìm khoảng trống" (giữ gap_detection = Cypher read nhanh).

- **Phát sinh:** correct-course 2026-06-18. Hiện thực hóa ARCH §5.2 ((:Paper)-[:FILLS_GAP]->(:Limitation)).
- **Quyết định kiến trúc (Dat 2026-06-18):** Chọn LLM-judge (chính xác) thay vì embedding-only; embedding chỉ làm TIỀN LỌC để cắt N×M lời gọi.
- **🧭 Nhãn module/role:** [ingestion] producer FILLS_GAP (worker ngầm) · [graph_rag] handler FILLS_GAP MỚI vào dispatch map của 4.1.
- **Phụ thuộc:** Story 4.1 (sync + thêm handler), Story 4.3 (Limitation/Finding ontology đã tồn tại).
- **FRs:** FR7, FR9. (ARCH §5.2.)

**AC nháp:**
1. Worker quét các Limitation trong project chưa có cạnh [:FILLS_GAP] (idempotent, không judge lại cặp đã quyết).
2. TIỀN LỌC: với mỗi Limitation, chọn top-K Paper ứng viên có cosine(embedding) ≥ ngưỡng (vd 0.65) — KHÔNG judge toàn bộ N×M.
3. LLM judge (gemini-1.5-flash) trên từng cặp (Limitation, Paper ứng viên): trả {fills: bool, lý do ngắn}; prompt yêu cầu "chỉ trả CÓ nếu paper thực sự giải quyết/lấp hạn chế này".
4. fills=true → ghi sync_outbox FILLS_GAP {filler_paper_id, limitation_id}; filler ≠ paper sở hữu limitation đó.
5. Handler FILLS_GAP mới (graph_rag): MATCH Paper + Limitation theo id (scope project_id) → MERGE [:FILLS_GAP]; idempotent.
6. CHẠY NGẦM (arq concurrency_limit=2 / cron sau ingest). KHÔNG nằm trên đường bấm nút gap. Cache theo (limitation_id, candidate_paper_id) tránh gọi lại; LLM qua LLMRouter (user→system fallback), retry/Tenacity khi rate-limit.
7. Ngưỡng thận trọng + log mọi quyết định (judge yes/no + lý do) để chỉnh; empty/ít dữ liệu → an toàn, không bịa cạnh.
```

```
### Story 4.8: [Frontend] Tách màu 3 loại Gap + Chú giải Gap có điều kiện — ⏳ backlog 🟢

Trên Knowledge Map (Story 4.2/4.4), tách màu node theo reason để phân biệt rõ 3 loại khoảng trống:
đỏ = mâu thuẫn (has_contradiction), cam = limitation chưa giải quyết (has_unfilled_limitation),
xanh = cụm cô lập (isolated_cluster). Bổ sung mục chú giải gap vào GraphLegend, chỉ hiển thị khi gap mode ON.

- **Phát sinh:** correct-course 2026-06-18 (gộp 2 reason vào 1 màu vàng gây nhầm — quyết định MVP "Option A" của Story 4.4 nay nâng cấp).
- **🧭 Nhãn module/role:** [frontend] thuần — KnowledgeMapTab CY_STYLE + GraphLegend.
- **Phụ thuộc:** Story 4.4 (gap mode + reason đã có trong response). KHÔNG phụ thuộc 4.6/4.7 (làm trước được ngay).
- **FRs:** FR9.

**AC nháp:**
1. Map reason → 3 class: has_contradiction → gap-contradiction (đỏ #EF4444, giữ); has_unfilled_limitation → gap-unfilled (cam #F59E0B, MỚI); isolated_cluster → gap-isolated (xanh #3B82F6, đổi nghĩa: chỉ còn cô lập).
2. Thêm selector node.gap-unfilled vào CY_STYLE; animation pulsing áp cho cả 3 class.
3. Dedup priority giữ nguyên (contradiction > unfilled > isolated) — màu hiển thị theo reason ưu tiên.
4. GraphLegend: thêm 3 dòng chú giải gap (đỏ/cam/xanh ↔ tên loại), CHỈ render khi gapMode = true; tắt gap mode → ẩn.
5. NodeDetailCard "Giải thích khoảng trống này": prefill khác nhau theo 3 reason (đã có ở 4.4, kiểm tra map đủ 3 nhánh).
6. Toggle OFF → removeClass cả 3 + removeStyle border-width (giữ fix review 4.4, không sót inline style).
```

### 4.B — Cập nhật bảng "Thứ tự thực thi & ưu tiên" Epic 4 (`epics.md`)

```
Thêm 3 dòng vào bảng:
| 4.6 CITES Producer (mở khóa cụm cô lập) | 🟡 Trí tuệ (FR7) | 4.1, 4.3 |
| 4.7 FILLS_GAP Producer (LLM-judge, mở khóa unfilled limitation) | 🟡 Trí tuệ (FR7) | 4.1, 4.3 |
| 4.8 Tách màu 3 loại Gap + Legend | 🟢 FE nhỏ | 4.4 |

Thêm dòng:
> 🏁 **Sau 4.6+4.7+4.8:** Gap detection phản ánh khoảng trống THẬT (CITES/FILLS_GAP đã sinh) + 3 màu phân biệt rõ.
> **Thứ tự follow-up:** 4.8 (FE, song song được) · 4.6 → 4.7 (ingestion). Tham chiếu: sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md.
```

### 4.C — Cập nhật dòng trạng thái tổng (`epics.md` dòng ~155)

```
OLD: Tổng: **28 story** ...gộp còn 5 story 4.1–4.5 (GC gộp vào 4.1)...
NEW: Tổng: **31 story** (+3 story follow-up 4.6/4.7/4.8 — CITES/FILLS_GAP producers + tách màu gap, correct-course 2026-06-18) ...gộp còn 5 story 4.1–4.5 (GC gộp vào 4.1); Epic 4 mở lại in-progress cho 3 story follow-up...
```

### 4.D — `sprint-status.yaml` (khối epic-4)

```
OLD:
  epic-4: in-progress
  4-1-...: done
  4-2-...: done
  4-3-...: done
  4-4-gap-detection-tren-map-graphrag-engine-va-to-vien: done
  4-5-gap-analyst-agent-supervisor-routing-langgraph: done
  epic-4-retrospective: optional
NEW:
  epic-4: in-progress
  4-1-...: done
  4-2-...: done
  4-3-...: done
  4-4-gap-detection-tren-map-graphrag-engine-va-to-vien: done
  4-5-gap-analyst-agent-supervisor-routing-langgraph: done
  # follow-up correct-course 2026-06-18: kích hoạt CITES/FILLS_GAP thật + tách màu gap
  4-6-cites-producer-trich-references-khop-paper: backlog
  4-7-fills-gap-producer-llm-judge-limitation-paper: backlog
  4-8-tach-mau-3-loai-gap-chu-giai-legend: backlog
  epic-4-retrospective: optional
```

### 4.E — Cập nhật "Khoảng trống đã biết" (`epics.md` cuối file)

```
Thêm mục:
- **CITES & FILLS_GAP Producers (FR7) — kích hoạt thật Gap Detection:** ✅ Đã tạo Story 4.6 (CITES
  producer), 4.7 (FILLS_GAP LLM-judge), 4.8 (tách màu 3 loại gap) (correct-course 2026-06-18). Trước
  đó Story 4.4 chạy gap_detection nhưng [:CITES] và [:FILLS_GAP] (đã có trong ARCH §5.2) chưa có producer
  → mọi Paper bị cờ cô lập + unfilled (nhiễu). Xem sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md.
```

---

## Section 5 — Implementation Handoff

- **Phân loại:** **Moderate** — bổ sung 3 story follow-up, đụng producer ingestion + handler graph_rag + FE; không viết lại architecture, không refactor orchestrator.
- **Người nhận:**
  - **Architect (Winston)** — review nhanh: (a) đặt producer CITES/FILLS_GAP ở `[ingestion]` đúng role-clarity; (b) chốt ngân sách chi phí/độ trễ LLM-judge + ngưỡng tiền-lọc embedding cho Story 4.7; (c) chiến lược backfill (re-judge toàn project hay chỉ incremental).
  - **Developer (Amelia)** — sau khi chốt, chạy `bmad-create-story` theo thứ tự **4.8 → 4.6 → 4.7**.
- **Bước kế tiếp:**
  1. Áp các sửa đổi 4.A–4.E vào `epics.md` + `sprint-status.yaml`.
  2. `bmad-create-story` sinh file story chi tiết tại `implementation-artifacts/4-6-...md`, `4-7-...md`, `4-8-...md`.
  3. `bmad-dev-story` triển khai: 4.8 (nhanh, demo màu ngay) → 4.6 → 4.7.
- **Success criteria:**
  - Sau 4.6: Paper có trích dẫn lẫn nhau → **không** còn bị cờ cô lập sai; chỉ paper thực sự không nối ai mới xanh.
  - Sau 4.7: Limitation đã được paper khác giải quyết → **không** còn cờ unfilled; chỉ gap thật còn cam.
  - Sau 4.8: 3 màu rõ ràng + chú giải gap hiện khi bật gap mode; user phân biệt được 3 loại khoảng trống.
  - `gap_detection` (Story 4.4) vẫn là Cypher read nhanh — LLM-judge chạy ngầm, không trên đường bấm nút.

---

## Phụ lục — Tóm tắt 3 story follow-up

| Story | Loại | Vai trò | Phụ thuộc | FRs |
|---|---|---|---|---|
| 4.6 | Backend | CITES producer: trích references + khớp Paper + emit outbox (mở khóa "cụm cô lập") | 4.1, 4.3 | FR7, FR9 |
| 4.7 | Backend | FILLS_GAP producer: LLM-judge Limitation↔Paper (embedding tiền lọc), chạy ngầm (mở khóa "unfilled limitation") | 4.1, 4.3 | FR7, FR9 |
| 4.8 | Frontend | Tách màu 3 loại gap (đỏ/cam/xanh) + chú giải gap có điều kiện | 4.4 | FR9 |
