---
baseline_commit: e2723a4
---

# Story 4.4: [BE+FE] Gap Detection trên Bản đồ — GraphRAG Engine & Tô viền Khoảng trống

Status: done

## Story

As a **nhà nghiên cứu dùng C2-App-053**,
I want **bản đồ tri thức hiển thị chế độ "Tìm khoảng trống nghiên cứu" tô viền đỏ nhấp nháy các node Paper có mâu thuẫn học thuật (CONTRADICTS) và viền vàng cho cụm cô lập / Limitation chưa được giải quyết — dựa trên API backend `GET /api/projects/{project_id}/graph/gaps` chạy Cypher traversal trên Neo4j**,
so that **tôi có thể nhìn thấy ngay trên đồ thị những khoảng trống nghiên cứu thực sự cần điều tra và nhấn "Giải thích khoảng trống này" để hỏi AI phân tích sâu hơn — hiện thực hóa FR7 (Phát hiện khoảng trống) kết hợp FR9 (Trực quan hóa)**.

## Bối cảnh & Phạm vi

Story này là **[BE+FE] vertical slice xuyên 2 layer** trong module `[graph_rag]`:

- `[graph_rag] application/` — **GapDetectionUseCase**: implement `gap_detection(project_id)` + `graph_search(entities, project_id)` bằng Cypher traversal
- `[graph_rag] presentation/` — **endpoint** `GET /api/projects/{project_id}/graph/gaps` + schemas mới
- `[graph_rag] domain/` — **entities mới**: `GapContext`, `GapFlaggedNode`, `GapFlaggedEdge`, `GraphContext`
- `[frontend]` — **KnowledgeMapTab**: thêm gap mode toggle + apply Cytoscape styles + animation; **NodeDetailCard**: thêm nút "Giải thích khoảng trống này"

**Phụ thuộc đã done:**
- Story 4.1 (Neo4j driver, HANDLER_MAP, constraints base Paper/Author/Project)
- Story 4.3 (constraints ontology Finding/Limitation/… + handler `ONTOLOGY_EXTRACTED` ghi Finding/CONTRADICTS/SUPPORTS/HAS_LIMITATION vào Neo4j)
- Story 4.2 (KnowledgeMapTab.tsx, NodeDetailCard.tsx, Cytoscape patterns)

**Ranh giới:**
- ✅ TRONG phạm vi: `GapDetectionUseCase.gap_detection()` + `GapDetectionUseCase.graph_search()` + endpoint `/graph/gaps` + FE gap mode + tô viền animation + nút "Giải thích khoảng trống này" + unit tests
- ❌ NGOÀI phạm vi: Leiden community detection (Phase 2); `community_summary_search` (Phase 2); HTTP endpoint riêng cho `graph_search` (Story 4.5 gọi trực tiếp qua Python); FE hiển thị Finding/Limitation node trên canvas (vẫn chỉ Paper/Author)

### Quyết định kiến trúc đã chốt

1. **Gap detection MVP = Cypher traversal thuần**: 3 loại khoảng trống — (a) CONTRADICTS findings, (b) isolated Paper (0 cạnh CITES), (c) Limitation chưa có `[:FILLS_GAP]`. Đủ cho FR7, không cần Leiden.
2. **`graph_search` là Python-only method** — KHÔNG có HTTP endpoint. Story 4.5 sẽ import `GapDetectionUseCase` và gọi trực tiếp như LangGraph tool. Expose qua `__all__` trong `use_cases.py`.
3. **`GapDetectionUseCase` là class riêng** trong `application/use_cases.py` — không gộp vào `GraphReadUseCase` (separation of concerns).
4. **Domain entities mới**: `GapContext`, `GapFlaggedNode`, `GapFlaggedEdge`, `GraphContext` — thêm vào `domain/entities.py`.
5. **Cytoscape gap styles**: thêm vào `CY_STYLE` array trong `KnowledgeMapTab.tsx` (selector `.gap-contradiction` → đỏ, `.gap-isolated` → vàng). Pulsing bằng `setInterval` toggle `border-width` 750ms.
6. **NodeDetailCard `gapReason` prop**: optional `gapReason?: 'contradiction' | 'isolated' | 'unfilled_limitation' | null`. Nếu set → hiển thị nút "Giải thích khoảng trống này".
7. **IDOR guard**: mọi Cypher query đều scope `project_id`; endpoint dùng `_get_project_or_404` hiện có.
8. **Empty graph safe**: nếu Neo4j chưa có dữ liệu ontology (Story 4.3 chưa chạy) → `GapContext` rỗng, FE không crash.

## Acceptance Criteria

### A. [domain] Entities mới

1. Thêm vào `backend/src/modules/graph_rag/domain/entities.py`:
   ```python
   @dataclass
   class GapFlaggedNode:
       paper_id: str
       reason: str  # "isolated_cluster" | "has_unfilled_limitation" | "has_contradiction"

   @dataclass
   class GapFlaggedEdge:
       finding1_id: str
       finding2_id: str
       paper1_id: str
       paper2_id: str
       reason: str  # "contradicts"

   @dataclass
   class GapContext:
       flagged_nodes: list[GapFlaggedNode] = field(default_factory=list)
       flagged_edges: list[GapFlaggedEdge] = field(default_factory=list)

   @dataclass
   class GraphContext:
       nodes: list[GraphNode] = field(default_factory=list)
       edges: list[GraphEdge] = field(default_factory=list)
   ```
   (`field` import `from dataclasses import dataclass, field` — đã có trong file.)

### B. [application] GapDetectionUseCase

2. Tạo class `GapDetectionUseCase` trong `backend/src/modules/graph_rag/application/use_cases.py`:
   ```python
   class GapDetectionUseCase:
       def __init__(self, neo4j_driver) -> None:
           self._driver = neo4j_driver

       async def gap_detection(self, project_id: str) -> GapContext: ...
       async def graph_search(self, entities: list[str], project_id: str) -> GraphContext: ...
   ```

