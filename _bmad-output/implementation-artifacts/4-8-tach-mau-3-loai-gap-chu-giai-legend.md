---
baseline_commit: e2723a4
---

# Story 4.8: [Frontend] Tách màu 3 loại Gap + Chú giải Gap có điều kiện

Status: done

## Story

As a **nhà nghiên cứu dùng C2-App-053**,
I want **bản đồ tri thức (Knowledge Map) hiển thị 3 loại khoảng trống nghiên cứu bằng 3 màu phân biệt — đỏ (mâu thuẫn), cam (limitation chưa giải quyết), xanh (cụm cô lập) — và bảng chú giải gap hiện ra khi bật chế độ "Tìm khoảng trống"**,
so that **tôi có thể nhận ra ngay loại khoảng trống của từng node Paper và không bị nhầm lẫn giữa 3 bản chất khác nhau (mâu thuẫn học thuật / hạn chế bỏ ngỏ / không có kết nối trích dẫn) — hoàn thiện UX của FR9 sau correct-course 2026-06-18**.

## Bối cảnh & Phạm vi

Story này là **[Frontend] thuần** — không có thay đổi backend. Đây là follow-up của correct-course 2026-06-18: Story 4.4 (gap detection + tô viền) đã gộp `has_unfilled_limitation` và `isolated_cluster` vào cùng class `gap-isolated` (màu vàng) — quyết định MVP "Option A". Story 4.8 nâng cấp lên 3 màu rõ ràng.

**Nhãn module/role:** `[frontend]` thuần — `KnowledgeMapTab.tsx` (CY_STYLE + `applyGapClasses` + pulsing), `GraphLegend.tsx` (legend có điều kiện), `GraphLegend.module.css`, `translations.ts`.

**Phụ thuộc đã done:**
- Story 4.4: gap mode toggle, `gapData` state, `applyGapClasses`, pulsing animation, `gapReason` prop NodeDetailCard — tất cả đã tồn tại, story 4.8 chỉ **sửa màu** và **thêm legend**.
- Story 4.4 trả về `reason: 'isolated_cluster' | 'has_unfilled_limitation' | 'has_contradiction'` — đã có, không cần thay đổi API.

**KHÔNG phụ thuộc** Story 4.6 hay 4.7 (có thể làm ngay, dữ liệu gap CITES/FILLS_GAP rỗng ≡ tất cả node xanh — an toàn, không crash; sau khi 4.6+4.7 sinh dữ liệu thật, màu sẽ phản ánh đúng).

**Ranh giới:**
- ✅ TRONG phạm vi: sửa `CY_STYLE` (thêm `gap-unfilled`, đổi `gap-isolated` → xanh) · sửa `applyGapClasses` (tách 3 class) · sửa pulsing + cleanup `removeStyle` · `GraphLegend` nhận `gapMode` prop + render 3 dòng gap có điều kiện · CSS cho gap legend items · translation keys · cập nhật tests
- ❌ NGOÀI phạm vi: thay đổi backend (`gap_detection` query, entities, schemas) · thay đổi `NodeDetailCard` (3 nhánh `handleExplainGap` ĐÃ đúng trong 4.4, chỉ cần verify) · thay đổi API/types (`GapFlaggedNode.reason` type không đổi)

## Acceptance Criteria

### A. [frontend] Tách màu 3 class trong `CY_STYLE` (`KnowledgeMapTab.tsx`)

1. Giữ nguyên selector `node.gap-contradiction` với `border-color: '#EF4444'` (đỏ) — **KHÔNG THAY ĐỔI**.

2. **ĐỔI** `border-color` của selector `node.gap-isolated` từ `#F59E0B` (vàng) sang **`#3B82F6`** (xanh `accent-blue`). Màu xanh = chỉ áp cho `isolated_cluster` (không có kết nối trích dẫn).

