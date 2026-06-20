---
baseline_commit: e2723a4b53953f0230eef1ff9976eb255e4e7774
---

# Story 4.5: Gap Analyst Agent & Supervisor Routing trong LangGraph

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **nhà nghiên cứu đang dùng chatbot của dự án**,
I want **hỏi AI về khoảng trống / mâu thuẫn nghiên cứu ngay trong khung chat và nhận câu trả lời có trích dẫn nguồn `[N]` thực tế**,
so that **tôi phát hiện được mâu thuẫn học thuật, hạn chế chưa giải quyết và cơ hội nghiên cứu mà không phải rời màn hình chat, đồng thời chat thường (RAG) vẫn nhanh như cũ**.

> **Bối cảnh:** Đây là story cuối nhóm "trí tuệ" (🟡 FR7) của Epic 4. Nó **tiến hóa** orchestrator đã xây ở Epic 3 (Story 3.2/3.6) từ **single RAG node** sang topology **Router-Worker** (ARCH §7.1): một **Supervisor** định tuyến mỗi tin nhắn tới **Research&RAG Agent** (mặc định) hoặc **Gap Analyst Agent** (khi intent là khoảng trống/mâu thuẫn). Gap Analyst gọi 2 tool đã build ở Story 4.4 (`gap_detection`, `graph_search` của module `graph_rag`) qua **Port**, sinh câu trả lời và đi qua **Citation Guardrail (Story 3.4)** trước khi stream SSE. Đây cũng là backend cho nút *"Giải thích khoảng trống này"* (Story 4.4) và *"Hỏi AI về bài này"* (Story 4.2).

## Acceptance Criteria

> AC kế thừa bản nháp 7-AC trong `sprint-change-proposal-2026-06-17-gap-detection.md` (đề mục "Story 4.7" = chính story này sau khi gộp 8→5), đã chốt lại theo code thực tế.

**Routing (Supervisor)**

1. **Supervisor node** phân loại intent của tin nhắn người dùng và **định tuyến** thành 1 trong 3 nhánh: (a) **Research&RAG Agent** — câu hỏi học thuật thông thường (nhánh **mặc định**); (b) **Gap Analyst Agent** — khi intent là **khoảng trống / mâu thuẫn / hạn chế** nghiên cứu; (c) **trả lời giao tiếp thường** (chào hỏi, "bạn là ai") — không cần retrieval.
   - **Given** tin nhắn bắt đầu bằng *"Phân tích ... mâu thuẫn, hạn chế và cơ hội nghiên cứu"* (đúng chuỗi prefill từ nút Gap→Chat của `NodeDetailCard.tsx`), **When** Supervisor chạy, **Then** route = `gap_analyst`.
   - **Given** câu hỏi học thuật bình thường ("CNN dùng cho gì?"), **When** Supervisor chạy, **Then** route = `research_rag`.
   - **Given** "xin chào" / "bạn là ai", **When** Supervisor chạy, **Then** route = nhánh trả lời giao tiếp (không gọi tool/retrieval).