3. `gap_detection(project_id)` thực thi 3 Cypher query độc lập, trả `GapContext`:

   **Query 1 — CONTRADICTS:** Paper có Finding tham gia CONTRADICTS edge:
   ```cypher
   MATCH (f1:Finding {project_id: $pid})-[:CONTRADICTS]->(f2:Finding {project_id: $pid})
   MATCH (p1:Paper {project_id: $pid})-[:HAS_FINDING]->(f1)
   MATCH (p2:Paper {project_id: $pid})-[:HAS_FINDING]->(f2)
   WHERE NOT p1:Deleted AND NOT p2:Deleted
   RETURN DISTINCT f1.id AS finding1_id, f2.id AS finding2_id,
          p1.id AS paper1_id, p2.id AS paper2_id
   ```
   → Mỗi record tạo `GapFlaggedEdge(finding1_id, finding2_id, paper1_id, paper2_id, reason="contradicts")`
   → Mỗi `paper1_id` và `paper2_id` tạo `GapFlaggedNode(paper_id, reason="has_contradiction")`

   **Query 2 — Isolated Cluster:** Paper không có cạnh CITES nào:
   ```cypher
   MATCH (p:Paper {project_id: $pid}) WHERE NOT p:Deleted
   OPTIONAL MATCH (p)-[:CITES]-(other:Paper {project_id: $pid})
   WHERE NOT other:Deleted
   WITH p, count(other) AS cites_count
   WHERE cites_count = 0
   RETURN p.id AS paper_id
   ```
   → `GapFlaggedNode(paper_id, reason="isolated_cluster")` — chỉ thêm nếu paper_id chưa có trong flagged_nodes với reason "has_contradiction" (dedup theo priority: contradiction > isolated).

   **Query 3 — Unfilled Limitations:** Paper có Limitation chưa được FILLS_GAP:
   ```cypher
   MATCH (p:Paper {project_id: $pid})-[:HAS_LIMITATION]->(l:Limitation {project_id: $pid})
   WHERE NOT p:Deleted
     AND NOT EXISTS {
       MATCH (filler:Paper {project_id: $pid})-[:FILLS_GAP]->(l) WHERE NOT filler:Deleted
     }
   RETURN DISTINCT p.id AS paper_id
   ```
   → `GapFlaggedNode(paper_id, reason="has_unfilled_limitation")` — chỉ thêm nếu paper_id chưa có với reason cao hơn (priority: contradiction > unfilled_limitation > isolated).

4. `gap_detection` xử lý lỗi gracefully: nếu Cypher fail (vd Neo4j chưa có ontology nodes) → bắt exception → trả `GapContext()` rỗng (không raise, log warning).

5. `graph_search(entities, project_id)` thực thi Cypher 1-hop neighborhood:
   ```cypher
   MATCH (start {project_id: $pid})-[r]-(neighbor {project_id: $pid})
   WHERE (start.title IN $entities OR start.name IN $entities)
     AND NOT start:Deleted AND NOT neighbor:Deleted
   RETURN DISTINCT start, neighbor, r,
          start.id AS start_id, neighbor.id AS neighbor_id,
          elementId(r) AS rel_id, type(r) AS rel_type,
          start.id = startNode(r).id AS start_is_source
   LIMIT 50
   ```
   → Trả `GraphContext(nodes=[...], edges=[...])`. Node mapping giống `GraphReadUseCase.get_graph` (xem Dev Notes §Pattern code tái dùng).

6. Cập nhật `__all__` trong `use_cases.py` để export `GapDetectionUseCase`:
   ```python
   __all__ = ["sync_outbox_task", "GraphReadUseCase", "GapDetectionUseCase"]
   ```

7. Import thêm `GapContext`, `GraphContext` từ `domain/entities.py` trong `use_cases.py`.

### C. [presentation] Endpoint + Schemas

8. Thêm vào `backend/src/modules/graph_rag/presentation/schemas.py`:
   ```python
   class GapFlaggedNodeResponse(BaseModel):
       paper_id: str
       reason: str  # "isolated_cluster" | "has_unfilled_limitation" | "has_contradiction"

   class GapFlaggedEdgeResponse(BaseModel):
       finding1_id: str
       finding2_id: str
       paper1_id: str
       paper2_id: str
       reason: str  # "contradicts"

   class GapResponse(BaseModel):
       flagged_nodes: list[GapFlaggedNodeResponse]
       flagged_edges: list[GapFlaggedEdgeResponse]
   ```

9. Thêm endpoint vào `backend/src/modules/graph_rag/presentation/router.py`:
   ```python
   @router.get("/{project_id}/graph/gaps", response_model=GapResponse)
   async def get_graph_gaps(
       project_id: str,
       current_user: User = Depends(get_current_user),
       repo: ProjectRepository = Depends(get_project_repository),
   ) -> GapResponse:
       await _get_project_or_404(project_id, current_user, repo)
       driver = await get_neo4j_driver()
       use_case = GapDetectionUseCase(driver)
       gap_context = await use_case.gap_detection(project_id)
       return GapResponse(
           flagged_nodes=[
               GapFlaggedNodeResponse(paper_id=n.paper_id, reason=n.reason)
               for n in gap_context.flagged_nodes
           ],
           flagged_edges=[
               GapFlaggedEdgeResponse(
                   finding1_id=e.finding1_id,
                   finding2_id=e.finding2_id,
                   paper1_id=e.paper1_id,
                   paper2_id=e.paper2_id,
                   reason=e.reason,
               )
               for e in gap_context.flagged_edges
           ],
       )
   ```

10. Import `GapDetectionUseCase`, `GapResponse`, `GapFlaggedNodeResponse`, `GapFlaggedEdgeResponse` vào `router.py`.

11. Endpoint trả `GapResponse` với cả hai list rỗng nếu không có gap → HTTP 200 (không phải 404/empty).