3. **THÊM** selector mới `node.gap-unfilled` vào `CY_STYLE` (NGAY SAU `node.gap-isolated`, TRƯỚC `node:selected`):
   ```typescript
   {
     selector: 'node.gap-unfilled',
     style: {
       'border-color': '#F59E0B',  // cam amber — has_unfilled_limitation
       'border-width': 4,
       'border-style': 'solid',
     },
   },
   ```

### B. [frontend] Tách 3 class trong `applyGapClasses` (`KnowledgeMapTab.tsx`)

4. Trong hàm `applyGapClasses(data: GapResponse)`, cập nhật logic tách class:
   - `cy.elements().removeClass('gap-contradiction gap-unfilled gap-isolated')` — xóa cả 3 class (thêm `gap-unfilled` vào reset)
   - Tạo 3 Set: `contradictionIds` (`has_contradiction`), `unfilledIds` (`has_unfilled_limitation`), `isolatedIds` (`isolated_cluster`)
   - Priority dedup (giữ nguyên logic 4.4): contradiction > unfilled > isolated — nếu paper_id đã có trong contradiction → không thêm vào unfilled/isolated; nếu đã có trong unfilled → không thêm vào isolated
   - Áp class: `gap-contradiction`, `gap-unfilled`, `gap-isolated` theo Set tương ứng

5. Khi `gapMode` → OFF (toggle tắt): `cy.elements().removeClass('gap-contradiction gap-unfilled gap-isolated')` — thêm `gap-unfilled` vào dòng remove hiện có (line 316 KnowledgeMapTab.tsx).

### C. [frontend] Pulsing animation cho cả 3 class

6. Trong `useEffect` pulsing animation (line 344 KnowledgeMapTab.tsx), thêm `gap-unfilled` vào selector:
   ```typescript
   cy.elements('.gap-contradiction, .gap-unfilled, .gap-isolated').style(
     'border-width', wide ? '5px' : '3px'
   );
   ```
   Áp pulsing đồng bộ cho cả 3 class.

7. Trong cleanup `removeStyle` của pulsing effect (line 353 KnowledgeMapTab.tsx), cập nhật selector:
   ```typescript
   cyRef.current?.elements('.gap-contradiction, .gap-unfilled, .gap-isolated').removeStyle('border-width');
   ```

### D. [frontend] `GraphLegend` nhận `gapMode` prop và render chú giải gap có điều kiện

8. `GraphLegend.tsx`: Thêm prop `gapMode?: boolean` (mặc định `false`):
   ```typescript
   interface GraphLegendProps {
     gapMode?: boolean;
   }
   export function GraphLegend({ gapMode = false }: GraphLegendProps) { ... }
   ```

9. Trong `GraphLegend.tsx`, thêm block chú giải gap **chỉ khi `gapMode === true`**, sau danh sách legend thường:
   ```tsx
   {gapMode && (
     <>
       <p className={styles.gapSectionTitle}>{t('graph.legendGapSection')}</p>
       <ul className={styles.list}>
         <li>
           <span className={`${styles.dotGap} ${styles.dotGapContradiction}`} />
           {t('graph.legendContradiction')}
         </li>
         <li>
           <span className={`${styles.dotGap} ${styles.dotGapUnfilled}`} />
           {t('graph.legendUnfilled')}
         </li>
         <li>
           <span className={`${styles.dotGap} ${styles.dotGapIsolated}`} />
           {t('graph.legendIsolated')}
         </li>
       </ul>
     </>
   )}
   ```

10. Trong `KnowledgeMapTab.tsx`, truyền `gapMode` vào `<GraphLegend gapMode={gapMode} />` (thay thế `<GraphLegend />` hiện có, line 497).

### E. [frontend] CSS cho legend gap (`GraphLegend.module.css`)