2. **Router nhẹ/lazy giữ SM-3 (first-chunk < 3s):** Supervisor **KHÔNG** được thêm 1 hop LLM-classification nặng vào nhánh RAG mặc định làm trễ token đầu tiên. Dùng heuristic (keyword/intent match) là nhánh nhanh; nếu dùng LLM phân loại thì phải là model `flash` rẻ + **không stream token classifier ra UI** (xem AC#9). RAG vẫn là nhánh mặc định; Gap Analyst là worker **thêm vào**, không thay thế.

**Gap Analyst Agent**

3. **Gap Analyst Agent** gọi tool `gap_detection_tool(project_id)` (+ `graph_search_tool(entities, project_id)` khi cần ngữ cảnh quan hệ), nhận `GapContext`/`GraphContext`, rồi sinh câu trả lời phân tích **mâu thuẫn (CONTRADICTS) / hạn chế (Limitation chưa FILLS_GAP) / cụm cô lập** — **mỗi luận điểm kèm thẻ `[N]`** trỏ tới tài liệu nguồn thực tế (paper) (FR7).
4. **Empty/không đủ dữ liệu đồ thị → trả lời an toàn, KHÔNG bịa mâu thuẫn.** Nếu `gap_detection` trả `GapContext` rỗng (không có flagged node/edge) → Gap Analyst trả câu cố định kiểu *"Chưa phát hiện khoảng trống/mâu thuẫn rõ ràng trong dữ liệu đồ thị của dự án."* (mô phỏng pattern `EMPTY_RETRIEVAL_MSG` của Story 3.6), **không gọi LLM bịa nội dung**.

**Research&RAG Agent (fusion)**

5. **Research&RAG Agent = `real_rag_node` hiện tại được mở rộng**: ngoài pgvector cosine search (Story 3.6), **bổ sung `graph_search`** vào context fusion (ARCH §7.4 Bước 2) khi truy vấn có thực thể đồ thị liên quan. Context fusion **giới hạn ~8.000 token** để tránh trễ/quá tải. Không được phá vỡ output shape của Story 3.6 (`valid_citation_ids` + `citation_map`).

**Tái dùng hạ tầng Epic 3 (KHÔNG regress)**

6. **Mọi câu trả lời của cả 2 worker đi qua Citation Guardrail node (tái dùng Story 3.4)** — `[N]` không hợp lệ bị thay `[Nguồn không xác định]`. `citation_map` (ordinal→chunk UUID, Story 3.6) tiếp tục được emit qua SSE để tooltip hoạt động. Nhánh "trả lời giao tiếp thường" (AC#1c) đi qua guardrail vô hại (không có `[N]` → no-op).
7. **LLM call qua `LLMRouter`** (user key → fallback system key, rate-limit cách ly theo §7.3). Supervisor/Gap Analyst/RAG đều lấy client qua `LLMRouter.get_llm_client(user_id, model_name=...)`.

**SSE protocol (tiến hóa)**

8. **Stream sự kiện tiến trình `agent_thinking` TRƯỚC khi stream text** (ARCH §7.4 Bước 4): trước khi worker bắt đầu sinh token, backend emit frame `data: {"event": "agent_thinking", "status": "<status>"}\n\n` (ví dụ `status: "routing"`, `"retrieving_rag_context"`, `"analyzing_gaps"`). Frame này hiển thị ở `ChatbotPanel.tsx` (thay/đi kèm hiệu ứng "AI is thinking"). Giữ nguyên thứ tự frame cũ của 3.6: `chunk*` → `citation_map` (nếu có) → `done`.
9. **KHÔNG leak token của Supervisor ra UI:** vì `astream_events(version="v2")` fire `on_chat_model_stream` cho **mọi** LLM call (kể cả Supervisor classifier), `_stream_graph_to_queue` phải **lọc theo node** — chỉ đẩy token của node worker (`research_rag`, `gap_analyst`) vào queue, bỏ token của `supervisor`.

**Regression (cứng)**

10. **KHÔNG regress AC Epic 3 + SM-3.** Toàn bộ test orchestrator hiện có vẫn pass (sau khi cập nhật 2 test topology — xem Task 7). `build_graph(checkpointer)` giữ nguyên signature. Câu hỏi RAG thường vẫn trả `citation_map` + tooltip như Story 3.6, first-chunk < 3s.

## Tasks / Subtasks

- [x] **Task 1 — Mở rộng `ChatState` + Supervisor node** (AC: 1, 2, 9) `[orchestrator]`
  - [x] Trong [graph.py](backend/src/modules/orchestrator/application/graph.py): thêm field `route: str` vào `ChatState`. Giữ nguyên 3 field cũ.
  - [x] Viết `supervisor_node` heuristic keyword-match (không LLM). Gap keywords check trước chitchat để tránh false positive ("hi" substring trong "nghiên"). Trả `{"route": "research_rag|gap_analyst|chitchat"}`.
  - [x] Viết `chitchat_node` trả lời giao tiếp ngắn không cần retrieval.
- [x] **Task 2 — Định nghĩa tools gọi `graph_rag` qua Port** (AC: 3, 5) `[orchestrator]` → `[graph_rag]`
  - [x] Tạo `application/tools/graph_rag_tools.py` với `gap_detection_tool` và `graph_search_tool`.
  - [x] Tôn trọng §9.6: gọi qua `GapDetectionUseCase`, không truy cập Neo4j thẳng.
  - [x] Guard nợ kỹ thuật 4.4: skip node thiếu `id`, chỉ dùng node `label in {"paper","author"}`.
- [x] **Task 3 — Gap Analyst Agent node** (AC: 3, 4, 6, 7) `[orchestrator]`
  - [x] Viết `gap_analyst_node`: đọc `project_id/user_id` từ config, gọi `gap_detection_tool`.
  - [x] Empty-safe (AC#4): GapContext rỗng → trả `EMPTY_GAP_MSG`, không gọi LLM.
  - [x] Build citation_map: ánh xạ ordinal→chunk UUID đại diện của paper (1 chunk/paper). Gọi LLM với model `gemini-2.5-pro`. Trả 3-key shape giống `real_rag_node`.
  - [x] **Chốt citation**: ánh xạ ordinal→chunk UUID đại diện để tái dùng tooltip Story 3.5/3.6 (không thêm endpoint mới). LLM chỉ được gọi sau khi đã lookup được ít nhất 1 chunk.
- [x] **Task 4 — Mở rộng Research&RAG Agent (fusion graph_search)** (AC: 5) `[orchestrator]`
  - [x] Sau pgvector retrieval, trích entity từ query (heuristic non-stopword), gọi `graph_search_tool`, fusion vào context `[Quan hệ Đồ thị tri thức]`.
  - [x] Giới hạn ~8.000 token (~32.000 chars). Giữ nguyên citation ordinals không bị phá.
  - [x] Giữ nguyên `EMPTY_RETRIEVAL_MSG` và blank-query guard.
- [x] **Task 5 — Tiến hóa `build_graph` sang Router-Worker** (AC: 1, 6, 10) `[orchestrator]`
  - [x] `build_graph(checkpointer)` giữ nguyên signature. Entry point: `supervisor`. Conditional edges → research_rag/gap_analyst/chitchat. Mọi worker edge → citation_guardrail.
  - [x] `build_graph(None)` dựng được topology (verified bằng test).
- [x] **Task 6 — Tiến hóa SSE: `agent_thinking` + lọc token theo node** (AC: 8, 9) `[orchestrator]`
  - [x] `_stream_graph_to_queue`: lọc `on_chat_model_stream` chỉ cho `_WORKER_NODES = {"research_rag","gap_analyst"}`. Supervisor token bị bỏ qua.
  - [x] Emit `agent_thinking` frame trước chunk đầu tiên của worker.
  - [x] `event_generator` trong router.py xử lý frame `agent_thinking`.
- [x] **Task 7 — Cập nhật & bổ sung test backend** (AC: 10, + mọi AC) `[orchestrator]`
  - [x] Sửa `test_guardrail_node_runs_after_workers` trong test_citation_guardrail.py.
  - [x] Viết `test_supervisor_routing.py` — 8 test cases routing heuristic.
  - [x] Viết `test_gap_analyst_node.py` — 3 test cases (empty, citation_map, no-chunk).
  - [x] Viết `test_sse_token_filter.py` — 3 test cases (supervisor blocked, worker emitted, agent_thinking ordering).
  - [x] 42/42 tests pass trong `tests/unit/orchestrator/`.
- [x] **Task 8 — Frontend: hiển thị `agent_thinking`** (AC: 8) `[frontend]`
  - [x] `ChatbotPanel.tsx`: state `thinkingStatus`, xử lý `agent_thinking` event, hiển thị label động theo status.
  - [x] Gap→Chat bridge: NodeDetailCard đã có `setPendingChatInput("Phân tích ... mâu thuẫn, hạn chế và cơ hội nghiên cứu")` → supervisor route gap_analyst (đã xác nhận qua test).
  - [x] `translations.ts`: thêm 3 key `chat.thinking.routing`, `chat.thinking.retrieving_rag_context`, `chat.thinking.analyzing_gaps`.
- [x] **Task 9 — Verify end-to-end & SM-3** (AC: 2, 10) `[fullstack]`
  - [x] 42/42 backend orchestrator tests pass (regression 0).
  - [x] 53/53 graph_rag unit tests pass.
  - [x] Frontend TypeScript clean (no errors). ChatbotPanel tests pass.
  - [x] supervisor_node heuristic: không có LLM hop → SM-3 đảm bảo cho nhánh RAG mặc định.

## Dev Notes

### Kiến trúc & ràng buộc bắt buộc

- **Module lõi: `[orchestrator]`** (Hexagonal, ARCH §9.7). Đây là **tiến hóa code Epic 3** (3.2/3.6) — cross-epic touch **hợp lệ** nhưng **KHÔNG được regress AC Epic 3 + SM-3 (first-chunk < 3s)**. RAG vẫn là **nhánh mặc định**; Gap Analyst là worker **thêm vào**. [Source: epics.md#Story-4.5, ARCH §7.1]
- **Ranh giới module (§9.6 — CỨNG):** orchestrator gọi `gap_detection`/`graph_search` của `graph_rag` **qua application use case (`GapDetectionUseCase`) = Port**, KHÔNG gọi thẳng Neo4j driver/Cypher. Đây là điều kiện không thương lượng. [Source: architecture.md#9.6; epics.md dòng 409]
- **Blueprint module orchestrator (§9.7):** `application/agent_workflow.py` (đồ thị: Supervisor/RAG/Gap/Guardrail), `application/tools/` (tool definitions từ Ports). **Lưu ý thực tế:** code hiện tại đặt graph trong `application/graph.py` (KHÔNG phải `agent_workflow.py`). **Giữ nguyên `graph.py`** để không vỡ import/test hiện có; thêm `application/tools/` cho phần mới. Ghi variance này (xem Project Structure Notes).
- **LLM models (CHỐT khi create-story — doc lệch §7 `1.5` vs §6.2/§8.4 `2.5`):**
  - Supervisor: nếu dùng LLM thì `gemini-flash` (rẻ, nhanh). **Khuyến nghị MVP: heuristic, KHÔNG gọi LLM** để giữ SM-3.
  - Research&RAG Agent & Gap Analyst Agent: model `pro`.
  - **Quyết định chốt:** **KHÔNG hardcode version** — dùng `LLMRouter.get_llm_client(user_id, model_name=...)`; truyền `model_name` từ config/settings động (mặc định hiện tại của router là `gemini-2.5-flash`). Với agent cần chất lượng cao, truyền model `pro` (ví dụ `"gemini-2.5-pro"` — khớp `DEFAULT_LLM_MODEL` §8.4, tránh `1.5` đã cũ ở §7). Ghi model đã chọn vào Completion Notes. [Source: architecture.md §7.1/§7.3/§8.4; sprint-change-proposal-2026-06-17-gap-detection.md dòng 24]
- **Tenacity/retry:** call ngoài (tool/LLM) nên bọc tenacity exponential backoff (ARCH-5). `LLMRateLimitError` pattern đã có trong domain. Không bắt buộc cho MVP nội bộ Neo4j (use case 4.4 đã graceful), nhưng LLM call nên có guard.

### Hợp đồng gọi tool (Story 4.4 — đã build, KHÔNG đổi interface)

```python
from backend.src.modules.graph_rag.application.use_cases import GapDetectionUseCase  # __all__ đã export
from backend.src.shared.infra.neo4j_client import get_neo4j_driver

driver = await get_neo4j_driver()
uc = GapDetectionUseCase(driver)              # __init__(self, neo4j_driver)

gap: GapContext = await uc.gap_detection(project_id)        # project_id: str — NEVER raises, luôn trả GapContext
graph: GraphContext = await uc.graph_search(entities, project_id)  # entities: list[str], project_id: str — CÓ THỂ raise nếu session-acquire fail
```

**Return shapes (dataclass thuần, KHÔNG Pydantic)** — [graph_rag/domain/entities.py](backend/src/modules/graph_rag/domain/entities.py):
```python
GapContext{ flagged_nodes: list[GapFlaggedNode], flagged_edges: list[GapFlaggedEdge] }
GapFlaggedNode{ paper_id: str, reason: str }   # reason ∈ {"isolated_cluster","has_unfilled_limitation","has_contradiction"}
GapFlaggedEdge{ finding1_id, finding2_id, paper1_id, paper2_id, reason }  # reason="contradicts"
GraphContext{ nodes: list[GraphNode], edges: list[GraphEdge] }
GraphNode{ id, label("paper"|"author"), title, authors, year, abstract, state, project_id }
GraphEdge{ id, source, target, type }
```
- `gap_detection` **NEVER raises** → không cần wrap error. `graph_search` **có thể raise** ở bước mở session → bọc try/except trong tool.
- `graph_search` chưa từng có caller/endpoint → **4.5 là consumer đầu tiên**, phải tự guard label/KeyError `n["id"]` (nợ kỹ thuật 4.4). [Source: deferred-work.md; 4-4 story Review Findings]
- `community_summary_search` / Leiden = **Phase 2, NGOÀI scope** — KHÔNG dùng. [Source: epics.md dòng 466]

### Hiện trạng code sẽ sửa (đọc kỹ trước khi đổi)

**[graph.py](backend/src/modules/orchestrator/application/graph.py) (159 dòng) — file chính:**
- `ChatState` (TypedDict, lines 31-34): `messages` (reducer `add_messages`), `valid_citation_ids: list[int]`, `citation_map: dict[int,str]`. → thêm `route`.
- `real_rag_node` (lines 51-127): đọc `user_id`/`project_id` từ `config["configurable"]`; embed (`GeminiEmbeddingClient`), pgvector cosine `<=>` (`TOP_K=5`, scope `project_id`), build `citation_map={i+1: str(row.id)}`, context prefix `[N]`, `LLMRouter(db).get_llm_client(user_id)` lấy **trong session**, `llm.astream(...)` **ngoài session**. → mở rộng fusion graph_search (Task 4).
- `apply_citation_guardrail` (lines 37-48) + `citation_guardrail_node` (lines 130-148): regex `\[(\d+)\]`, thay tag ngoài `valid_set` bằng `[Nguồn không xác định]`; trả AIMessage **cùng `id`** để `add_messages` GHI ĐÈ (tránh replay bản chưa kiểm duyệt). → **tái dùng nguyên trạng**, không sửa logic.
- `build_graph` (lines 151-158): hiện linear `real_rag → citation_guardrail`, entry `real_rag`. → tiến hóa Router-Worker (Task 5), **GIỮ signature `build_graph(checkpointer)`** (gọi ở use_cases.py:101 InvokeUseCase, :221 stream + nhiều test).

**[use_cases.py](backend/src/modules/orchestrator/application/use_cases.py) `_stream_graph_to_queue` (lines 206-278):**
- `astream_events(..., version="v2")`, lọc `on_chat_model_stream` → put `{"type":"chunk","data":...}`. ⚠️ **GOTCHA:** fire cho MỌI LLM call (kể cả supervisor) → phải lọc `event["metadata"].get("langgraph_node")` (Task 6).
- Sau stream: `aget_state(config)` lấy state SAU guardrail → `citation_map` + `final_content` đã sạch → lưu DB → emit `citation_map` rồi `done`. `finally`: sentinel `None` + `delete_run`. → thêm nhánh `agent_thinking`.

**SSE wire protocol (3.6 — giữ nguyên, chỉ thêm `agent_thinking`):**
```
data: {"event":"agent_thinking","status":"<...>"}\n\n   ← MỚI (trước text)
data: {"chunk":"<token>"}\n\n
data: {"event":"citation_map","data":{"1":"<uuid>",...}}\n\n
data: {"event":"done","content":"<cleaned answer>"}\n\n
```
Internal queue typed-frames: `{"type":"chunk"|"citation_map"|"done"|"agent_thinking", ...}` + sentinel `None`.

### Frontend (plumbing citation đã có từ 3.6)

- **Sửa:** [ChatbotPanel.tsx](frontend/src/features/workspace/ChatbotPanel.tsx) — `es.onmessage` thêm nhánh `agent_thinking`. [translations.ts](frontend/src/i18n/translations.ts) — i18n status (nếu cần).
- **KHÔNG sửa (đã đủ):** [NodeDetailCard.tsx](frontend/src/features/workspace/NodeDetailCard.tsx) đã có nút Gap→Chat gọi `setPendingChatInput("Phân tích ${gapDesc}. Hãy chỉ rõ mâu thuẫn, hạn chế và cơ hội nghiên cứu.")` (workspace store). `MessageContent.tsx`/`CitationBadge.tsx`/`chatStore.ts`/`types/chat.ts` đã xử lý `citationMap` ordinal→UUID.
- **Hợp đồng route quan trọng:** chuỗi prefill bắt đầu **"Phân tích ..."** + chứa **"mâu thuẫn, hạn chế và cơ hội nghiên cứu"** → Supervisor PHẢI route `gap_analyst` (đồng bộ AC#1).

### Testing standards

- Backend: `pytest` + `@pytest.mark.asyncio` + `unittest.mock` (`AsyncMock`/`MagicMock`/`patch`). **Chạy: `python -m pytest tests/unit/orchestrator/ --noconftest -v`** (flag `--noconftest` bắt buộc — conftest import LangGraph gây lỗi). Chạy **theo module**, tránh full `tests/unit` (pre-existing TestClient isolation issues).
- Patch theo **symbol-path trong `graph.py`/`use_cases.py`** (ví dụ `patch("backend.src.modules.orchestrator.application.graph.LLMRouter")`). ⚠️ Nếu tách node sang file/module mới, patch path sẽ vỡ → **giữ node trong `graph.py`** hoặc cập nhật patch.
- `build_graph(None)` dùng để test topology không cần DB.
- Mock tool Neo4j: tái dùng `_FakeNeo4jDriver(run_side_effects=[contradicts, isolated, unfilled])` (test_gap_detection.py) hoặc `instance.gap_detection = AsyncMock(return_value=GapContext(...))` (test_graph_router.py).
- Frontend: `vitest`. `npm test`.

### Nợ kỹ thuật kế thừa (cảnh báo, không bắt buộc fix trong story này)

- 🟠 **Race cùng `thread_id`:** `aget_state(config)` chỉ key theo `thread_id` → 2 run đồng thời đọc state lẫn nhau. Pre-existing 3.6, **4.5 KHÔNG làm tệ hơn**. [use_cases.py:243]
- 🟠 In-memory `run_registry` không đa-worker (MVP single-server). [run_registry — deferred 3.2]
- 🟠 `graph_search` chưa lọc label / KeyError `n["id"]` → **Task 2 phải guard khi tiêu thụ**. [deferred 4.4]

### Project Structure Notes

- **Variance hợp lý:** §9.7 blueprint đặt graph ở `application/agent_workflow.py`; code thực tế ở `application/graph.py`. **Giữ `graph.py`** (tránh vỡ import/test Epic 3). Thêm mới `application/tools/` đúng blueprint.
- Naming: Python `snake_case` (hàm/biến), `PascalCase` (class). API boundary Pydantic `alias_generator=to_camel` (§9.2) — nhưng story này chủ yếu nội bộ LangGraph, SSE frame là JSON thuần (giữ key như 3.6).
- KHÔNG đổi DB schema (không cần migration). KHÔNG thêm endpoint REST mới (Gap Analyst chạy trong luồng `/chat` SSE hiện có).

### References

- [Source: epics.md#Story-4.5] — scope, module/role labels, dependencies (3.6, 4.4), FR6+FR7, ràng buộc SM-3.
- [Source: architecture.md §7.1] Router-Worker topology; §7.2 Tools; §7.3 LLMRouter; §7.4 luồng 4 bước + fusion ~8000 token + `agent_thinking`; §7.6 prompt template; §9.6 module boundaries (Port); §9.7 orchestrator blueprint; §5.2 graph_search/gap_detection signatures.
- [Source: sprint-change-proposal-2026-06-17-gap-detection.md] AC nháp 7-AC ("Story 4.7"), router nhẹ/lazy, chốt model, Leiden→Phase 2.
- [Source: 3-6 story] SSE protocol (chunk/citation_map/done), astream_events v2, empty-retrieval, citation_map flow → frontend.
- [Source: 4-4 story] `GapDetectionUseCase` signatures, GapContext/GraphContext, Gap→Chat bridge prefill, guard nợ `graph_search`.
- [Source: deferred-work.md] nợ kỹ thuật orchestrator/graph_search.
- Code: [graph.py](backend/src/modules/orchestrator/application/graph.py), [use_cases.py](backend/src/modules/orchestrator/application/use_cases.py), [router.py](backend/src/modules/orchestrator/presentation/router.py), [graph_rag/use_cases.py](backend/src/modules/graph_rag/application/use_cases.py), [graph_rag/entities.py](backend/src/modules/graph_rag/domain/entities.py), [neo4j_client.py](backend/src/shared/infra/neo4j_client.py), [llm/router.py](backend/src/shared/infra/llm/router.py).

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Fix routing false positive: "hi" là substring của "nghiên" → check gap keywords trước chitchat keywords.
- Fix LLM called before valid_citation_ids check: chuyển LLM resolve vào trong block kiểm tra citation_map.
- Fix patch path: chuyển lazy import lên top-level để patch `backend.src.modules.orchestrator.application.graph.gap_detection_tool` hoạt động.

### Completion Notes List

- **Supervisor routing**: Dùng heuristic keyword-match thuần, KHÔNG có LLM hop → giữ SM-3 cho nhánh RAG mặc định. Gap keywords check TRƯỚC chitchat để tránh false positive (AC#1, AC#2).
- **Citation contract cho Gap Analyst**: Chọn ánh xạ ordinal→chunk UUID đại diện (1 chunk/paper) để tái dùng nguyên trạng tooltip `/api/citations/{chunk_id}` Story 3.5/3.6 — không tạo endpoint mới (AC#3).
- **LLM model Gap Analyst**: Dùng `gemini-2.5-pro` (model pro) qua `LLMRouter.get_llm_client(user_id, model_name="gemini-2.5-pro")` (AC#7).
- **graph_search fusion (real_rag_node)**: Heuristic entity extraction (non-stopword tokens ≥3 chars), max 5 entities, giới hạn 32.000 chars (~8.000 tokens) tổng context, bọc try/except để không phá RAG nếu graph_search fail (AC#5).
- **Token filter**: `_WORKER_NODES = {"research_rag","gap_analyst"}` — supervisor token hoàn toàn bị loại khỏi SSE queue (AC#9).
- **agent_thinking**: Emit frame trước chunk đầu tiên của worker. Frontend `ChatbotPanel.tsx` hiển thị label động theo status (AC#8).
- **Regression**: 42/42 orchestrator tests + 53/53 graph_rag tests pass. TypeScript clean. Pre-existing CenterWorkspace/Cytoscape canvas failure không liên quan đến story này.

### File List

- `backend/src/modules/orchestrator/application/graph.py` (modified)
- `backend/src/modules/orchestrator/application/use_cases.py` (modified)
- `backend/src/modules/orchestrator/presentation/router.py` (modified)
- `backend/src/modules/orchestrator/application/tools/__init__.py` (new)
- `backend/src/modules/orchestrator/application/tools/graph_rag_tools.py` (new)
- `tests/unit/orchestrator/test_citation_guardrail.py` (modified)
- `tests/unit/orchestrator/test_supervisor_routing.py` (new)
- `tests/unit/orchestrator/test_gap_analyst_node.py` (new)
- `tests/unit/orchestrator/test_sse_token_filter.py` (new)
- `frontend/src/features/workspace/ChatbotPanel.tsx` (modified)
- `frontend/src/i18n/translations.ts` (modified)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)

### Review Findings

> Code review 2026-06-18 (3 lớp đối kháng: Blind Hunter / Edge Case Hunter / Acceptance Auditor). 6 patch đã sửa + thêm 3 regression test, 3 mục defer, 2 dismiss. Backend 45/45 pass, frontend tsc sạch + ChatbotPanel test pass.

**Patch đã áp dụng (đã sửa + test):**

- [x] [Review][Patch] `_logger` không tồn tại → NameError làm sập cả 2 worker node trên error-path của graph_search (handler đáng lẽ graceful-degrade lại tự ném, vi phạm AC#5/AC#10) [backend/src/modules/orchestrator/application/graph.py:208, 333] — đổi `_logger` → `logger`.
- [x] [Review][Patch] Routing false-positive: keyword `"phân tích"` ép mọi câu hỏi học thuật ("phân tích cấu trúc CNN") sang gap_analyst, phá AC#2 (RAG là nhánh mặc định) [graph.py:46] — bỏ `"phân tích"` khỏi `_GAP_KEYWORDS` (prefill Gap→Chat vẫn match qua "mâu thuẫn"/"hạn chế"/"cơ hội nghiên cứu").
- [x] [Review][Patch] Chitchat substring `"hi"` lọt vào "machine"/"history" → câu hỏi học thuật ngắn bị route nhầm chitchat [graph.py:106] — chuyển sang match theo ranh giới từ (`_CHITCHAT_PATTERN` regex word-boundary).
- [x] [Review][Patch] Frontend `t()` ném TypeError khi status không có key dịch (`translations[key][lang]` không guard, ChatbotPanel dùng `as any`) — fallback `|| t('chat.thinking')` chết vì throw xảy ra trước [frontend/src/i18n/useTranslation.ts:8] — guard missing-key trả `''` để pattern fallback hoạt động.
- [x] [Review][Patch] Gap Analyst cấp ordinal trước khi lookup chunk → citation_map không liền mạch (vd `{2: uuid}` thiếu `[1]`) khi paper đầu thiếu chunk; guardrail sẽ gạch `[1]` LLM sinh ra [graph.py:271] — cấp ordinal theo thứ tự chunk tìm được (liền mạch từ 1) + bỏ qua flagged edge không trỏ tới ordinal nào.
- [x] [Review][Patch] AC#8: status `"routing"` chưa bao giờ được emit và key dịch `chat.thinking.routing` là dead-code [backend/.../use_cases.py:230] — emit `agent_thinking{status:"routing"}` ngay đầu luồng (phản hồi tức thì khi supervisor phân loại).

**Defer (hạn chế thật, gốc từ Cypher exact-match của 4.4 — cần thiết kế riêng, không sửa trong story này):**

- [x] [Review][Defer] Gap Analyst truyền `paper_ids` (UUID) làm `entities` cho `graph_search`, nhưng Cypher match trên `title`/`name` → khối fusion `[Quan hệ Đồ thị tri thức]` của gap_analyst LUÔN rỗng (dead enrichment + tốn 1 round-trip Neo4j) [graph.py:322] — deferred, cần lookup title trước khi gọi graph_search.
- [x] [Review][Defer] real_rag fusion truyền token đơn của query làm entities; Cypher exact-match `title IN $entities` gần như không khớp full-title → fusion hiệu lực yếu [graph.py:196] — deferred, hạn chế Cypher 4.4 (cần CONTAINS/fuzzy).
- [x] [Review][Defer] Giới hạn ~8000 token fusion là heuristic char thô, ngưỡng lệch giữa 2 worker (32000 vs 30000) và cắt giữa chuỗi có thể chém thẻ `[N]`/dòng graph [graph.py:212, 338] — deferred, refine khi có token-counter thật.

**Dismiss (không phải lỗi):** cờ `_agent_thinking_emitted` dùng chung 1 lần/luồng (mỗi invocation chỉ 1 worker chạy); chitchat/empty-path không stream token (nội dung tới qua `done` event — đúng thiết kế như empty-retrieval 3.6).