12. Project không thuộc user → 404 (tái dùng `_get_project_or_404` hiện có — đã đúng).

### D. [frontend] Types + API

13. Thêm vào `frontend/src/types/graph.ts`:
    ```typescript
    export interface GapFlaggedNode {
      paper_id: string;
      reason: 'isolated_cluster' | 'has_unfilled_limitation' | 'has_contradiction';
    }

    export interface GapFlaggedEdge {
      finding1_id: string;
      finding2_id: string;
      paper1_id: string;
      paper2_id: string;
      reason: 'contradicts';
    }

    export interface GapResponse {
      flagged_nodes: GapFlaggedNode[];
      flagged_edges: GapFlaggedEdge[];
    }
    ```

14. Thêm hàm `fetchGaps` vào `frontend/src/api/graph.ts`:
    ```typescript
    import type { GraphResponse, SyncStatus, GapResponse } from '@/types/graph';

    export async function fetchGaps(projectId: string): Promise<GapResponse> {
      const res = await apiClient.get<GapResponse>(`/api/projects/${projectId}/graph/gaps`);
      return res.data;
    }
    ```

### E. [frontend] KnowledgeMapTab — Gap Mode

15. Thêm state và toggle vào `KnowledgeMapTab.tsx`:
    ```typescript
    const [gapMode, setGapMode] = useState(false);
    const [gapData, setGapData] = useState<GapResponse | null>(null);
    const [gapLoading, setGapLoading] = useState(false);
    ```