11. Thêm vào `GraphLegend.module.css`:
    ```css
    .gapSectionTitle {
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #78716C;
      margin: 8px 0 4px;
      border-top: 1px solid #E5E2DC;
      padding-top: 6px;
    }

    .dotGap {
      display: inline-block;
      width: 12px;
      height: 12px;
      border-radius: 50%;
      flex-shrink: 0;
      background: transparent;
      border-width: 2.5px;
      border-style: solid;
    }

    .dotGapContradiction {
      border-color: #EF4444;
    }

    .dotGapUnfilled {
      border-color: #F59E0B;
    }

    .dotGapIsolated {
      border-color: #3B82F6;
    }
    ```

### F. [frontend] Translation keys (`translations.ts`)

12. Thêm key mới `graph.legendUnfilled` vào `translations.ts`:
    ```typescript
    'graph.legendUnfilled': { vi: 'Limitation chưa giải quyết (cam)', en: 'Unfilled limitation (orange)' },
    ```

13. Thêm key mới `graph.legendGapSection` (tiêu đề phân cách legend gap):
    ```typescript
    'graph.legendGapSection': { vi: 'Khoảng trống', en: 'Gaps' },
    ```

14. Cập nhật key hiện có `graph.legendIsolated` (đổi "vàng" → "xanh", đổi mô tả):
    ```typescript
    'graph.legendIsolated': { vi: 'Cụm cô lập (xanh)', en: 'Isolated cluster (blue)' },
    ```
    *(Bỏ "/ Hạn chế" vì nay hạn chế là cam riêng)*

15. Key hiện có `graph.legendContradiction` GIỮ NGUYÊN: `{ vi: 'Mâu thuẫn học thuật (đỏ)', en: 'Contradiction (red)' }`.

### G. [frontend] NodeDetailCard — Verify 3 nhánh `handleExplainGap`

16. Kiểm tra `NodeDetailCard.tsx` — `handleExplainGap` đã có 3 nhánh đúng từ Story 4.4:
    - `contradiction` → "mâu thuẫn học thuật..."
    - `isolated` → "khoảng trống do thiếu liên kết trích dẫn..."
    - `unfilled_limitation` → "hạn chế chưa được giải quyết trong..."
    
    **KHÔNG cần sửa**. Chỉ xác nhận 3 nhánh còn đó và đúng.

### H. Tests Frontend

17. **Cập nhật** `frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx` — test `'removes gap classes on gap mode off'` (line 234–260): sửa assertion từ `'gap-contradiction gap-isolated'` → **`'gap-contradiction gap-unfilled gap-isolated'`** (vì `applyGapClasses` và off-toggle đều dùng 3-class string mới).

18. **Thêm** vào `KnowledgeMapTab.test.tsx`:
    - `'applies gap-unfilled class to has_unfilled_limitation nodes'`: mock `fetchGaps` trả `[{paper_id: 'p2', reason: 'has_unfilled_limitation'}]` → `cy.getElementById('p2').addClass('gap-unfilled')` được gọi.
    - `'applies gap-isolated (blue) class to isolated_cluster nodes'`: mock `fetchGaps` trả `[{paper_id: 'p3', reason: 'isolated_cluster'}]` → `cy.getElementById('p3').addClass('gap-isolated')` được gọi (lần này xanh, không còn vàng).
    - `'dedup: contradiction wins over unfilled for same paper'`: mock `[{paper_id: 'p4', reason: 'has_contradiction'}, {paper_id: 'p4', reason: 'has_unfilled_limitation'}]` → chỉ `gap-contradiction` được thêm cho `'p4'`, không thêm `gap-unfilled`.
    - `'passes gapMode to GraphLegend'`: render với `projectId`, toggle gap mode ON → `GraphLegend` nhận `gapMode=true` → text `graph.legendGapSection` (vi: "Khoảng trống") xuất hiện trong DOM.

