---
baseline_commit: 1b048c8
---

# Story 4.2: [BE+FE] Knowledge Map UI — Đọc & Vẽ Đồ thị Cytoscape.js + Node Detail Card

Status: done

## Story

As a **nhà nghiên cứu dùng C2-App-053**,
I want **xem bản đồ tri thức tương tác Cytoscape.js trong tab "Bản đồ Tri thức" với đồ thị paper/tác giả, Node Detail Card, chú giải màu sắc, và chỉ báo đồng bộ, đồng thời có thể hỏi AI về bài báo ngay từ bản đồ**,
so that **tôi hiểu trực quan mạng lưới tài liệu, trạng thái nạp của từng paper, và có thể đặt câu hỏi liên kết đồ thị ↔ chat trong một luồng liền mạch (FR9 + Co-existent Redundant Pathways)**.

## Bối cảnh & Phạm vi

Story này là **[BE+FE] vertical slice** xuyên 2 module chính: `[graph_rag]` (BE endpoint đọc Neo4j) và `[workspace/frontend]` (FE canvas). Là story cốt lõi 🟢 ngay sau Story 4.1 (đã done ✅), lần đầu đưa dữ liệu Neo4j lên màn hình.

**Dữ liệu đã sẵn sàng từ Story 4.1:**
- `neo4j_client.py` singleton tại `backend/src/shared/infra/neo4j_client.py`
- Nodes `Paper` (có property `state="full_text"` hoặc `"metadata_only"`) + `Author` + `[:AUTHORED_BY]` edges trong Neo4j
- Handler `[:CITES]` có sẵn (không có producer ở MVP, chưa có dữ liệu thật)
- Mọi node mang `project_id` để IDOR scoping
- Module `backend/src/modules/graph_rag/` đã tồn tại (Hexagonal) — **chưa có** `presentation/` folder, story này tạo mới

**Ranh giới rõ ràng:**
- ✅ TRONG phạm vi: BE endpoint đọc đồ thị (GET graph, GET expand, GET sync-status) + FE Cytoscape canvas + Node Detail Card + Legend + Sync Indicator + "Hỏi AI về bài này" bridge
- ❌ NGOÀI phạm vi: Gap detection / tô viền khoảng trống → Story 4.4; Ontology edges (CONTRADICTS/SUPPORTS) → Story 4.3+4.4; Leiden/community → Phase 2

### 🧭 Nhãn module/role theo task

| Task | Module | Vai trò |
|---|---|---|
| BE endpoints đọc đồ thị (router, schemas, use_cases) | `[graph_rag]` | READ — API Provider |
| Sync-status endpoint (query sync_outbox) | `[graph_rag]` | READ — `sync_outbox` là shared outbox, graph_rag consumer đã đọc nó |
| FE KnowledgeMapTab, NodeDetailCard, Legend | `[workspace]` FE feature folder | UI Consumer |
| FE API client `graph.ts`, types `graph.ts` | `[workspace]` FE api/ types/ | FE Infrastructure |
| CenterWorkspace.tsx (cắm KnowledgeMapTab) | `[workspace]` FE | UPDATE nhẹ |
| chatStore (thêm pendingChatInput) | `[workspace]` FE store | UPDATE — Graph→Chat bridge |

## Acceptance Criteria

### A. Backend — Endpoint đọc đồ thị

1. `GET /api/projects/{project_id}/graph` — trả về toàn bộ đồ thị ban đầu, giới hạn **150 nodes / 300 edges** kèm cờ `has_more: bool`. JWT + owner scoping (401 nếu chưa đăng nhập, 404 nếu project không thuộc user). Response chỉ bao gồm nodes và edges **không mang nhãn `:Deleted`**. Cypher scope `WHERE n.project_id = $project_id AND NOT n:Deleted`.

2. `GET /api/projects/{project_id}/graph/nodes/{node_id}/expand` — trả về **≤ 20 node lân cận 1-hop mới** (chưa có trong đồ thị client đang hiển thị, xác định qua query param `?existing_ids=id1,id2,...`) kèm edges kết nối chúng. Endpoint chỉ trả `Paper`/`Author` nodes (không `:Deleted`), scope `project_id`.

3. `GET /api/projects/{project_id}/graph/sync-status` — trả về `{"syncing": bool}`. `syncing=true` khi `COUNT(*) FROM sync_outbox WHERE project_id=? AND processed=false AND dead_lettered=false > 0`. JWT + owner scoping. Dùng Postgres session factory (không qua Neo4j).

4. Tất cả 3 endpoints đăng ký vào `main.py` qua `app.include_router(graph_router, prefix="/api")`. Prefix router là `/projects` (pattern giống workspace router).