16. Khi `gapMode` chuyển từ `false` → `true` (toggle ON):
    - Gọi `fetchGaps(projectId)` với `gapLoading=true`
    - Khi nhận data: set `gapData`, apply Cytoscape classes (xem AC#17)
    - Khi lỗi: log error, `gapMode` về `false`, hiển thị thông báo (hoặc silent fail)
    - Set `gapLoading=false`

17. Áp dụng Cytoscape classes khi có `gapData`:
    ```typescript
    // Reset classes trước
    cy.elements().removeClass('gap-contradiction gap-isolated');

    // Nodes với has_contradiction → class gap-contradiction (đỏ)
    // Nodes khác trong flagged_nodes → class gap-isolated (vàng)
    const contradictionIds = new Set(
      gapData.flagged_nodes
        .filter(n => n.reason === 'has_contradiction')
        .map(n => n.paper_id)
    );
    const isolatedIds = new Set(
      gapData.flagged_nodes
        .filter(n => n.reason !== 'has_contradiction')
        .map(n => n.paper_id)
    );
    contradictionIds.forEach(id => cy.getElementById(id).addClass('gap-contradiction'));
    isolatedIds.forEach(id => {
      if (!contradictionIds.has(id)) cy.getElementById(id).addClass('gap-isolated');
    });
    ```

18. Khi `gapMode` → `false` (toggle OFF):
    - `cy.elements().removeClass('gap-contradiction gap-isolated')`
    - `setGapData(null)`

19. Khi `loadGraph` gọi lại (reload đồ thị): nếu `gapMode` đang ON → sau khi load xong, re-apply gap classes từ `gapData` hiện tại.

20. Thêm Cytoscape styles vào `CY_STYLE` array (THÊM SAU tất cả node type styles, TRƯỚC `node:selected`):
    ```typescript
    {
      selector: 'node.gap-contradiction',
      style: {
        'border-color': '#EF4444',  // state-danger red
        'border-width': 4,
        'border-style': 'solid',
      },
    },
    {
      selector: 'node.gap-isolated',
      style: {
        'border-color': '#F59E0B',  // state-warning yellow
        'border-width': 4,
        'border-style': 'solid',
      },
    },
    ```

21. Animation pulsing (oscillate border-width) khi gap mode ON và có data:
    ```typescript
    useEffect(() => {
      if (!gapMode || !gapData || !cyRef.current) return;
      const cy = cyRef.current;
      let wide = true;
      const interval = setInterval(() => {
        cy.elements('.gap-contradiction').style('border-width', wide ? '5px' : '3px');
        cy.elements('.gap-isolated').style('border-width', wide ? '5px' : '3px');
        wide = !wide;
      }, 750);
      return () => clearInterval(interval);
    }, [gapMode, gapData]);
    ```

22. Thêm nút toggle vào toolbar (sau nút "Khôi phục góc nhìn"):
    ```tsx
    <button
      className={`${styles.gapModeBtn} ${gapMode ? styles.gapModeBtnActive : ''}`}
      onClick={() => setGapMode(v => !v)}
      disabled={!projectId || gapLoading}
      type="button"
    >
      {gapLoading ? t('graph.gapModeLoading') : gapMode ? t('graph.gapModeOff') : t('graph.gapModeOn')}
    </button>
    ```

23. Thêm vào `KnowledgeMapTab.module.css`:
    ```css
    .gapModeBtn {
      padding: 4px 10px;
      font-size: 12px;
      border: 1px solid var(--border-hairline);
      border-radius: var(--rounded-md, 6px);
      background: var(--surface-raised);
      color: var(--ink-secondary);
      cursor: pointer;
      font-family: inherit;
    }

    .gapModeBtn:hover:not(:disabled) {
      background: var(--surface-base);
      color: var(--ink-primary);
    }

    .gapModeBtn:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .gapModeBtnActive {
      background: #FEE2E2;
      color: #991B1B;
      border-color: #EF4444;
    }

    .gapModeBtnActive:hover:not(:disabled) {
      background: #FECACA;
    }
    ```

### F. [frontend] NodeDetailCard — "Giải thích khoảng trống này"

24. Thêm prop `gapReason?: 'contradiction' | 'isolated' | 'unfilled_limitation' | null` vào `NodeDetailCardProps`:
    ```typescript
    interface NodeDetailCardProps {
      node: GraphNode;
      allNodes: GraphNode[];
      allEdges?: GraphEdge[];
      onClose: () => void;
      onExpand?: () => void;
      gapReason?: 'contradiction' | 'isolated' | 'unfilled_limitation' | null;
    }
    ```

25. Trong paper card view: nếu `gapReason` truthy → hiển thị nút "Giải thích khoảng trống này" trong `<div className={styles.actions}>`, DƯỚI nút "Hỏi AI về bài này":
    ```tsx
    {gapReason && (
      <button className={styles.explainGapBtn} onClick={handleExplainGap} type="button">
        {t('graph.explainGap')}
      </button>
    )}
    ```

26. `handleExplainGap` prefill chat với câu hỏi gap-specific:
    ```typescript
    const handleExplainGap = () => {
      const gapDesc = {
        contradiction: `mâu thuẫn học thuật trong nghiên cứu: ${node.title}`,
        isolated: `khoảng trống do thiếu liên kết trích dẫn: ${node.title}`,
        unfilled_limitation: `hạn chế chưa được giải quyết trong: ${node.title}`,
      }[gapReason ?? 'contradiction'] ?? `khoảng trống nghiên cứu liên quan đến: ${node.title}`;
      setPendingChatInput(`Phân tích ${gapDesc}. Hãy chỉ rõ mâu thuẫn, hạn chế và cơ hội nghiên cứu.`);
    };
    ```

27. `KnowledgeMapTab` truyền `gapReason` vào `NodeDetailCard` khi `gapMode` ON:
    ```typescript
    const nodeGapReason = gapMode && gapData
      ? (() => {
          const entry = gapData.flagged_nodes.find(n => n.paper_id === selectedNode?.id);
          if (!entry) return null;
          if (entry.reason === 'has_contradiction') return 'contradiction' as const;
          if (entry.reason === 'has_unfilled_limitation') return 'unfilled_limitation' as const;
          return 'isolated' as const;
        })()
      : null;

    // Trong JSX:
    <NodeDetailCard
      ...
      gapReason={nodeGapReason}
    />
    ```

### G. [frontend] Translations

28. Thêm vào `frontend/src/i18n/translations.ts`:
    ```typescript
    'graph.gapModeOn': { vi: '🔍 Tìm khoảng trống', en: '🔍 Find gaps' },
    'graph.gapModeOff': { vi: '✕ Ẩn khoảng trống', en: '✕ Hide gaps' },
    'graph.gapModeLoading': { vi: 'Đang phân tích...', en: 'Analysing...' },
    'graph.explainGap': { vi: 'Giải thích khoảng trống này', en: 'Explain this gap' },
    'graph.legendContradiction': { vi: 'Mâu thuẫn học thuật (đỏ)', en: 'Contradiction (red)' },
    'graph.legendIsolated': { vi: 'Cụm cô lập / Hạn chế (vàng)', en: 'Isolated / Limitation (yellow)' },
    ```

### H. Tests Backend

29. Tạo `tests/unit/graph_rag/test_gap_detection.py` với các tests:

    - `test_gap_detection_returns_empty_when_no_gaps`: mock Neo4j session trả empty cho 3 queries → `GapContext` với 2 list rỗng
    - `test_gap_detection_returns_contradiction_nodes`: mock query 1 trả 1 record `{finding1_id, finding2_id, paper1_id, paper2_id}` → `flagged_nodes` có 2 entries `has_contradiction`, `flagged_edges` có 1 entry `contradicts`
    - `test_gap_detection_returns_isolated_cluster`: mock query 2 trả 1 record `{paper_id}` → `flagged_nodes` có 1 entry `isolated_cluster`
    - `test_gap_detection_returns_unfilled_limitation`: mock query 3 trả 1 record `{paper_id}` → `flagged_nodes` có 1 entry `has_unfilled_limitation`
    - `test_gap_detection_dedup_priority_contradiction_over_isolated`: paper xuất hiện trong cả query 1 lẫn query 2 → chỉ 1 entry với reason `has_contradiction`
    - `test_gap_detection_graceful_on_neo4j_exception`: mock session.run raise Exception → trả `GapContext()` rỗng (không raise)
    - `test_graph_search_returns_nodes_and_edges`: mock session trả 1 record có `start + neighbor + rel` → `GraphContext` có nodes và edges
    - `test_graph_search_returns_empty_when_no_match`: mock trả empty → `GraphContext()` rỗng

    **Pattern mock session** (tái dùng từ `test_graph_router.py`):
    ```python
    class _FakeNeo4jSession:
        def __init__(self, run_side_effects=None):
            self._effects = list(run_side_effects or [])
            self._call_count = 0

        async def run(self, query, **kwargs):
            result = _FakeNeo4jResult(
                self._effects[self._call_count] if self._call_count < len(self._effects) else []
            )
            self._call_count += 1
            return result

        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass

    class _FakeNeo4jDriver:
        def __init__(self, run_side_effects=None):
            self._effects = run_side_effects or []
        def session(self): return _FakeNeo4jSession(self._effects)
    ```

30. Thêm vào `tests/unit/graph_rag/test_graph_router.py` (KHÔNG xóa tests cũ):

    - `test_get_graph_gaps_returns_empty_response`: mock GapDetectionUseCase trả GapContext rỗng → 200 với `{flagged_nodes: [], flagged_edges: []}`
    - `test_get_graph_gaps_returns_flagged_nodes`: mock trả GapContext với 1 flagged_node → response có 1 item trong `flagged_nodes`
    - `test_get_graph_gaps_project_not_owned_returns_404`: project không thuộc user → 404

    **Pattern mock GapDetectionUseCase trong router test**:
    ```python
    with patch("backend.src.modules.graph_rag.presentation.router.GapDetectionUseCase") as MockUseCase:
        instance = AsyncMock()
        instance.gap_detection = AsyncMock(return_value=GapContext())
        MockUseCase.return_value = instance
        # ... run test
    ```

### I. Tests Frontend

31. Trong `frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx` — thêm (KHÔNG xóa tests hiện có):

    - `'renders gap mode button'`: render với `projectId`, check button text `graph.gapModeOn` có trong DOM
    - `'toggles gap mode on click'`: click button → `fetchGaps` được gọi với `projectId`
    - `'applies gap-contradiction class to contradiction nodes'`: mock `fetchGaps` trả flagged_nodes `[{paper_id: 'p1', reason: 'has_contradiction'}]` → `cy.getElementById('p1').addClass` được gọi với `'gap-contradiction'`
    - `'removes gap classes on gap mode off'`: toggle ON rồi OFF → `cy.elements().removeClass('gap-contradiction gap-isolated')` được gọi

32. Trong `frontend/src/features/workspace/__tests__/NodeDetailCard.test.tsx` — thêm:

    - `'renders explainGap button when gapReason is set'`: render với `gapReason='contradiction'` → button text `graph.explainGap` visible
    - `'does not render explainGap button when gapReason is null'`: render với `gapReason={null}` → không có button `graph.explainGap`
    - `'explainGap button calls setPendingChatInput with gap context'`: click button → `setPendingChatInput` được gọi với string có chứa `node.title`

## Tasks / Subtasks

- [x] **Task 1 — [domain] Entities mới** (AC: 1)
  - [x] Thêm `GapFlaggedNode`, `GapFlaggedEdge`, `GapContext`, `GraphContext` vào `backend/src/modules/graph_rag/domain/entities.py`
  - [x] Giữ nguyên `GraphNode`, `GraphEdge`, `GraphData` đang có (KHÔNG sửa)

- [x] **Task 2 — [application] GapDetectionUseCase** (AC: 2–7)
  - [x] Tạo class `GapDetectionUseCase` trong `use_cases.py`
  - [x] Implement `gap_detection`: 3 Cypher queries + dedup theo priority + graceful exception
  - [x] Implement `graph_search`: 1-hop neighborhood Cypher, trả `GraphContext`
  - [x] Update `__all__`, import entities

- [x] **Task 3 — [presentation] Schemas + Endpoint** (AC: 8–12)
  - [x] Thêm `GapFlaggedNodeResponse`, `GapFlaggedEdgeResponse`, `GapResponse` vào `schemas.py`
  - [x] Thêm endpoint `GET /{project_id}/graph/gaps` vào `router.py`
  - [x] Import `GapDetectionUseCase` + schemas vào router

- [x] **Task 4 — [frontend] Types + API** (AC: 13–14)
  - [x] Thêm `GapFlaggedNode`, `GapFlaggedEdge`, `GapResponse` vào `types/graph.ts`
  - [x] Thêm `fetchGaps` vào `api/graph.ts`, cập nhật import type

- [x] **Task 5 — [frontend] KnowledgeMapTab Gap Mode** (AC: 15–23)
  - [x] Thêm state `gapMode`, `gapData`, `gapLoading`
  - [x] Toggle ON: fetch + apply Cytoscape classes
  - [x] Toggle OFF: remove classes, clear data
  - [x] Reload guard: re-apply classes sau `loadGraph`
  - [x] Thêm Cytoscape styles `.gap-contradiction` + `.gap-isolated` vào `CY_STYLE`
  - [x] Animation pulsing via `setInterval`
  - [x] Thêm nút toggle vào toolbar
  - [x] CSS `.gapModeBtn` + `.gapModeBtnActive` vào `KnowledgeMapTab.module.css`

- [x] **Task 6 — [frontend] NodeDetailCard** (AC: 24–27)
  - [x] Thêm prop `gapReason?` vào `NodeDetailCardProps`
  - [x] Thêm `handleExplainGap` + nút "Giải thích khoảng trống này"
  - [x] `KnowledgeMapTab` compute `nodeGapReason` và truyền xuống `NodeDetailCard`

- [x] **Task 7 — [frontend] Translations** (AC: 28)
  - [x] Thêm 6 key mới vào `translations.ts`

- [x] **Task 8 — Tests Backend** (AC: 29–30)
  - [x] Tạo `tests/unit/graph_rag/test_gap_detection.py` (9 tests)
  - [x] Thêm 3 tests gap endpoint vào `test_graph_router.py`

- [x] **Task 9 — Tests Frontend** (AC: 31–32)
  - [x] Thêm 4 tests vào `KnowledgeMapTab.test.tsx`
  - [x] Thêm 3 tests vào `NodeDetailCard.test.tsx`

### Review Findings (bmad-code-review — 2026-06-18)

3 review layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor). 2 patch đã fix, 3 defer, phần còn lại dismiss (đúng theo spec/false-positive).