19. **Giữ nguyên** 4 test gap hiện có (không xóa):
    - `'renders gap mode button'`
    - `'toggles gap mode on click — fetchGaps called with projectId'`
    - `'applies gap-contradiction class to contradiction nodes'`
    - `'removes gap classes on gap mode off'` ← chỉ cập nhật assertion (AC#17)

## Tasks / Subtasks

- [x] **Task 1 — [frontend] Cập nhật `CY_STYLE` + `applyGapClasses`** (AC: 1–5)
  - [x] Thêm selector `node.gap-unfilled` (cam `#F59E0B`) vào `CY_STYLE` sau `node.gap-isolated`, trước `node:selected`
  - [x] Đổi `node.gap-isolated` border-color từ `#F59E0B` → `#3B82F6` (xanh)
  - [x] Cập nhật `applyGapClasses`: tạo 3 Set, áp 3 class với priority dedup (contradiction > unfilled > isolated)
  - [x] Cập nhật `cy.elements().removeClass(...)` trong toggle OFF (line 316): thêm `gap-unfilled`

- [x] **Task 2 — [frontend] Cập nhật pulsing animation** (AC: 6–7)
  - [x] Thêm `.gap-unfilled` vào selector trong `setInterval` callback (pulsing)
  - [x] Thêm `.gap-unfilled` vào selector trong `removeStyle` cleanup

- [x] **Task 3 — [frontend] `GraphLegend` với gap section có điều kiện** (AC: 8–11)
  - [x] Thêm `gapMode?: boolean` prop vào `GraphLegend`
  - [x] Thêm block legend gap (3 items đỏ/cam/xanh) conditional `{gapMode && ...}`
  - [x] Thêm CSS `.gapSectionTitle`, `.dotGap`, `.dotGapContradiction`, `.dotGapUnfilled`, `.dotGapIsolated` vào `GraphLegend.module.css`
  - [x] Cập nhật `KnowledgeMapTab.tsx`: `<GraphLegend gapMode={gapMode} />`

- [x] **Task 4 — [frontend] Translations** (AC: 12–15)
  - [x] Thêm key `graph.legendUnfilled` (cam)
  - [x] Thêm key `graph.legendGapSection` (tiêu đề phần gap)
  - [x] Cập nhật `graph.legendIsolated` → "Cụm cô lập (xanh)" / "Isolated cluster (blue)"
  - [x] Xác nhận `graph.legendContradiction` GIỮ NGUYÊN (đỏ)

- [x] **Task 5 — [frontend] Verify NodeDetailCard** (AC: 16)
  - [x] Đọc `NodeDetailCard.tsx` xác nhận 3 nhánh `handleExplainGap` đủ: contradiction / isolated / unfilled_limitation
  - [x] Không cần sửa code; chạy test hiện có để xác nhận pass

- [x] **Task 6 — [frontend] Tests** (AC: 17–19)
  - [x] Cập nhật assertion `'removes gap classes on gap mode off'`: `'gap-contradiction gap-unfilled gap-isolated'`
  - [x] Thêm `'applies gap-unfilled class to has_unfilled_limitation nodes'`
  - [x] Thêm `'applies gap-isolated (blue) class to isolated_cluster nodes'`
  - [x] Thêm `'dedup: contradiction wins over unfilled for same paper'`
  - [x] Thêm `'passes gapMode to GraphLegend — gap legend items appear'`
  - [x] Chạy toàn bộ test suite FE: `npm run test` → pass

## Dev Notes

### Kiến trúc & Ràng buộc bắt buộc

- **FE-only:** story này KHÔNG chạm backend. `GapFlaggedNode.reason` type từ API (`'isolated_cluster' | 'has_unfilled_limitation' | 'has_contradiction'`) **không đổi**. Dữ liệu backend trả về đã đúng từ Story 4.4.
- **KHÔNG sửa `applyGapClasses` signature** — function nhận `GapResponse`, không thay đổi contract.
- **KHÔNG sửa `gapModeRef`/`gapDataRef`** refs — logic stale-closure-safe từ 4.4 giữ nguyên.
- **KHÔNG sửa `loadGraph` re-apply guard** (line 267) — dùng `applyGapClasses(gapDataRef.current)`, sẽ tự dùng logic 3-class mới khi hàm được cập nhật.
- **CY_STYLE immutable**: array khai báo ở module level — dev thêm/sửa entry trực tiếp, không factory.

### 🚨 Regression bắt buộc — 1 test PHẢI cập nhật

Test tại `KnowledgeMapTab.test.tsx` line 259:
```typescript
expect(removeClassMock).toHaveBeenCalledWith('gap-contradiction gap-isolated');
```
**SAU story 4.8**, string này phải là `'gap-contradiction gap-unfilled gap-isolated'`. Nếu không cập nhật, test sẽ FAIL sau khi code thay đổi. Đây là test regression duy nhất cần sửa trước khi commit.

### Hiện trạng code sẽ ĐỘNG TỚI (xác minh trước khi code)

**`frontend/src/features/workspace/KnowledgeMapTab.tsx`**

- **`CY_STYLE` (line 97–119):** 2 selectors gap hiện có:
  - line 98–103: `node.gap-contradiction` → `#EF4444` (GIỮ)
  - line 104–110: `node.gap-isolated` → `#F59E0B` (ĐỔI → `#3B82F6`)
  - THÊM `node.gap-unfilled` SAU `node.gap-isolated` (giữa line 110 và line 111 — `node:selected`)
  
- **`applyGapClasses` (line 167–181):** 
  ```typescript
  // Hiện tại: chỉ contradictionIds + isolatedIds (gộp cả unfilled vào isolated)
  const isolatedIds = new Set(
    data.flagged_nodes.filter((n) => n.reason !== 'has_contradiction').map(...)
  );
  // → gộp cả has_unfilled_limitation lẫn isolated_cluster vào gap-isolated (vàng)
  ```
  Cần tách thành 3 Set với priority dedup.

- **Toggle OFF (line 315–317):**
  ```typescript
  cy.elements().removeClass('gap-contradiction gap-isolated');
  // → cần thêm 'gap-unfilled'
  ```

- **Pulsing (line 344–346):**
  ```typescript
  cy.elements('.gap-contradiction').style(...);
  cy.elements('.gap-isolated').style(...);
  // → gộp thành 1 selector hoặc thêm dòng .gap-unfilled
  ```

- **Cleanup (line 353):**
  ```typescript
  cyRef.current?.elements('.gap-contradiction, .gap-isolated').removeStyle('border-width');
  // → thêm '.gap-unfilled'
  ```

- **`<GraphLegend />` (line 497):** không truyền prop → `<GraphLegend gapMode={gapMode} />`

**`frontend/src/features/workspace/GraphLegend.tsx`** (line 1–33): Component đơn giản, không có props hiện tại. Thêm prop + conditional block.

**`frontend/src/features/workspace/GraphLegend.module.css`** (line 1–91): Thêm 5 class mới vào cuối.

**`frontend/src/i18n/translations.ts`** (line 160–161 — gap keys hiện có):
```typescript
'graph.legendContradiction': { vi: 'Mâu thuẫn học thuật (đỏ)', en: 'Contradiction (red)' },
'graph.legendIsolated': { vi: 'Cụm cô lập / Hạn chế (vàng)', en: 'Isolated / Limitation (yellow)' },
```
→ Sửa `legendIsolated`, thêm `legendUnfilled` + `legendGapSection`.

**`frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx`** (line 234–260): Cập nhật assertion + thêm test.

### Pattern code tái dùng

**`applyGapClasses` — logic dedup 3 Set (khuyến nghị):**
```typescript
const applyGapClasses = useCallback((data: GapResponse) => {
  const cy = cyRef.current;
  if (!cy) return;
  cy.elements().removeClass('gap-contradiction gap-unfilled gap-isolated');
  const contradictionIds = new Set(
    data.flagged_nodes.filter((n) => n.reason === 'has_contradiction').map((n) => n.paper_id),
  );
  const unfilledIds = new Set(
    data.flagged_nodes
      .filter((n) => n.reason === 'has_unfilled_limitation' && !contradictionIds.has(n.paper_id))
      .map((n) => n.paper_id),
  );
  const isolatedIds = new Set(
    data.flagged_nodes
      .filter((n) => n.reason === 'isolated_cluster' && !contradictionIds.has(n.paper_id) && !unfilledIds.has(n.paper_id))
      .map((n) => n.paper_id),
  );
  contradictionIds.forEach((id) => cy.getElementById(id).addClass('gap-contradiction'));
  unfilledIds.forEach((id) => cy.getElementById(id).addClass('gap-unfilled'));
  isolatedIds.forEach((id) => cy.getElementById(id).addClass('gap-isolated'));
}, []);
```

**Pulsing animation — gộp selector 3 class:**
```typescript
const interval = setInterval(() => {
  cy.elements('.gap-contradiction, .gap-unfilled, .gap-isolated').style(
    'border-width', wide ? '5px' : '3px'
  );
  wide = !wide;
}, 750);
return () => {
  clearInterval(interval);
  cyRef.current?.elements('.gap-contradiction, .gap-unfilled, .gap-isolated').removeStyle('border-width');
};
```

**Cytoscape CY_STYLE — thêm selector (pattern từ 4.4):**
```typescript
{
  selector: 'node.gap-unfilled',
  style: {
    'border-color': '#F59E0B',  // amber orange — has_unfilled_limitation
    'border-width': 4,
    'border-style': 'solid',
  },
},
```

**GraphLegend — conditional gap section (pattern legend items hiện có):**
Mỗi gap item dùng `<span className={`${styles.dotGap} ${styles.dotGapXxx}`} />` thay vì `styles.dot` — dot gap chỉ có border, không có fill (thể hiện "viền màu" thay vì "node tô màu").

**Test `addClassMock` pattern (từ 4.4):**
```typescript
vi.mocked(graphApi.fetchGaps).mockResolvedValue({
  flagged_nodes: [{ paper_id: 'p2', reason: 'has_unfilled_limitation' }],
  flagged_edges: [],
});
// ...
await waitFor(() => expect(mocks.cy.getElementById).toHaveBeenCalledWith('p2'));
await waitFor(() => expect(mocks.addClassMock).toHaveBeenCalledWith('gap-unfilled'));
```

### Learnings từ Story 4.4 (áp dụng vào 4.8)

- **Cytoscape `addClass` trên empty collection không crash** — safe khi paper không có trong canvas.
- **`removeStyle('border-width')` là bắt buộc khi dùng pulsing** — inline style đặt bởi `setInterval` bypass stylesheet class (4px) và còn sót sau `removeClass`. Fix review 4.4 đã chứng minh điều này (AC#2 của review → patch đã merge). **KHÔNG bỏ `removeStyle` trong cleanup**.
- **`gapModeRef` + `gapDataRef`** — `applyGapClasses` và `loadGraph` re-apply guard dùng refs để tránh stale closure. Khi sửa `applyGapClasses`, hàm mới sẽ tự động được dùng bởi cả 2 luồng (toggle ON + reload).
- **Class reset VÀ selector phải nhất quán:** `removeClass` string, pulsing selector, và `removeStyle` selector đều phải liệt kê đúng các class đang dùng. Thiếu 1 class → inline style hoặc class cũ còn sót.
- **"KHÔNG return sớm khi !projectId"** (line 447 comment) — pattern từ 4.2 giữ nguyên. GraphLegend luôn render trong container.
- **Deferred review 4.4:** `gapData` không refetch sau `loadGraph`/expand (AC chỉ yêu cầu re-apply classes cũ). Giữ nguyên behavior này trong 4.8.

### Design Tokens Gap màu

Story 4.8 chốt 3 màu (từ ARCH §5.2 + sprint-change-proposal):
- **Đỏ `#EF4444`** = `state-danger` — `has_contradiction` (mâu thuẫn học thuật, nghiêm trọng nhất)
- **Cam `#F59E0B`** = `state-warning` amber — `has_unfilled_limitation` (hạn chế chưa giải quyết)
- **Xanh `#3B82F6`** = `accent-blue` — `isolated_cluster` (không có cạnh CITES — không kết nối)

Priority hiển thị khi node có nhiều reason: contradiction > unfilled > isolated.

Note: Màu `#F59E0B` (amber) của `gap-unfilled` trùng với màu cũ của `gap-isolated` (vàng từ Story 4.4). Dev cần tránh nhầm khi đọc code cũ.

### Project Structure Notes

**Files CẬP NHẬT:**
```
frontend/src/features/workspace/KnowledgeMapTab.tsx          # CY_STYLE + applyGapClasses + pulsing + GraphLegend prop
frontend/src/features/workspace/GraphLegend.tsx              # +gapMode prop + conditional gap legend
frontend/src/features/workspace/GraphLegend.module.css       # +CSS gap legend indicators
frontend/src/i18n/translations.ts                            # +legendUnfilled, +legendGapSection, ~legendIsolated
frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx  # ~1 assertion + 4 tests mới
```

**Files KHÔNG SỬA:**
- `NodeDetailCard.tsx` / `NodeDetailCard.module.css` — `handleExplainGap` 3 nhánh đã đúng
- `KnowledgeMapTab.module.css` — không có class mới cần thêm (classes gap là Cytoscape classes, không CSS modules)
- Tất cả backend files (`use_cases.py`, `router.py`, `entities.py`, …)
- `frontend/src/api/graph.ts`, `frontend/src/types/graph.ts` — API/types không thay đổi
- `frontend/src/features/workspace/__tests__/NodeDetailCard.test.tsx` — tests hiện có vẫn valid

### References

- [Source: sprint-change-proposal-2026-06-18-cites-fillsgap-producers.md §Section 4.A, lines 145-163] — Story 4.8 AC nháp: 3 class, priority dedup, legend có điều kiện
- [Source: epics.md §Story 4.8, line 489-505] — AC nháp + phạm vi + phụ thuộc
- [Source: epics.md §Sprint change notes, line 391] — "Thứ tự follow-up: 4.8 (FE, song song được) · 4.6 → 4.7 (ingestion)"
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:97-119] — CY_STYLE hiện tại (2 selectors gap: contradiction đỏ, isolated vàng)
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:167-181] — `applyGapClasses` hiện tại (chỉ 2 Set — cần tách thành 3)
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:314-337] — Gap mode toggle effect (ON/OFF)
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:340-355] — Pulsing animation + cleanup `removeStyle`
- [Source: frontend/src/features/workspace/KnowledgeMapTab.tsx:497] — `<GraphLegend />` (cần truyền prop `gapMode`)
- [Source: frontend/src/features/workspace/GraphLegend.tsx:1-33] — `GraphLegend` hiện tại (không có prop)
- [Source: frontend/src/features/workspace/GraphLegend.module.css:1-91] — CSS legend hiện tại (pattern .dot, .diamond, .line)
- [Source: frontend/src/i18n/translations.ts:149-161] — Translation keys graph legend + gap hiện có
- [Source: frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx:234-260] — Test cần cập nhật assertion (line 259)
- [Source: 4-4-gap-detection-tren-map-graphrag-engine-va-to-vien.md §Review Findings, line 543] — Patch "removeStyle" = bắt buộc; §Dev Notes §GraphLegend line 709-714 = "Option A" nay được nâng cấp
- [Source: 4-4-gap-detection-tren-map-graphrag-engine-va-to-vien.md §Dev Notes §UX Design tokens, line 703-708] — Màu: #EF4444, #F59E0B từ Story 4.4; #3B82F6 mới cho isolated

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