5. Response schema JSON chuẩn:
   ```json
   {
     "nodes": [
       {"id": "...", "label": "paper|author", "title": "...", "authors": ["..."], "year": 2024,
        "abstract": "...", "state": "full_text|metadata_only", "project_id": "..."}
     ],
     "edges": [
       {"id": "...", "source": "...", "target": "...", "type": "AUTHORED_BY|CITES|..."}
     ],
     "has_more": false
   }
   ```

### B. Frontend — Cytoscape.js Canvas

6. Cài `cytoscape` + `cytoscape-fcose` (hoặc `cytoscape-cola`) + `@types/cytoscape` vào `frontend/package.json`. Layout mặc định là `fcose` (heuristic force-directed nhanh, bundle nhỏ hơn cola).

7. Component `KnowledgeMapTab.tsx` tại `frontend/src/features/workspace/` render canvas Cytoscape.js đầy đủ chiều cao còn lại của workspace (dùng `height: 100%` / `flex: 1`). Canvas nền `var(--surface-base)`.

8. **Phân biệt node theo `state`** (DESIGN §5):
   - `state="full_text"` → node tròn, viền đậm xanh lá `var(--state-success)` (#10B981)
   - `state="metadata_only"` → node tròn, viền nét đứt cam `var(--state-warning)` (#F59E0B)
   - Node `Author` → hình thoi nhỏ hơn, màu tím `var(--accent-violet)` (#8B5CF6), luôn hiển thị nếu toggle author bật

9. **Cạnh theo `type`** (DESIGN §5):
   - `AUTHORED_BY` → nét đứt màu tím `var(--accent-violet)`, không mũi tên
   - `CITES` → nét liền màu xanh `var(--accent-blue)`, có mũi tên định hướng (target-arrow)

10. **Zoom/pan** đầy đủ (built-in Cytoscape). Có nút reset view (fit-to-screen) ở góc trên phải canvas.

11. **Toggle ẩn/hiện Author nodes**: checkbox/toggle nhỏ trong UI, khi tắt ẩn mọi node Author + cạnh AUTHORED_BY (Cytoscape `cy.elements('[label="author"]').hide()`).

12. **Lazy expand**: Khi click node Paper đang hiển thị (không phải để mở Node Detail Card — cần phân biệt: single-click → Detail Card, double-click hoặc nút "Mở rộng" trong Card → expand). Gọi `GET .../expand?existing_ids=...`, nhận nodes/edges mới, **thêm vào Cytoscape** dùng `cy.add(...)` rồi chạy layout `fcose` **chỉ trên nodes mới** (fix vị trí node cũ bằng `position` constraint của fcose để không xáo trộn). Nếu `has_more=false` khi load initial → không cần nút expand.

### C. Node Detail Card

13. Single-click một node Paper → **Node Detail Card** trượt ra từ góc trên phải canvas (absolute positioned trong container canvas, `position: absolute; top: 0; right: 0`). Nền `var(--surface-raised)`, bo góc `var(--rounded-lg)` (8px), viền `var(--border-hairline)`, shadow nhẹ. Hiển thị: tiêu đề (16px/600), tác giả (13px/400), năm (11px/400 ink-secondary), abstract (13px/400, max 5 dòng với `line-clamp`).

14. Card có nút **"✕"** (đóng card). Click vùng canvas trống → đóng card.

15. Card có nút **"Hỏi AI về bài này"** (màu `var(--accent-blue)`, text trắng). Click → set `pendingChatInput` trong workspaceStore thành `"Hãy phân tích bài báo: {title}"`, sau đó `ChatbotPanel` dọn và prefill input, focus textarea. Không auto-send — user quyết định gửi.

16. Single-click node Author → Card nhỏ hiển thị tên tác giả + danh sách các paper của tác giả đó trong project (từ đồ thị đang có). Không cần nút "Hỏi AI".

### D. Legend & Sync Indicator

17. **Legend** nhỏ cố định góc dưới trái canvas (absolute positioned), hiển thị bảng màu: node full-text (xanh đậm), node metadata-only (nét đứt cam), cạnh CITES (xanh mũi tên), cạnh AUTHORED_BY (tím nét đứt), node Author (tím hình thoi). Background mờ `rgba(var(--surface-raised-rgb), 0.9)`.

18. **Sync Indicator**: poll `GET .../graph/sync-status` mỗi **10 giây** khi tab Graph đang active (`activeTab === 'graph'`). Nếu `syncing=true` → hiển thị badge nhỏ góc trên trái canvas "⟳ Đồ thị đang cập nhật…" màu `var(--state-warning)`. Badge biến mất khi `syncing=false`. Không block render canvas.

19. Khi `activeProjectId` thay đổi (user chọn project khác) → clear graph + re-fetch.

### E. Graph → Chat Bridge (workspaceStore update)

20. Thêm `pendingChatInput: string | null` và `setPendingChatInput(msg: string | null)` vào `workspaceStore.ts`. `ChatbotPanel.tsx` thêm `useEffect` watch `pendingChatInput`: khi có giá trị → set vào `inputValue` state của Panel + focus textarea + gọi `setPendingChatInput(null)` (clear sau khi consume).

### F. CenterWorkspace Update

21. `CenterWorkspace.tsx` thay placeholder `<p>{t('tab.graph')}</p>` thành `<KnowledgeMapTab projectId={activeProjectId} />`. Import lazy nếu muốn tách bundle (`React.lazy`).

### G. Tests

22. Unit test BE (pytest, mock Neo4j + DB):
    - `GET .../graph` trả đúng shape `{nodes, edges, has_more}` với mock session trả data
    - `GET .../graph` với `project_id` không thuộc user → 404
    - `GET .../graph/nodes/{id}/expand` lọc đúng `existing_ids`
    - `GET .../graph/sync-status` trả `syncing=true` khi có unprocessed events, `syncing=false` khi không có
    - Tests tại `tests/unit/graph_rag/test_graph_router.py`

23. Unit test FE (vitest + testing-library, pattern dự án hiện có):
    - `KnowledgeMapTab` render với `projectId=null` → hiển thị placeholder "Chọn một dự án"
    - Mock API trả empty graph → canvas render không crash
    - Nút "Hỏi AI về bài này" click → `pendingChatInput` set đúng trong store

## Tasks / Subtasks

- [x] **Task 1 — BE presentation layer `[graph_rag]`** (AC: 1,2,3,4,5)
  - [x] Tạo `backend/src/modules/graph_rag/presentation/` folder với `__init__.py`
  - [x] Tạo `backend/src/modules/graph_rag/presentation/schemas.py`: Pydantic `NodeResponse`, `EdgeResponse`, `GraphResponse`, `SyncStatusResponse`
  - [x] Tạo `backend/src/modules/graph_rag/presentation/router.py`: 3 endpoints (graph, expand, sync-status)
  - [x] Viết `GraphReadUseCase` vào `backend/src/modules/graph_rag/application/use_cases.py` (thêm vào file hiện có — hiện chỉ có re-export `sync_outbox_task`)
  - [x] Tạo/cập nhật `backend/src/modules/graph_rag/domain/entities.py`: `GraphNode`, `GraphEdge`, `GraphData` dataclasses
  - [x] Đăng ký `graph_router` vào `backend/main.py` (thêm `from ... import router as graph_router` + `app.include_router`)
  - [x] Tests `tests/unit/graph_rag/test_graph_router.py`

- [x] **Task 2 — FE dependencies & types** (AC: 6)
  - [x] `npm install cytoscape cytoscape-fcose` + `npm install -D @types/cytoscape` trong `frontend/`
  - [x] Tạo `frontend/src/types/graph.ts`: `GraphNode`, `GraphEdge`, `GraphResponse`, `SyncStatus` interfaces

- [x] **Task 3 — FE API client** (AC: 1,2,3)
  - [x] Tạo `frontend/src/api/graph.ts`: `fetchGraph(projectId)`, `expandNode(projectId, nodeId, existingIds)`, `getSyncStatus(projectId)`

- [x] **Task 4 — KnowledgeMapTab canvas** (AC: 7,8,9,10,11,12)
  - [x] Tạo `frontend/src/features/workspace/KnowledgeMapTab.tsx` + `KnowledgeMapTab.module.css`
  - [x] Init Cytoscape trong `useEffect` + ref, style nodes/edges theo design tokens
  - [x] Toggle Author nodes (checkbox)
  - [x] Double-click/expand button gọi `expandNode` + thêm nodes vào cy + layout gia tăng
  - [x] Reset view button

- [x] **Task 5 — NodeDetailCard** (AC: 13,14,15,16)
  - [x] Tạo `frontend/src/features/workspace/NodeDetailCard.tsx` + CSS module
  - [x] Paper card: title/authors/year/abstract + nút "Hỏi AI" + nút đóng
  - [x] Author card: tên + list papers
  - [x] Single-click node → show card; click canvas empty → close

- [x] **Task 6 — Legend** (AC: 17)
  - [x] Tạo `frontend/src/features/workspace/GraphLegend.tsx` + CSS module
  - [x] Fixed position góc dưới trái, bảng màu đầy đủ

- [x] **Task 7 — Sync Indicator** (AC: 18,19)
  - [x] Thêm sync-status polling vào `KnowledgeMapTab` (setInterval 10s, clear khi unmount/tab inactive)
  - [x] Badge UI "⟳ Đồ thị đang cập nhật…" khi `syncing=true`
  - [x] Clear graph + re-fetch khi `activeProjectId` đổi

- [x] **Task 8 — Graph→Chat Bridge** (AC: 15,20)
  - [x] Cập nhật `frontend/src/store/workspaceStore.ts`: thêm `pendingChatInput` + `setPendingChatInput`
  - [x] Cập nhật `frontend/src/features/workspace/ChatbotPanel.tsx`: useEffect consume `pendingChatInput`

- [x] **Task 9 — CenterWorkspace cắm component** (AC: 21)
  - [x] Sửa `CenterWorkspace.tsx`: thay placeholder graph tab bằng `<KnowledgeMapTab projectId={activeProjectId} />`

- [x] **Task 10 — Test FE** (AC: 22,23)
  - [x] Vitest tests cho `KnowledgeMapTab`, `NodeDetailCard`, pendingChatInput

## Dev Notes

### Kiến trúc & nguồn dữ liệu bắt buộc tuân thủ

- **Hexagonal Architecture §9.5** — presentation/ router.py chỉ gọi use_cases; use_cases.py gọi domain + neo4j_client; KHÔNG gọi thẳng neo4j_client từ router. Xem `architecture.md §9.5` cấu trúc graph_rag module.
- **Module boundaries §9.6** — graph_rag là CONSUMER đọc Neo4j + cung cấp read API. Endpoint sync-status đọc `sync_outbox` (bảng dùng chung) via Postgres session factory — hợp lệ vì graph_rag worker đã đọc bảng này. Import `SyncOutboxORM` từ `workspace/infrastructure/orm_models.py` là chấp nhận được (shared outbox).
- **JWT + Owner Scoping** — tất cả endpoints phải `Depends(get_current_user)` + kiểm tra project thuộc user (`ProjectRepository.get_by_id_and_user`). Pattern: xem `workspace/presentation/router.py` — import `get_current_user` từ `identity/infrastructure/auth_dependencies.py`, `get_project_repository` từ `workspace/infrastructure/dependencies.py`. Project không tìm thấy hoặc không thuộc user → `raise HTTPException(404)`.
- **Lazy Rendering §8.4** — `MATCH (n) WHERE n.project_id=$pid AND NOT n:Deleted RETURN n LIMIT 150`. Cho edges: `MATCH (a)-[r]->(b) WHERE a.project_id=$pid AND NOT a:Deleted AND NOT b:Deleted RETURN r LIMIT 300`. `has_more` = True nếu total nodes > 150.
- **Expand 1-hop** — `MATCH (seed {id: $node_id})-[r]-(neighbor) WHERE neighbor.project_id=$pid AND NOT neighbor:Deleted AND NOT neighbor.id IN $existing_ids RETURN neighbor, r LIMIT 20`.
- **IDOR chống cross-project** — mọi Cypher đều `WHERE n.project_id = $project_id` (đã có từ 4.1 — xem `neo4j_adapter.py` MERGE với `project_id`). Endpoint cần double-check: verify project belongs to current_user TRƯỚC khi query Neo4j.

### Hiện trạng code sẽ ĐỘNG TỚI (xác minh từ codebase hiện tại)

- **`backend/src/modules/graph_rag/`** đã có: `domain/__init__.py` (trống), `application/use_cases.py` (chỉ re-export `sync_outbox_task`), `infrastructure/` (neo4j_adapter.py, outbox_worker.py, garbage_collection.py). **CHƯA có** `presentation/` folder, `domain/entities.py` (chưa tạo).
- **`backend/main.py`** hiện đăng ký 7 routers: `admin, identity, workspace, search, ingestion, orchestrator, citation`. Pattern import: `from backend.src.modules.<module>.presentation.router import router as <name>_router` + `app.include_router(<name>_router, prefix="/api")`. Thêm graph_router theo cùng pattern.
- **`frontend/src/features/workspace/CenterWorkspace.tsx`** dòng 51-53: `<div style={{ display: activeTab === 'graph' ? 'block' : 'none' }}><p className={styles.placeholder}>{t('tab.graph')}</p></div>` — đây là điểm thay thế bằng `<KnowledgeMapTab projectId={activeProjectId} />`.
- **`frontend/src/store/workspaceStore.ts`** có `TabKey = 'library' | 'graph' | 'writing'`, `activeTab`, `setActiveTab` — **KHÔNG sửa** type này. Chỉ thêm `pendingChatInput: string | null` + `setPendingChatInput`.
- **`frontend/src/store/chatStore.ts`** — `inputValue` là local state trong `ChatbotPanel.tsx` (dòng 21: `const [inputValue, setInputValue] = useState('')`) — **không phải** trong chatStore. `pendingChatInput` thêm vào workspaceStore, ChatbotPanel đọc qua `useWorkspaceStore(s => s.pendingChatInput)` + `useWorkspaceStore(s => s.setPendingChatInput)`.
- **Pattern CSS modules** — dùng `*.module.css` + CSS custom properties `var(--token-name)`. Xem `CenterWorkspace.module.css` và `LibraryTab.module.css` cho pattern layout.
- **Pattern API client FE** — axios `apiClient` với `withCredentials: true` (file `api/client.ts`). Pattern: `apiClient.get<T>('/api/...')` return `res.data`. Xem `api/projects.ts` cho pattern chuẩn.
- **i18n** — đã có `'tab.graph': { vi: 'Bản đồ Tri thức', en: 'Knowledge Map' }` và `'map.title': { vi: 'BẢN ĐỒ TRI THỨC CYTOSCAPE.JS', en: 'CYTOSCAPE.JS KNOWLEDGE MAP' }` trong `translations.ts`. Thêm key mới cho legend/card cần cập nhật `translations.ts`.
- **`get_project_repository`** dependency: `from backend.src.modules.workspace.infrastructure.dependencies import get_project_repository`. Dùng `ProjectRepository.get_by_id_and_user(project_id, user.id)` — kiểm tra owner.
- **Postgres session trong graph_rag router** (cho sync-status): dùng `get_async_session` từ `shared/infra/database.py` hoặc inject session factory từ `workspace/infrastructure/dependencies.py`. Pattern xem `ingestion/presentation/router.py`.
- **`SyncOutboxORM`** tại `backend/src/modules/workspace/infrastructure/orm_models.py`: `processed` (Boolean), `dead_lettered` (Boolean), `project_id` (Uuid as_uuid=False). Query: `SELECT COUNT(*) FROM sync_outbox WHERE project_id=:pid AND processed=false AND dead_lettered=false`.

### Lưu ý về Cytoscape.js + incremental layout

- **Import pattern**: `import Cytoscape from 'cytoscape'; import fcose from 'cytoscape-fcose'; Cytoscape.use(fcose);` — gọi `use()` một lần ở file-level (ngoài component), tránh lỗi "extension already registered" khi HMR.
- **Ref cho cy instance**: `const cyRef = useRef<Cytoscape.Core | null>(null)`. Khởi tạo trong `useEffect(() => { cyRef.current = Cytoscape({container: containerRef.current, ...}); return () => cyRef.current?.destroy(); }, [])`.
- **Incremental layout khi expand**: Sau `cy.add(newElements)`, lock vị trí nodes CŨ bằng `cy.nodes(':grabbed').lock()` hoặc dùng `fcose` `fixedNodeConstraint` option với nodes đang hiển thị. Layout chỉ chạy trên `newElements.union(newElements.neighborhood())`.
- **`has_more` flag**: Nếu `has_more=true` → hiển thị banner nhỏ "Đồ thị lớn, click node để mở rộng" (không auto-load tất cả).
- **Cytoscape style dùng CSS vars**: Cytoscape stylesheet dùng giá trị hex cứng (không đọc được CSS vars). Cần tạo hàm `getComputedStyle(document.documentElement).getPropertyValue('--state-success')` để lấy giá trị runtime, truyền vào Cytoscape style. Hoặc hardcode theo design tokens đã biết: `state-success=#10B981`, `state-warning=#F59E0B`, `accent-blue=#2563EB`, `accent-violet=#8B5CF6`.

### Learnings từ Story 4.1 (tránh lặp lỗi)

- **Key env Neo4j**: `pagecache_size` (KHÔNG phải `pagecache__size` double underscore) — đã fix ở 4.1.
- **`ctx["redis"]` do arq cung cấp** — graph router không dùng arq context, dùng `get_redis()` singleton bình thường nếu cần Redis.
- **Author.id format**: `"{project_id}:{normalized_name}"` — khi đọc graph, node `Author` có field `id` theo format này; label hiển thị FE dùng `name` property.
- **`project_id` property** trên mọi Neo4j node — đã verified, dùng để scope query. Không cần join Postgres để verify owner sau khi đã scope Cypher.
- **State property trên Paper node**: `"full_text"` hoặc `"metadata_only"` — đã MERGE vào Neo4j từ 4.1, sẵn sàng để FE phân biệt màu.
- **Test pattern**: `AsyncMock` + `_FakeSessionFactory` (xem `tests/unit/ingestion/test_worker.py:72`). Test Neo4j: mock `AsyncSession.run()` trả `MagicMock` với `.data()` method.
- **Pre-existing test failure**: `tests/unit/workspace/test_projects_api.py` có 35 lỗi SQLite isolation — không liên quan, đừng debug.

### Design Tokens cần dùng (hardcode cho Cytoscape style)

| Token | Light value | Dùng cho |
|---|---|---|
| `--state-success` | `#10B981` | Paper full-text node border |
| `--state-warning` | `#F59E0B` | Paper metadata-only node border + sync badge |
| `--accent-blue` | `#2563EB` | CITES edge + "Hỏi AI" button |
| `--accent-violet` | `#8B5CF6` | AUTHORED_BY edge + Author node |
| `--surface-base` | `#FAF9F6` | Canvas background |
| `--surface-raised` | Light: `#FFFFFF` / Dark: `#2A2A2A` | Node Detail Card background |
| `--border-hairline` | `#E5E2DC` | Node Detail Card border |
| `--ink-primary` | `#1C1917` | Card title text |
| `--ink-secondary` | `#78716C` | Card meta text |

### Project Structure Notes

**Files mới tạo:**
```
backend/src/modules/graph_rag/
├── domain/entities.py                   # GraphNode, GraphEdge, GraphData dataclasses
├── application/use_cases.py             # THÊM GraphReadUseCase (giữ re-export sync_outbox_task)
└── presentation/
    ├── __init__.py
    ├── router.py                        # 3 endpoints
    └── schemas.py                       # Pydantic response schemas

frontend/src/
├── api/graph.ts                         # fetchGraph, expandNode, getSyncStatus
├── types/graph.ts                       # GraphNode, GraphEdge, GraphResponse, SyncStatus
└── features/workspace/
    ├── KnowledgeMapTab.tsx
    ├── KnowledgeMapTab.module.css
    ├── NodeDetailCard.tsx
    ├── NodeDetailCard.module.css
    └── GraphLegend.tsx
```

**Files UPDATE:**
```
backend/main.py                          # +import graph_router, +app.include_router
frontend/src/store/workspaceStore.ts     # +pendingChatInput, +setPendingChatInput
frontend/src/features/workspace/CenterWorkspace.tsx   # thay placeholder graph
frontend/src/features/workspace/ChatbotPanel.tsx      # +useEffect consume pendingChatInput
frontend/src/i18n/translations.ts        # +key cho graph UI (legend, card, sync badge, ask AI btn)
tests/unit/graph_rag/                    # +test_graph_router.py
```

**KHÔNG SỬA:** `workspaceStore.ts` TabKey type (đã có 'graph'), `neo4j_client.py`, `neo4j_adapter.py`, `outbox_worker.py`, `garbage_collection.py`, `docker-compose.yml`, Alembic migrations.

### References

- [Source: architecture.md#8.4] — Cytoscape.js Lazy Rendering & Layout Expansion (150/300 limit, expand 1-hop ≤20, fcose/cola incremental layout)
- [Source: architecture.md#9.5] — Hexagonal module structure graph_rag (domain/application/infrastructure/presentation)
- [Source: architecture.md#9.6] — Module boundaries, IDOR scoping `project_id`, Producer=ingestion Consumer=graph_rag
- [Source: epics.md#Story-4.2] — phạm vi đầy đủ: BE endpoint + FE canvas + node state + author network + legend + sync indicator + "Hỏi AI"
- [Source: ux-designs/DESIGN.md#5] — Cytoscape.js Knowledge Map Canvas visual spec (colors, Node Detail Card)
- [Source: backend/main.py] — pattern đăng ký router (import + include_router prefix="/api")
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py] — Paper.state property, Author.id format, HANDLER_MAP
- [Source: frontend/src/features/workspace/CenterWorkspace.tsx] — điểm cắm KnowledgeMapTab (dòng 51-53)
- [Source: frontend/src/store/workspaceStore.ts] — state structure (thêm pendingChatInput)
- [Source: frontend/src/features/workspace/ChatbotPanel.tsx:21] — `inputValue` là local state (không trong store)
- [Source: backend/src/modules/workspace/infrastructure/orm_models.py#37] — SyncOutboxORM schema
- [Source: 4-1-dong-bo-postgres-neo4j-outbox-worker-va-garbage-collection.md — Review Findings] — các lỗi đã fix ở 4.1 để không tái hiện

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created (2026-06-18)
- Triển khai hoàn chỉnh vertical slice BE+FE story 4.2 (2026-06-18):
  - BE: 3 endpoints (GET graph, expand, sync-status) với JWT + owner scoping; `GraphReadUseCase` theo Hexagonal; 5 unit tests pass
  - FE: `KnowledgeMapTab` Cytoscape.js (fcose layout, node styles theo design tokens, toggle author, double-click expand, reset view); `NodeDetailCard` (Paper + Author variants, nút "Hỏi AI"); `GraphLegend`; sync-status polling 10s; Graph→Chat bridge qua `workspaceStore.pendingChatInput`
  - Thêm 17 translation keys mới cho graph UI
  - 99 FE tests pass (vitest), 5 BE tests pass (pytest), không có regression
  - pre-existing failures trong `test_producer.py` (3 failures) — không liên quan story này
- **Hậu code-review + verify E2E thật (2026-06-18):** áp 7 review patches + sửa 3 BLOCKER chỉ lộ khi chạy thật với Neo4j: (1) endpoint đọc graph sập vì `result.data()` ép Node→dict mất `.labels`; (2) canvas sập chiều cao do `.tabContent` không phải flex; (3) Cytoscape init lúc tab ẩn (0×0) không resize. Đã verify trực tiếp với Neo4j + backend thật (project DNA trả đúng 37 node / 27 cạnh), rebuild + restart container backend. Sau đó một AI agent khác tinh chỉnh thêm (refactor `loadGraph`/`cyReady`, dùng `style('display')` thay `show()/hide()`, thêm shim type `cytoscape-fcose.d.ts`, mở rộng test FE). **Trạng thái cuối đã xác nhận: BE 6 tests + FE 65 workspace tests pass, tsc sạch, app chạy đúng end-to-end.**

### File List

**Mới tạo:**
- `backend/src/modules/graph_rag/domain/entities.py`
- `backend/src/modules/graph_rag/application/use_cases.py` (cập nhật — thêm GraphReadUseCase)
- `backend/src/modules/graph_rag/presentation/__init__.py`
- `backend/src/modules/graph_rag/presentation/schemas.py`
- `backend/src/modules/graph_rag/presentation/router.py`
- `tests/unit/graph_rag/test_graph_router.py`
- `frontend/src/types/graph.ts`
- `frontend/src/types/cytoscape-fcose.d.ts` (shim type cho `cytoscape-fcose` — thêm khi sửa hậu-review)
- `frontend/src/api/graph.ts`
- `frontend/src/features/workspace/KnowledgeMapTab.tsx`
- `frontend/src/features/workspace/KnowledgeMapTab.module.css`
- `frontend/src/features/workspace/NodeDetailCard.tsx`
- `frontend/src/features/workspace/NodeDetailCard.module.css`
- `frontend/src/features/workspace/GraphLegend.tsx`
- `frontend/src/features/workspace/GraphLegend.module.css`
- `frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx`
- `frontend/src/features/workspace/__tests__/NodeDetailCard.test.tsx`

**Cập nhật:**
- `backend/main.py` (thêm graph_router)
- `frontend/package.json` + `frontend/package-lock.json` (thêm cytoscape, cytoscape-fcose, @types/cytoscape)
- `frontend/src/i18n/translations.ts` (thêm 17 graph.* keys)
- `frontend/src/store/workspaceStore.ts` (thêm pendingChatInput + setPendingChatInput)
- `frontend/src/features/workspace/CenterWorkspace.tsx` (mount KnowledgeMapTab)
- `frontend/src/features/workspace/ChatbotPanel.tsx` (consume pendingChatInput)

### Review Findings (code review 2026-06-18, 3 lớp: Blind Hunter + Edge Case Hunter + Acceptance Auditor)

**Patches đã áp dụng & xác minh (BE 6 tests pass, FE 101 tests pass, tsc sạch):**

- [x] [Review][Patch] Edge "treo" làm crash Cytoscape — `get_graph` query node (LIMIT 150) và edge (LIMIT 300) độc lập, edge có thể tham chiếu node ngoài cửa sổ → `cy.add()` throw. Fix: scope edge query theo tập `node_ids` đã trả về (`WHERE a.id IN $node_ids AND b.id IN $node_ids`). [backend/src/modules/graph_rag/application/use_cases.py:65]
- [x] [Review][Patch] IDOR hardening expand — `expand_node` không scope `seed` theo project_id (chỉ scope neighbor). Fix: thêm `seed.project_id = $pid AND NOT seed:Deleted`. [backend/src/modules/graph_rag/application/use_cases.py:94]
- [x] [Review][Patch] "Hỏi AI" switch sang tab `library` làm ẩn đồ thị đang xem (chat sống ở panel phải luôn mounted, không cần đổi tab). Fix: bỏ `setActiveTab('library')`. [frontend/src/features/workspace/NodeDetailCard.tsx:18]
- [x] [Review][Patch] Author↔paper dùng fuzzy substring match (tên rỗng khớp mọi paper; tên ngắn khớp nhầm) + `node.authors` luôn rỗng từ Neo4j. Fix: suy ra quan hệ từ cạnh `AUTHORED_BY` (truyền `allEdges` xuống card). [frontend/src/features/workspace/NodeDetailCard.tsx, KnowledgeMapTab.tsx]
- [x] [Review][Patch] Sync polling chạy ở mọi tab — AC#18 yêu cầu chỉ poll khi `activeTab === 'graph'`. Fix: gate polling theo `activeTab`, reset `syncing=false` khi rời tab/lỗi. [frontend/src/features/workspace/KnowledgeMapTab.tsx:236]
- [x] [Review][Patch] Không phân biệt "load lỗi" vs "đồ thị rỗng" — key `graph.error`/`graph.emptyGraph` có sẵn nhưng không render. Fix: thêm error/empty overlay. [frontend/src/features/workspace/KnowledgeMapTab.tsx]
- [x] [Review][Patch] Author đã ẩn lại hiện ra sau load/expand (toggle effect chỉ chạy theo `[showAuthors]`). Fix: `applyAuthorVisibility()` sau mỗi lần load & expand. [frontend/src/features/workspace/KnowledgeMapTab.tsx]

**Patches bổ sung (phát hiện khi verify trực quan trên trình duyệt — canvas trắng/legend đè header):**

- [x] [Review][Patch] 🔴 Canvas sập chiều cao → đồ thị không bao giờ vẽ + legend/overlay dồn lên đầu. Nguyên nhân: `.tabContent` là `display:block` nhưng div tab graph dùng `flex:1` để lấy chiều cao (vô hiệu) → `.container{height:100%}` không có tham chiếu. Fix: `.tabContent` thành `display:flex; flex-direction:column; min-height:0`; thêm `minHeight:0` cho div graph. [frontend/src/features/workspace/CenterWorkspace.module.css, CenterWorkspace.tsx]
- [x] [Review][Patch] 🔴 Cytoscape init lúc tab ẩn (mặc định tab `library` → container `display:none` 0×0) → giữ size 0, không tự resize khi hiện ra → canvas trắng dù có data. Fix: effect khi `activeTab === 'graph'` gọi `cy.resize()` + `cy.fit()`. [frontend/src/features/workspace/KnowledgeMapTab.tsx]
- [x] [Review][Patch] 🔴🔴 **BLOCKER — endpoint đọc graph luôn 500/rỗng**: `GraphReadUseCase` dùng `result.data()` → driver neo4j ép Node thành dict thuộc tính trần (mất `.labels`) → `list(n.labels)` ném `AttributeError`. Test cũ CHE bug vì mock `.data()` trả object có `.labels` (không giống driver thật). Đã xác minh trên Neo4j thật: project có 4 Paper + 33 Author active nhưng endpoint trả rỗng. Fix: lặp record (`[rec async for rec in result]`) giữ Node object cho cả `get_graph` + `expand_node`; sửa mock test cho khớp driver thật. Verify lại với DB thật → trả đúng 37 node. [backend/src/modules/graph_rag/application/use_cases.py, tests/unit/graph_rag/test_graph_router.py]

**Deferred (ngoài phạm vi Story 4.2):**

- [x] [Review][Defer] `abstract` (và `p.authors`) không được lưu trên Paper node trong Neo4j (adapter từ Story 4.1) → AC#13 abstract luôn rỗng dù FE đã render đúng khi có data. Spec 4.2 cấm sửa `neo4j_adapter.py`. Follow-up: Story 4.3 (graph extraction) bổ sung property. [backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py]
- [x] [Review][Defer] `has_more` chỉ tính theo node; edge bị cap 300 im lặng không có cờ báo. Đúng theo letter của spec (has_more = node-driven). Cân nhắc thêm cờ edge-overflow ở story sau.
- [x] [Review][Defer] `expandNode` dồn toàn bộ id vào query `existing_ids` → rủi ro URL quá dài (414) khi đồ thị rất lớn. Ở quy mô 150 node chưa chạm; cân nhắc chuyển POST body sau.

**Dismissed (false positive):**

- `dblclick` không phải event native Cytoscape → SAI. Đã verify cytoscape 3.34 đăng ký `dblclick`/`dbltap`. Expand double-click hoạt động.
- `pendingChatInput` đè draft của user → đúng theo thiết kế AC#20 ("dọn và prefill input").
- `year: 0` bị coi là rỗng → year hợp lệ không bao giờ là 0; đã chuyển sang `node.year != null` cho card.