- [x] [Review][Patch] `gap_detection` không bọc `async with session()` trong try/except → Neo4j down sẽ raise → 500, vi phạm AC#4 "không raise" [use_cases.py:228] — ĐÃ FIX: bọc session-acquisition + thêm test `test_gap_detection_graceful_on_session_acquisition_failure`
- [x] [Review][Patch] Pulsing animation đặt inline `border-width` (bypass) nhưng cleanup chỉ `clearInterval` → khi tắt gap mode `removeClass` không xóa được inline style, viền sai width còn sót [KnowledgeMapTab.tsx:344] — ĐÃ FIX: cleanup gọi `removeStyle('border-width')`
- [x] [Review][Defer] Gap queries không có `LIMIT` + node ngoài cửa sổ 150 node bị `getElementById` no-op âm thầm (gap không hiển thị) [use_cases.py:174-199] — deferred, giới hạn thiết kế MVP, spec đã note "addClass trên empty collection safe"
- [x] [Review][Defer] `graph_search` match mọi node có `project_id` (Finding/Limitation) → rủi ro KeyError `n["id"]` / mislabel thành paper [use_cases.py:201-210] — deferred, đúng spec verbatim, chưa có caller (để Story 4.5 khi wrap LangGraph tool)
- [x] [Review][Defer] `gapData` không refetch sau `loadGraph`/expand — node mới không nằm trong phân tích gap, chỉ re-apply classes cũ [KnowledgeMapTab.tsx:267] — deferred, AC#19 chỉ yêu cầu re-apply, refetch ngoài scope