### Completion Notes List

- Ultimate context engine analysis completed — comprehensive developer guide created (2026-06-18)
- Tất cả 6 Task đã hoàn thành (2026-06-18): CY_STYLE tách 3 màu, applyGapClasses 3 Set với priority dedup, pulsing animation bao gồm gap-unfilled, GraphLegend nhận gapMode prop và hiển thị legend gap có điều kiện, 3 translation keys mới/cập nhật, 4 test mới + 1 assertion cập nhật — tất cả pass.
- NodeDetailCard.tsx xác nhận đủ 3 nhánh handleExplainGap (contradiction/isolated/unfilled_limitation) — không cần sửa.
- CenterWorkspace.test.tsx có 4 tests fail do thiếu Cytoscape mock — đây là lỗi pre-existing từ story 1.4, không liên quan story 4.8.

### File List

- frontend/src/features/workspace/KnowledgeMapTab.tsx
- frontend/src/features/workspace/GraphLegend.tsx
- frontend/src/features/workspace/GraphLegend.module.css
- frontend/src/i18n/translations.ts
- frontend/src/features/workspace/__tests__/KnowledgeMapTab.test.tsx

### Change Log

- 2026-06-18: Story 4.8 hoàn thành — Tách 3 màu gap (đỏ contradiction / cam unfilled / xanh isolated) + GraphLegend hiển thị chú giải gap có điều kiện khi bật gapMode + 5 test mới/cập nhật pass.

