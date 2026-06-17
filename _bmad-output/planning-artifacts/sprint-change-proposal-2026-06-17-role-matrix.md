# Sprint Change Proposal — Làm rõ Ranh giới Vai trò 3 Tầng (Module ↔ Epic ↔ Story)

- **Ngày:** 2026-06-17
- **Người đề xuất:** Dat (qua correct-course)
- **Phạm vi tập trung:** Epic 4 (Bản đồ Tri thức & Phân tích Đồ thị) — chạm Epic 2, Epic 3
- **Phân loại thay đổi:** **Moderate** — *realignment/clarification tài liệu* (KHÔNG replan, KHÔNG đổi FR, KHÔNG đổi MVP scope, KHÔNG rework code đã done)
- **Định tuyến:** PO / DEV (đồng bộ backlog + nhãn module trên story)

---

## 1. Tóm tắt Vấn đề (Issue Summary)

Sau nhiều lần gộp/tách story (correct-course 2026-06-17, gộp Epic 4 từ 8→5 story), **ranh giới vai trò giữa Module ↔ Epic ↔ Story bị mờ và chồng lấn**, đặc biệt ở Epic 4. AI ngữ cảnh phát hiện các điểm nhức nhối:

1. **Producer vs Consumer của `sync_outbox`:** chưa có producer tạo Paper node — `PAPER_UPSERTED` nên thuộc Story 2.5 (ingestion) hay 4.1 (graph sync)?
2. **Ranh giới Epic 2 ↔ Epic 4:** Graph Extraction (4.3) là "Giai đoạn 2" của pipeline ingest (Epic 2, §6.2) nhưng đặt ở Epic 4.
3. **Story 4.1 gánh quá nhiều vai** (Neo4j infra + producer + consumer + GC).
4. **Ontology (Finding/Limitation/edges)** trải trên 4.1 (sync) và 4.3 (extract) — ai định nghĩa schema, ai ghi, ai MERGE.
5. **Tiến hóa orchestrator** (single RAG node 3.2/3.6 → Supervisor-Worker 4.5) chạm lại Epic 3.
6. Cần đối chiếu mỗi epic/story với **7 module Hexagonal** (§9.4).

**Chẩn đoán gốc:** Vấn đề **không phải kiến trúc sai**, mà là **3 trục bị trộn khi đọc tài liệu**. Story theo pattern vertical-slice của dự án **được phép xuyên nhiều module** — điều thiếu không phải "tách story" mà là **nhãn module trên từng task** + **một ma trận trách nhiệm chính thức**. Do đó đây là thay đổi mức tài liệu, không phải replan.

---

## 2. Phân tích Tác động (Impact Analysis)

### Nguyên tắc 3 trục (chốt)
| Trục | Định nghĩa | Tính chất |
|---|---|---|
| **Module** (§9.4) | *Nơi code sống* — bounded context Hexagonal | Cố định, 7 module |
| **Epic** | *Chủ đề giá trị / nhóm FR* | Nhóm theo value — **KHÔNG buộc 1:1 với module** |
| **Story** | *Lát cắt thực thi (vertical slice)* | **Được phép xuyên nhiều module**, miễn mỗi *task* khai báo `[module]` và tôn trọng §9.6 |

### Ranh giới bất biến (§9.6 — không thay đổi, chỉ làm rõ)
- **`ingestion` = PRODUCER** duy nhất ghi `sync_outbox` (gồm cả Stage-2 Graph Extraction §6.2).
- **`graph_rag` / `simple_rag` = CONSUMER** (worker đọc `sync_outbox` → Neo4j / pgvector).

### Tác động theo artifact
- **epics.md:** thêm 1 section "Ma trận Trách nhiệm 3 Tầng"; gắn nhãn `[module]·role` cho story xuyên-module (4.1, 4.3, 4.5); làm rõ chủ sở hữu ontology.
- **architecture.md §9.6:** thêm 1 khối làm rõ producer gồm Stage-2 + bảng sự kiện sync_outbox + nguyên tắc 3 trục (KHÔNG viết lại §5/§6/§7).
- **sprint-status.yaml:** cập nhật comment Epic 4 trỏ tới proposal này; **status không đổi** (4.1 vẫn ready-for-dev).
- **Story 4.1:** chỉnh nhẹ — gắn nhãn module/role cho task; làm rõ 4.1 **KHÔNG** tạo constraints ontology (4.3 làm); xác nhận producer là retrofit `[ingestion]` của 2.5. **Không tách, không đổi AC nghiệp vụ.**
- **Code:** **0 rework.** Story đã done (2.5/3.6) không bị đụng; producer code vốn đã được 4.1 đặt đúng trong `worker.py` (module ingestion).

---

## 3. Phán quyết theo 6 Điểm Nhức nhối (Recommended Approach)

| # | Điểm | Phán quyết (đã được Dat chốt 2026-06-17) |
|---|---|---|
| 1 | Chủ sở hữu `PAPER_UPSERTED` | **Chủ = module `ingestion`** (đáng lẽ thuộc 2.5). 2.5 done & thiếu → **4.1 retrofit**, code đặt đúng trong `ingestion` (`worker.py`), gắn nhãn "[ingestion] vá nợ 2.5". **Giữ ở 4.1**, không tạo story 2.8. |
| 2 | Stage-2 Extraction (4.3) | **Code = module `ingestion`** (mở rộng worker 2.5, là Stage-2 §6.2, vai PRODUCER ontology). `graph_rag` chỉ CONSUME. Epic 4 **giữ 4.3** (value = FR7), gắn nhãn `[ingestion]`. |
| 3 | 4.1 ôm quá nhiều | **GIỮ nguyên** (mạch lạc cùng Neo4j driver + write-path; GC ride-along; tách lại mâu thuẫn quyết định gộp 8→5). Sửa = **gắn nhãn module/role từng task**. |
| 4 | Ontology trải 4.1 ↔ 4.3 | **Tách bạch chủ sở hữu** (bảng dưới). 4.1 = base + khung dispatch mở-rộng-được; 4.3 = constraints ontology + produce + handler MERGE. |
| 5 | Orchestrator 3.x → 4.5 | orchestrator là module **Epic 3**; 4.5 **tiến hóa** nó (cross-epic touch hợp lệ). Ràng buộc: RAG = nhánh mặc định, Gap Analyst = worker thêm, **không regress AC Epic 3 + SM-3 (first-chunk < 3s)**. |
| 6 | Map 7 module | → Ma trận §4. |