## Dev Notes

### Kiến trúc & Ràng buộc bắt buộc

- **Hexagonal Architecture §9.5**: `GapDetectionUseCase` = application layer (gọi infrastructure Neo4j). KHÔNG đặt Cypher trong `router.py` hay `entities.py`.
- **Module boundary §9.6**: `graph_rag` là CONSUMER thuần (đọc Neo4j). KHÔNG ghi `sync_outbox`. KHÔNG gọi `ingestion` module.
- **Story 4.5 dependency**: `GapDetectionUseCase` + `graph_search` phải được export từ `graph_rag.application.use_cases` để Story 4.5 có thể import và wrap thành LangGraph tool. KHÔNG đổi interface sau khi tạo.
- **`get_neo4j_driver()` trong router**: gọi trực tiếp như `GraphReadUseCase` hiện có — xem `router.py:43`. `get_neo4j_driver` là async function trả driver singleton.
- **IDOR guard**: mọi Cypher query PHẢI scope `project_id` (xem `where n.project_id = $pid`). `_get_project_or_404` verify ownership trước khi chạy Cypher.

### Pattern code tái dùng

**GraphReadUseCase — Node mapping** (copy pattern vào `graph_search`):
```python
# File: backend/src/modules/graph_rag/application/use_cases.py:46-64
# Lặp record async for, KHÔNG dùng result.data() (mất .labels)
records = [rec async for rec in result]
for rec in records:
    n = rec["neighbor"]  # hoặc rec["n"]
    labels = list(n.labels)
    if "Author" in labels:
        label = "author"
        title = n.get("name", "")
    else:
        label = "paper"
        title = n.get("title", "")
    nodes.append(GraphNode(id=n["id"], label=label, title=title, ...))
```

**Edge direction trong graph_search** (xem `expand_node` use_case):
```python
# backend/src/modules/graph_rag/application/use_cases.py:140-148
if rec["start_is_source"]:
    source_id = rec["start_id"]
    target_id = n["id"]
else:
    source_id = n["id"]
    target_id = rec["start_id"]
```

**get_neo4j_driver pattern** (xem `router.py:43-44`):
```python
from backend.src.shared.infra.neo4j_client import get_neo4j_driver
driver = await get_neo4j_driver()
use_case = GapDetectionUseCase(driver)
```

**_FakeNeo4jSession cho tests** — copy từ `tests/unit/graph_rag/test_graph_router.py:55-73`. 3 queries riêng biệt nên mock `run_side_effects` có 3 phần tử.

**Cytoscape class manipulation** (tái dùng pattern từ `applyAuthorVisibility`):
```typescript
// backend/src/features/workspace/KnowledgeMapTab.tsx:133-141
cy.elements('[label="author"]').style('display', 'element');
// Gap mode dùng addClass/removeClass thay vì style trực tiếp:
cy.getElementById(paperId).addClass('gap-contradiction');
cy.elements().removeClass('gap-contradiction gap-isolated');
```

**fetchGraph pattern** (tái dùng cho fetchGaps):
```typescript
// frontend/src/api/graph.ts:4-7
const res = await apiClient.get<GraphResponse>(`/api/projects/${projectId}/graph`);
return res.data;
```

**setPendingChatInput pattern** (xem NodeDetailCard.tsx:18-21):
```typescript
const setPendingChatInput = useWorkspaceStore((s) => s.setPendingChatInput);
const handleAskAI = () => {
  setPendingChatInput(`Hãy phân tích bài báo: ${node.title}`);
};
```

### Hiện trạng code sẽ ĐỘNG TỚI (xác minh trước khi code)

- **`backend/src/modules/graph_rag/domain/entities.py`** (line 1–30): 3 dataclass `GraphNode`, `GraphEdge`, `GraphData`. Thêm 4 dataclass mới VÀO CUỐI file. `from dataclasses import dataclass, field` đã có.
- **`backend/src/modules/graph_rag/application/use_cases.py`** (line 1–153): `GraphReadUseCase` có `get_graph` + `expand_node`. Thêm `GapDetectionUseCase` VÀO CUỐI file (không sửa `GraphReadUseCase`). Import thêm `GapContext`, `GraphContext` từ domain.
- **`backend/src/modules/graph_rag/presentation/schemas.py`** (line 1–30): 4 Pydantic models hiện có. Thêm 3 models mới VÀO CUỐI.
- **`backend/src/modules/graph_rag/presentation/router.py`** (line 1–89): 3 endpoints hiện có. Thêm 1 endpoint + imports mới. `_get_project_or_404` (line 24-33) tái dùng.
- **`frontend/src/types/graph.ts`** (line 1–27): 4 interfaces. Thêm 3 interfaces mới VÀO CUỐI.
- **`frontend/src/api/graph.ts`** (line 1–25): 3 functions. Thêm `fetchGaps`, cập nhật import type.
- **`frontend/src/features/workspace/KnowledgeMapTab.tsx`** (line 1–415): Complex component với Cytoscape. CY_STYLE array (line 27–104) → thêm 2 class selectors trước `node:selected` (line 98-103). Toolbar (line 365–377) → thêm nút gap mode. State section (line 116–124) → thêm 3 state mới. `loadGraph` callback (line 209–239) → thêm guard re-apply gap. Import `fetchGaps`, `GapResponse` từ api/types.
- **`frontend/src/features/workspace/KnowledgeMapTab.module.css`** (line 1–127): CSS module. Thêm 4 class vào cuối.
- **`frontend/src/features/workspace/NodeDetailCard.tsx`** (line 1–97): Paper + Author views. Thêm prop `gapReason?` + handler + button trong paper view (line 66–96).
- **`frontend/src/i18n/translations.ts`**: thêm 6 key vào `translations` object (xem grep line 136–152 hiện có key graph.*).