### Review Findings

**Code review 2026-06-18 (bmad-code-review — Blind Hunter + Edge Case Hunter + Acceptance Auditor):**

- Acceptance Auditor: **19/19 AC đạt**, không vi phạm ràng buộc "KHÔNG SỬA" (NodeDetailCard, types/API, refs, loadGraph guard giữ nguyên). Màu CY_STYLE ↔ legend dot ↔ translation đồng bộ (đỏ #EF4444 / cam #F59E0B / xanh #3B82F6).

- [x] [Review][Patch] Gap state kẹt khi bỏ chọn dự án giữa lúc fetchGaps in-flight — nút gap kẹt `disabled` + legend gap hiện trên đồ thị rỗng [KnowledgeMapTab.tsx:328-339] — ĐÃ SỬA: gộp `!projectId` vào nhánh reset, thêm `setGapLoading(false)` + `setGapMode(false)`. Thêm regression test `'clears gap state when project is deselected mid-fetch'`. (Lưu ý: hạ tầng gap-mode vốn từ Story 4.4; sửa nằm trong effect mà 4.8 đã chạm, không động vào loadGraph re-apply guard.)

- [x] [Review][Defer] Chuyển dự án A→B khi gap mode ON: loadGraph re-apply `gapDataRef` (data của A) lên đồ thị B trong cửa sổ trước khi fetch B resolve [KnowledgeMapTab.tsx:281] — deferred, pre-existing (Story 4.4 infra; 4.8 cấm sửa loadGraph re-apply guard). Tác động thực tế thấp (paper_id gần như không trùng giữa dự án).
- [x] [Review][Defer] Mock test dùng chung một `nodeElement` cho mọi `getElementById(id)` → bug gán class sai-node không bị bắt [__tests__/KnowledgeMapTab.test.tsx:312-323] — deferred, pre-existing (hạ tầng mock từ 4.4). Các test 1-node hiện tại vẫn đúng; nâng cấp mock per-id để sau.

- Dismissed (noise/đã xử lý): thứ tự cleanup pulsing inline `border-width` (đã xử lý bằng `removeStyle` sẵn có); interval restart khi `gapData` đổi (chỉ cosmetic); enum `reason` lạ (union có kiểu + filter `===` → không gán class, không default sai).

- Pre-existing không liên quan 4.8: `CenterWorkspace.test.tsx` (4 fail) thiếu mock Cytoscape — lỗi từ Story 1.4, file không bị 4.8 đụng tới.

**Kết quả:** typecheck sạch; `KnowledgeMapTab.test.tsx` 16/16 pass (15 + 1 regression mới); toàn bộ workspace suite pass trừ CenterWorkspace pre-existing.