---

## 4. Ma trận Trách nhiệm 3 Tầng (Detailed Change — sẽ nhúng vào epics.md)

| Module (§9.4) | Vai trò chính | Epic chính | Story | FR / ARCH |
|---|---|---|---|---|
| `identity` | Auth, JWT, users, RBAC | E1 | 1.1✅ 1.2✅ 1.3✅(BE auth) | FR1 |
| `workspace` | Projects, settings động, **chủ ORM `sync_outbox` + `projects`** | E1, E5 | 1.4✅ 1.5✅ 1.6✅; 2.6✅; 5.3 | FR2, FR11, FR12 |
| `ingestion` | **PRODUCER** sync_outbox; pipeline nạp (write-heavy), Stage-1+Stage-2 §6.2 | E2 (+E4) | 2.2–2.5✅ 2.7✅; **4.1·Producer**; **4.3** | FR3,4,5,16; FR7(extract) |
| `simple_rag` | Vector search read (pgvector), `vector_search` | E3 | 3.6✅ | FR6, NFR3 |
| `graph_rag` | **CONSUMER** sync→Neo4j; `graph_search`/`gap_detection`; GC | E4 | **4.1·Infra+Consumer+GC**; 4.2(BE); 4.4(Engine) | FR7, FR9, ARCH-2, ARCH-8 |
| `orchestrator` | LangGraph, SSE, Supervisor/RAG/Gap agents, Citation Guardrail | E3 (+E4) | 3.1–3.4✅ 3.6✅; **4.5** | FR6,8,10,15; FR7(chat) |
| `shared` | Shared Kernel: LLMRouter, `neo4j_client`, `redis_client` | cross | 2.1✅; driver ở 4.1 | ARCH-6 |

### Story xuyên-module (đã gắn nhãn task)
- **4.1** = `[shared]` Neo4j driver · `[ingestion]` producer `PAPER_UPSERTED` (vá nợ 2.5) · `[graph_rag]` consumer worker + GC · `[workspace]` migration `sync_outbox`/`projects` (+`[ingestion]` migration `papers.deleted_at`).
- **4.3** = `[ingestion]` Stage-2 extraction (produce ontology event) · `[graph_rag]` constraints ontology + handler MERGE đăng ký vào dispatch map của 4.1.
- **4.5** = `[orchestrator]` tiến hóa graph LangGraph (chạm code Epic 3) · gọi tool `[graph_rag]` (gap_detection/graph_search).

### Chủ sở hữu Ontology (gỡ chồng lấn 4.1 ↔ 4.3)
| Khía cạnh | Chủ | Story |
|---|---|---|
| Schema base (Paper/Author/Project) + Unique Constraints base | `graph_rag` | **4.1** |
| Schema ontology (Finding/Limitation/Method/Dataset/Topic/Problem + edges CONTRADICTS/SUPPORTS/HAS_LIMITATION/FILLS_GAP) + constraints ontology | `graph_rag` | **4.3** (KHÔNG phải 4.1) |
| Trích xuất & PRODUCE ontology event vào `sync_outbox` | `ingestion` | **4.3** |
| MERGE ontology vào Neo4j (consume) | `graph_rag` handler | **4.3** (đăng ký vào dispatch map khung-mở-rộng của 4.1) |
| Khung dispatch map mở-rộng-được (forward-compat) | `graph_rag` | **4.1** |

---

## 5. Tác động lên Story 4.1 (cần sửa gì)

Chỉ chỉnh nhẹ (KHÔNG đổi AC nghiệp vụ, KHÔNG tách, status giữ `ready-for-dev`):
1. Phần **Bối cảnh & Phạm vi:** thêm khối "Nhãn module/role theo task" làm rõ 4.1 xuyên 4 module.
2. **AC#4 / Dev Notes:** ghi rõ 4.1 tạo **constraints base** (Paper/Author/Project); **constraints ontology do 4.3 tạo**, không phải 4.1.
3. **AC#8 / Task 3:** xác nhận producer `PAPER_UPSERTED` là **retrofit `[ingestion]`** của Story 2.5 (code đặt trong `worker.py` của module ingestion — đúng §9.6), không phải logic "thuộc về" graph_rag.
4. Thêm tham chiếu proposal này vào References.

---

## 6. Handoff & Tiêu chí Thành công

- **Phân loại:** Moderate → **PO/DEV**.
- **Deliverables:** (a) proposal này; (b) epics.md có ma trận + nhãn; (c) architecture.md §9.6 có khối làm rõ; (d) sprint-status comment cập nhật; (e) story 4.1 gắn nhãn.
- **Tiêu chí thành công:**
  - Mọi story Epic 4 đọc được câu trả lời "code của task này thuộc module nào" trong ≤ 5 giây.
  - Dev triển khai 4.1 biết rõ: tạo base constraints (không tạo ontology), producer là retrofit ingestion, GC là ride-along.
  - Không story nào vi phạm §9.6 (không gọi thẳng infra module khác).
  - 0 thay đổi FR, 0 rework code đã done.