### Cypher Queries đầy đủ

#### gap_detection — Query 1: CONTRADICTS

```cypher
MATCH (f1:Finding {project_id: $pid})-[:CONTRADICTS]->(f2:Finding {project_id: $pid})
MATCH (p1:Paper {project_id: $pid})-[:HAS_FINDING]->(f1)
MATCH (p2:Paper {project_id: $pid})-[:HAS_FINDING]->(f2)
WHERE NOT p1:Deleted AND NOT p2:Deleted
RETURN DISTINCT f1.id AS finding1_id, f2.id AS finding2_id,
       p1.id AS paper1_id, p2.id AS paper2_id
```
Params: `pid=project_id`

#### gap_detection — Query 2: Isolated Paper

```cypher
MATCH (p:Paper {project_id: $pid}) WHERE NOT p:Deleted
OPTIONAL MATCH (p)-[:CITES]-(other:Paper {project_id: $pid})
WHERE NOT other:Deleted
WITH p, count(other) AS cites_count
WHERE cites_count = 0
RETURN p.id AS paper_id
```
Params: `pid=project_id`

#### gap_detection — Query 3: Unfilled Limitation

```cypher
MATCH (p:Paper {project_id: $pid})-[:HAS_LIMITATION]->(l:Limitation {project_id: $pid})
WHERE NOT p:Deleted
  AND NOT EXISTS {
    MATCH (filler:Paper {project_id: $pid})-[:FILLS_GAP]->(l)
    WHERE NOT filler:Deleted
  }
RETURN DISTINCT p.id AS paper_id
```
Params: `pid=project_id`

#### graph_search — 1-hop neighborhood

```cypher
MATCH (start {project_id: $pid})-[r]-(neighbor {project_id: $pid})
WHERE (start.title IN $entities OR start.name IN $entities)
  AND NOT start:Deleted AND NOT neighbor:Deleted
RETURN DISTINCT start, neighbor, r,
       start.id AS start_id, neighbor.id AS neighbor_id,
       elementId(r) AS rel_id, type(r) AS rel_type,
       start.id = startNode(r).id AS start_is_source
LIMIT 50
```
Params: `pid=project_id`, `entities=entities` (List[str])

### Logic dedup trong gap_detection

```python
seen: dict[str, str] = {}  # paper_id → reason (priority: contradiction > unfilled > isolated)
PRIORITY = {"has_contradiction": 3, "has_unfilled_limitation": 2, "isolated_cluster": 1}

def _add_flagged_node(paper_id: str, reason: str):
    current = seen.get(paper_id)
    if current is None or PRIORITY[reason] > PRIORITY[current]:
        seen[paper_id] = reason

# Sau 3 queries, build list:
flagged_nodes = [GapFlaggedNode(paper_id=pid, reason=r) for pid, r in seen.items()]
```

### UX Design tokens Gap Mode

Từ `UX DESIGN.md §5 Cytoscape.js`:
- "Node khoảng trống nghiên cứu có màu đỏ `{colors.state-danger}` với hiệu ứng hoạt hình vòng tròn tỏa bóng mờ nhấp nháy" → `#EF4444` (state-danger trong CSS vars)
- Cụm cô lập → vàng `{colors.state-warning}` → `#F59E0B`
- Animation `pulse 1.5s infinite` — implement bằng JS setInterval (750ms per half-cycle) vì Cytoscape không hỗ trợ CSS `animation` trực tiếp trong stylesheet

### GraphLegend — cân nhắc cập nhật

Story 4.2 đã tạo `GraphLegend.tsx` + `GraphLegend.module.css`. Khi gap mode ON, nên thêm legend cho đỏ/vàng. Tuy nhiên để giữ scope MVP gọn:
- **Option A (recommended):** Không sửa GraphLegend trong story này — gap mode button đủ rõ ràng, legend có thể thêm sau nếu UX review yêu cầu.
- **Option B:** Thêm 2 legend items conditional (chỉ hiện khi `gapMode=true`).
- Dev chọn Option A trừ khi thời gian cho phép.

### Learnings từ Story 4.3 (áp dụng vào 4.4)

- **`result.data()` bug Neo4j**: Trong `get_graph`/`expand_node`, code đã dùng `async for rec in result` để giữ Node object. `graph_search` PHẢI dùng cùng pattern (KHÔNG `result.data()` cho node records — chỉ dùng `.data()` cho edge records là scalar).
- **Test mock Neo4j session**: `_FakeNeo4jSession` có `_call_count` để trả side effects theo thứ tự. `gap_detection` gọi 3 session.run → mock cần 3 phần tử.
- **JSON parse graceful**: không áp dụng (4.4 không gọi LLM), nhưng vẫn cần try/except quanh mỗi Cypher query để chống crash khi Neo4j chưa có indexes.
- **Pre-existing test failures**: `tests/unit/workspace/test_projects_api.py` có ~35 lỗi SQLite — KHÔNG debug, bỏ qua.

### Learnings từ Story 4.2 KnowledgeMapTab (tránh lỗi cũ)

- **KHÔNG return sớm khi `!projectId`** (line 358-362 comment trong KnowledgeMapTab.tsx) — Cytoscape container phải luôn render. Gap mode button phải `disabled={!projectId}` thay vì bỏ render.
- **Cytoscape `cy.getElementById(id)`** có thể trả empty collection nếu node không có trong canvas (vd node bị ẩn hoặc chưa load). `addClass` trên empty collection không crash — safe.
- **`applyAuthorVisibility`** dùng `showAuthorsRef` (ref, không phải state) trong callback. Pattern này tránh stale closure. Gap mode nên dùng `gapModeRef` + `gapDataRef` nếu cần dùng trong callbacks có stale closure risk.
- **Re-apply sau loadGraph**: `loadGraph` gọi `cy.elements().remove()` rồi add lại → mất classes. Guard: sau `cy.layout().run()` trong `loadGraph`, nếu `gapModeRef.current` → re-apply classes từ `gapDataRef.current`.

### Project Structure Notes

**Files MỚI tạo:**
```
tests/unit/graph_rag/
└── test_gap_detection.py            # Tests GapDetectionUseCase (AC: 29)
```

**Files CẬP NHẬT:**
```
Backend:
backend/src/modules/graph_rag/domain/entities.py           # +GapFlaggedNode, GapFlaggedEdge, GapContext, GraphContext
backend/src/modules/graph_rag/application/use_cases.py     # +GapDetectionUseCase, update __all__
backend/src/modules/graph_rag/presentation/schemas.py      # +GapFlaggedNodeResponse, GapFlaggedEdgeResponse, GapResponse
backend/src/modules/graph_rag/presentation/router.py       # +GET /graph/gaps endpoint

Frontend:
frontend/src/types/graph.ts                                # +GapFlaggedNode, GapFlaggedEdge, GapResponse
frontend/src/api/graph.ts                                  # +fetchGaps
frontend/src/features/workspace/KnowledgeMapTab.tsx        # +gap mode toggle, CY_STYLE, animation
frontend/src/features/workspace/KnowledgeMapTab.module.css # +gapModeBtn styles
frontend/src/features/workspace/NodeDetailCard.tsx         # +gapReason prop + explainGap button
frontend/src/i18n/translations.ts                          # +6 gap keys

Tests:
tests/unit/graph_rag/test_graph_router.py                  # +3 tests cho /graph/gaps
frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx   # +4 gap tests
frontend/src/features/workspace/__tests__/NodeDetailCard.test.tsx    # +3 gap tests
```

**KHÔNG SỬA:** `outbox_worker.py`, `neo4j_adapter.py`, `GraphReadUseCase` (chỉ thêm class mới), `worker.py`, Alembic migrations (không có schema DB mới), `GraphLegend.tsx` (optional).

### References

- [Source: epics.md §Story 4.4, line 390-399] — Mô tả gap_detection/graph_search/endpoint/UX tô viền + Cầu nối Gap→Chat + Phạm vi MVP (Cypher, không Leiden)
- [Source: architecture.md §5.2, line 152-155] — Module 1 API: `gap_detection(project_id)->GapContext`, `graph_search(entities, project_id)->GraphContext`
- [Source: architecture.md §9.6, line 461-463] — Role-clarity: `graph_rag` là CONSUMER; schema/constraints do `graph_rag` sở hữu
- [Source: sprint-change-proposal-2026-06-17-gap-detection.md §Section 4.A] — AC nháp cho gap_detection + graph_search (AC 1–6)
- [Source: ux-designs/ux-C2-App-053-2026-06-12/DESIGN.md §5, line 210-215, 231] — Cytoscape styles: gap node đỏ `state-danger` pulse 1.5s; knowledge map canvas spec
- [Source: backend/src/modules/graph_rag/application/use_cases.py:39-92] — `get_graph` pattern: async for records, Node mapping (paper/author), edge direction
- [Source: backend/src/modules/graph_rag/presentation/router.py:24-33, 36-50] — `_get_project_or_404` + endpoint pattern
- [Source: backend/src/modules/graph_rag/infrastructure/neo4j_adapter.py:326-334] — `HANDLER_MAP` + import patterns
- [Source: tests/unit/graph_rag/test_graph_router.py:33-82] — `_FakeNeo4jResult`, `_FakeNeo4jSession`, `_FakeNeo4jDriver` mock classes
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:27-104, 358-362] — CY_STYLE array + "KHÔNG return sớm" comment
- [Source: frontend/src/features/workspace/NodeDetailCard.tsx:14-21] — NodeDetailCardProps + setPendingChatInput pattern
- [Source: 4-3-graph-extraction-trich-xuat-ontology-hoc-thuat.md §Dev Notes] — Learnings `result.data()` bug + test mock patterns

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created (2026-06-18)
- Story 4.4 fully implemented: BE domain entities, GapDetectionUseCase (3 Cypher queries + dedup priority), REST endpoint GET /graph/gaps, FE types+API, KnowledgeMapTab gap mode toggle+animation, NodeDetailCard explainGap button, translations, tests (2026-06-18)
- Backend: 9 tests test_gap_detection.py + 3 tests test_graph_router.py → 52/52 graph_rag unit tests pass
- Frontend: 11 tests KnowledgeMapTab + 10 tests NodeDetailCard → 21/21 pass, no regressions

### File List

- backend/src/modules/graph_rag/domain/entities.py
- backend/src/modules/graph_rag/application/use_cases.py
- backend/src/modules/graph_rag/presentation/schemas.py
- backend/src/modules/graph_rag/presentation/router.py
- frontend/src/types/graph.ts
- frontend/src/api/graph.ts
- frontend/src/features/workspace/KnowledgeMapTab.tsx
- frontend/src/features/workspace/KnowledgeMapTab.module.css
- frontend/src/features/workspace/NodeDetailCard.tsx
- frontend/src/features/workspace/NodeDetailCard.module.css
- frontend/src/i18n/translations.ts
- tests/unit/graph_rag/test_gap_detection.py (new)
- tests/unit/graph_rag/test_graph_router.py
- frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx
- frontend/src/features/workspace/__tests__/NodeDetailCard.test.tsx

### Change Log

- 2026-06-18: Story 4.4 implemented — Gap Detection trên Bản đồ, GraphRAG Engine & Tô viền Khoảng trống. Thêm GapDetectionUseCase với 3 Cypher queries (CONTRADICTS/isolated/unfilled), endpoint GET /graph/gaps, gap mode toggle FE với pulsing animation, nút "Giải thích khoảng trống này".
