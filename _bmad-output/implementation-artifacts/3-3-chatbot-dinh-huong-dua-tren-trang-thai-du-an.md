---
baseline_commit: fc89d14
---

# Story 3.3: Chatbot Đinh Hướng Dựa Trên Trạng Thái Dự Án

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn chatbot chủ động gợi ý hành động tiếp theo dựa trên trạng thái hiện tại của dự án,
Để tôi không bị bối rối khi chưa biết bắt đầu từ đâu.

> **Phạm vi story này** tương đương epic 3.6 + 3.7:
> - Epic 3.6: [Backend] Context-Aware Suggestion API
> - Epic 3.7: [Frontend] Quick Reply Action UI

## Acceptance Criteria

1. **AC#1 — Suggestions API [Backend]**
   **Given** gọi `POST /api/chat/suggestions` với body `{"active_tab": "library", "document_count": 0, "has_draft": false}`,
   **When** endpoint xử lý,
   **Then** trả về JSON `[{"label": "Tải tài liệu lên", "actionKey": "open_upload"}, {"label": "Tìm kiếm bài báo", "actionKey": "focus_search"}, {"label": "Xem bản đồ tri thức", "actionKey": "navigate_graph"}]` HTTP 200.

2. **AC#2 — Suggestions thay đổi theo context [Backend]**
   **Given** gọi `POST /api/chat/suggestions` với `{"active_tab": "library", "document_count": 5, "has_draft": false}`,
   **When** endpoint xử lý,
   **Then** trả về gợi ý phù hợp với dự án đã có tài liệu (ví dụ: không gợi ý upload lại, mà gợi ý xem bản đồ hoặc soạn thảo).

3. **AC#3 — Quick Reply Buttons hiển thị [Frontend]**
   **Given** user chọn một dự án và ChatbotPanel hiển thị,
   **When** suggestions được fetch về thành công,
   **Then** hiển thị tối đa 3 nút pill/chip bên trên `inputArea` trong ChatbotPanel, với label từ API.

4. **AC#4 — Navigate to tab [Frontend]**
   **Given** đang hiển thị Quick Reply Buttons,
   **When** user click nút có `actionKey = "navigate_library"` hoặc `"navigate_graph"` hoặc `"navigate_writing"`,
   **Then** tab tương ứng trong `CenterWorkspace` trở thành active ngay lập tức (không reload trang).

5. **AC#5 — Open Upload Modal [Frontend]**
   **Given** đang hiển thị Quick Reply Buttons,
   **When** user click nút có `actionKey = "open_upload"`,
   **Then** tab Library được active VÀ Upload Modal mở ra.

6. **AC#6 — Suggestions refresh khi đổi project [Frontend]**
   **Given** đang hiển thị suggestions của project A,
   **When** user chọn project B khác,
   **Then** suggestions cũ biến mất, fetch lại suggestions cho project B và hiển thị mới.

> 🔍 **Cách nghiệm thu trực quan:**
> 1. **AC#1-2**: Swagger UI → `POST /api/chat/suggestions` với `document_count=0` → thấy 3 gợi ý có upload. Đổi `document_count=5` → thấy gợi ý khác.
> 2. **AC#3**: Chọn project trên Dashboard → ChatbotPanel hiện 3 nút pill nhỏ phía trên ô nhập chat.
> 3. **AC#4**: Click nút "Xem bản đồ tri thức" → tab Graph trong CenterWorkspace active.
> 4. **AC#5**: Click nút "Tải tài liệu lên" → tab Library active + Upload Modal mở ra.
> 5. **AC#6**: Đổi project → pills cũ biến mất rồi hiện pills mới của project mới.

---

## Tasks / Subtasks

### FRONTEND — Workspace Store (AC#3, #4, #5, #6)

- [x] **Task 1**: Tạo `frontend/src/store/workspaceStore.ts` — shared state cho tab navigation và upload modal
  - [x] 1.1 Tạo file mới:
    ```typescript
    import { create } from 'zustand';

    type TabKey = 'library' | 'graph' | 'writing';

    interface WorkspaceState {
      activeTab: TabKey;
      documentCount: number;
      isUploadModalOpen: boolean;

      setActiveTab: (tab: TabKey) => void;
      setDocumentCount: (count: number) => void;
      setUploadModalOpen: (open: boolean) => void;
    }

    export const useWorkspaceStore = create<WorkspaceState>()((set) => ({
      activeTab: 'library',
      documentCount: 0,
      isUploadModalOpen: false,

      setActiveTab: (tab) => set({ activeTab: tab }),
      setDocumentCount: (count) => set({ documentCount: count }),
      setUploadModalOpen: (open) => set({ isUploadModalOpen: open }),
    }));
    ```

### FRONTEND — CenterWorkspace.tsx (AC#4, #5)

- [x] **Task 2**: Cập nhật `CenterWorkspace.tsx` — dùng `workspaceStore` thay cho local `activeTab` state
  - [x] 2.1 Xóa `const [activeTab, setActiveTab] = useState<TabKey>('library')` (local state)
  - [x] 2.2 Thêm import và đọc từ store:
    ```typescript
    import { useWorkspaceStore } from '@/store/workspaceStore';
    // ...
    const activeTab = useWorkspaceStore((s) => s.activeTab);
    const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);
    ```
  - [x] 2.3 Xóa type alias `type TabKey = ...` khỏi `CenterWorkspace.tsx` (đã chuyển sang workspaceStore)
  - **Lưu ý**: Không cần thay đổi logic render hay CSS — chỉ thay nguồn state.

### FRONTEND — LibraryTab.tsx (AC#5, #6)

- [x] **Task 3**: Cập nhật `LibraryTab.tsx` — sync document count và upload modal state với store
  - [x] 3.1 Thêm import workspaceStore:
    ```typescript
    import { useWorkspaceStore } from '@/store/workspaceStore';
    ```
  - [x] 3.2 Thay `const [showUpload, setShowUpload] = useState(false)` bằng:
    ```typescript
    const isUploadModalOpen = useWorkspaceStore((s) => s.isUploadModalOpen);
    const setUploadModalOpen = useWorkspaceStore((s) => s.setUploadModalOpen);
    ```
  - [x] 3.3 Thay tất cả `showUpload` → `isUploadModalOpen` và `setShowUpload` → `setUploadModalOpen` trong file (dùng replace_all).
    Cụ thể:
    - `onClick={() => setShowUpload(true)}` → `onClick={() => setUploadModalOpen(true)}`
    - `{showUpload && projectId && (` → `{isUploadModalOpen && projectId && (`
    - `onClose={() => setShowUpload(false)}` → `onClose={() => setUploadModalOpen(false)}`
    - `onSuccess={(documentId) => { setShowUpload(false); ...` → `onSuccess={(documentId) => { setUploadModalOpen(false); ...`
  - [x] 3.4 Thêm `useEffect` sync document count vào store khi `papers` thay đổi:
    ```typescript
    const setDocumentCount = useWorkspaceStore((s) => s.setDocumentCount);
    // ...
    useEffect(() => {
      setDocumentCount(papers.length);
    }, [papers.length, setDocumentCount]);
    ```
    **Đặt useEffect này SAU khi `papers` state đã được định nghĩa** (dòng ~32 file hiện tại).

### BACKEND — Suggestions API (AC#1, #2)

- [x] **Task 4**: Thêm DTOs vào `backend/src/modules/orchestrator/application/dtos.py`
  - [x] 4.1 Thêm vào cuối file:
    ```python
    @dataclass
    class GetSuggestionsDTO:
        active_tab: str  # 'library' | 'graph' | 'writing'
        document_count: int
        has_draft: bool
    ```

- [x] **Task 5**: Tạo `GetSuggestionsUseCase` trong `backend/src/modules/orchestrator/application/use_cases.py`
  - [x] 5.1 Thêm vào cuối file (sau `_stream_graph_to_queue`):
    ```python
    @dataclass
    class SuggestionItem:
        label: str
        action_key: str


    class GetSuggestionsUseCase:
        """AC#1, #2: Trả về danh sách gợi ý hành động dựa trên trạng thái dự án.
        Mock LLM adapter — logic thuần Python, không gọi vector DB hay LLM thật.
        """

        def execute(self, dto: "GetSuggestionsDTO") -> list[SuggestionItem]:
            if dto.document_count == 0:
                return [
                    SuggestionItem(label="Tải tài liệu lên", action_key="open_upload"),
                    SuggestionItem(label="Tìm kiếm bài báo", action_key="focus_search"),
                    SuggestionItem(label="Xem bản đồ tri thức", action_key="navigate_graph"),
                ]
            if dto.has_draft:
                return [
                    SuggestionItem(label="Tiếp tục soạn thảo", action_key="navigate_writing"),
                    SuggestionItem(label="Tìm kiếm thêm tài liệu", action_key="focus_search"),
                    SuggestionItem(label="Xem bản đồ tri thức", action_key="navigate_graph"),
                ]
            return [
                SuggestionItem(label="Xem bản đồ tri thức", action_key="navigate_graph"),
                SuggestionItem(label="Tìm kiếm thêm tài liệu", action_key="focus_search"),
                SuggestionItem(label="Bắt đầu soạn thảo", action_key="navigate_writing"),
            ]
    ```
  - **Lưu ý**: `SuggestionItem` dùng `@dataclass` theo convention domain entities. Import `dataclass` ở đầu file đã có sẵn (file dùng `@dataclass` cho DTOs).

- [x] **Task 6**: Thêm Pydantic schemas vào `backend/src/modules/orchestrator/presentation/schemas.py`
  - [x] 6.1 Thêm vào cuối file:
    ```python
    class GetSuggestionsRequest(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        active_tab: str = Field(..., description="Tab đang active: library | graph | writing")
        document_count: int = Field(..., ge=0)
        has_draft: bool = False


    class SuggestionItemResponse(BaseModel):
        model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
        label: str
        action_key: str
    ```

- [x] **Task 7**: Thêm endpoint vào `backend/src/modules/orchestrator/presentation/router.py`
  - [x] 7.1 Thêm imports (nếu chưa có):
    ```python
    from backend.src.modules.orchestrator.application.dtos import GetSuggestionsDTO
    from backend.src.modules.orchestrator.application.use_cases import GetSuggestionsUseCase
    from backend.src.modules.orchestrator.presentation.schemas import (
        GetSuggestionsRequest,
        SuggestionItemResponse,
    )
    ```
  - [x] 7.2 Thêm route mới sau các routes hiện có:
    ```python
    @router.post("/chat/suggestions", response_model=list[SuggestionItemResponse])
    async def get_suggestions(
        request: GetSuggestionsRequest,
        current_user: User = Depends(get_current_user),
    ) -> list[SuggestionItemResponse]:
        use_case = GetSuggestionsUseCase()
        items = use_case.execute(
            GetSuggestionsDTO(
                active_tab=request.active_tab,
                document_count=request.document_count,
                has_draft=request.has_draft,
            )
        )
        return [SuggestionItemResponse(label=item.label, action_key=item.action_key) for item in items]
    ```
  - **Lưu ý**: `GetSuggestionsUseCase` không cần inject repository vì không đụng DB. Gọi trực tiếp `GetSuggestionsUseCase()`.

### FRONTEND — API Client (AC#1, #6)

- [x] **Task 8**: Thêm `getSuggestions()` vào `frontend/src/api/chat.ts`
  - [x] 8.1 Thêm type và function:
    ```typescript
    export interface Suggestion {
      label: string;
      actionKey: string;
    }

    export interface SuggestionsRequest {
      activeTab: string;
      documentCount: number;
      hasDraft: boolean;
    }

    export async function getSuggestions(payload: SuggestionsRequest): Promise<Suggestion[]> {
      const { data } = await apiClient.post<Suggestion[]>('/api/chat/suggestions', payload);
      return data;
    }
    ```

### FRONTEND — ChatbotPanel.tsx (AC#3, #4, #5, #6)

- [x] **Task 9**: Cập nhật `ChatbotPanel.tsx` — thêm Quick Reply Buttons
  - [x] 9.1 Thêm imports:
    ```typescript
    import { useWorkspaceStore } from '@/store/workspaceStore';
    import { getSuggestions, type Suggestion } from '@/api/chat';
    ```
  - [x] 9.2 Thêm state suggestions trong component (sau `const [inputValue, setInputValue] = useState('')`):
    ```typescript
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    ```
  - [x] 9.3 Đọc từ workspaceStore:
    ```typescript
    const activeTab = useWorkspaceStore((s) => s.activeTab);
    const documentCount = useWorkspaceStore((s) => s.documentCount);
    const setActiveTab = useWorkspaceStore((s) => s.setActiveTab);
    const setUploadModalOpen = useWorkspaceStore((s) => s.setUploadModalOpen);
    ```
  - [x] 9.4 Thêm `useEffect` fetch suggestions khi `activeProjectId` hoặc `documentCount` thay đổi:
    ```typescript
    useEffect(() => {
      if (!activeProjectId) {
        setSuggestions([]);
        return;
      }
      getSuggestions({
        activeTab,
        documentCount,
        hasDraft: false,
      })
        .then(setSuggestions)
        .catch(() => setSuggestions([]));
    }, [activeProjectId, documentCount, activeTab]);
    ```
  - [x] 9.5 Thêm hàm xử lý click suggestion:
    ```typescript
    function handleSuggestionClick(actionKey: string) {
      switch (actionKey) {
        case 'open_upload':
          setActiveTab('library');
          setUploadModalOpen(true);
          break;
        case 'navigate_library':
          setActiveTab('library');
          break;
        case 'navigate_graph':
          setActiveTab('graph');
          break;
        case 'navigate_writing':
          setActiveTab('writing');
          break;
        case 'focus_search':
          setActiveTab('library');
          break;
        default:
          break;
      }
    }
    ```
  - [x] 9.6 Thêm Quick Reply Buttons vào JSX — đặt **giữa `messages` div và `inputArea` div**:
    ```tsx
    {suggestions.length > 0 && !isStreaming && (
      <div className={styles.suggestions}>
        {suggestions.map((s) => (
          <button
            key={s.actionKey}
            className={styles.suggestionPill}
            onClick={() => handleSuggestionClick(s.actionKey)}
            type="button"
          >
            {s.label}
          </button>
        ))}
      </div>
    )}
    ```
    **Vị trí**: Đặt ngay trước `<div className={styles.inputArea}>`.

### FRONTEND — ChatbotPanel.module.css (AC#3)

- [x] **Task 10**: Thêm styles cho suggestions pills vào `ChatbotPanel.module.css`
  - [x] 10.1 Thêm vào cuối file:
    ```css
    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      padding: 6px 12px 2px;
    }

    .suggestionPill {
      padding: 4px 10px;
      background: none;
      border: 1px solid var(--accent-blue);
      border-radius: 12px;
      color: var(--accent-blue);
      font-size: 11px;
      cursor: pointer;
      white-space: nowrap;
      transition: background 0.15s, color 0.15s;
    }

    .suggestionPill:hover {
      background: var(--accent-blue);
      color: white;
    }
    ```

### FRONTEND — i18n (không cần thiết)

Không cần thêm i18n key cho story này — label suggestion trả trực tiếp từ API (tiếng Việt hardcode trong use case). Nếu cần đa ngôn ngữ, bổ sung ở story sau.

### BACKEND — Unit Tests (AC#1, #2)

- [x] **Task 11**: Thêm unit tests cho `GetSuggestionsUseCase`
  - [x] 11.1 Tạo hoặc cập nhật `tests/unit/orchestrator/test_suggestions.py`:
    ```python
    """Unit tests cho GetSuggestionsUseCase (AC #1, #2)."""
    import pytest
    from backend.src.modules.orchestrator.application.dtos import GetSuggestionsDTO
    from backend.src.modules.orchestrator.application.use_cases import GetSuggestionsUseCase


    def _uc() -> GetSuggestionsUseCase:
        return GetSuggestionsUseCase()


    def test_suggestions_empty_project_returns_upload_first():
        result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=0, has_draft=False))
        assert len(result) == 3
        assert result[0].action_key == "open_upload"


    def test_suggestions_with_documents_no_draft():
        result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=5, has_draft=False))
        assert len(result) == 3
        action_keys = [r.action_key for r in result]
        assert "open_upload" not in action_keys
        assert "navigate_graph" in action_keys


    def test_suggestions_with_draft():
        result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=5, has_draft=True))
        assert result[0].action_key == "navigate_writing"


    def test_suggestions_all_have_label_and_action_key():
        result = _uc().execute(GetSuggestionsDTO(active_tab="library", document_count=0, has_draft=False))
        for item in result:
            assert item.label
            assert item.action_key
    ```
  - [x] 11.2 Chạy tests: `python -m pytest tests/unit/orchestrator/test_suggestions.py -v`

---

## Dev Notes

### Bối Cảnh & Mục Tiêu

Story này bổ sung tính năng **Context-Aware Guidance** (FR-15 trong PRD): chatbot chủ động gợi ý hành động dựa trên trạng thái dự án (tab hiện tại, số tài liệu, có bản thảo không). MVP dùng mock logic thuần Python thay vì gọi LLM thật — tương tự `mock_rag_node` trong story 3.2.

### Thay Đổi Kiến Trúc Quan Trọng: workspaceStore

**Vấn đề:** `CenterWorkspace` giữ `activeTab` là local state → `ChatbotPanel` không thể đọc và không thể điều hướng tab.

**Giải pháp:** Tạo `workspaceStore` (Zustand) chứa `activeTab`, `documentCount`, `isUploadModalOpen`. Cả `CenterWorkspace`, `LibraryTab`, và `ChatbotPanel` đều subscribe/publish vào store này.

**Pattern nhất quán:** Giống `chatStore`, `projectStore`, `languageStore`, `themeStore` — tất cả đều là Zustand store riêng biệt theo domain.

### Pitfalls Cần Tránh

1. **`isUploadModalOpen` phải reset khi đóng LibraryTab** — hiện tại LibraryTab ẩn/hiện qua `display: none` (không unmount). Khi store `isUploadModalOpen = true` mà LibraryTab ẩn, modal không render. Điều này OK — modal chỉ hiện khi tab Library active. Đảm bảo `setActiveTab('library')` được gọi TRƯỚC `setUploadModalOpen(true)` trong `handleSuggestionClick`.

2. **`documentCount` lag vì LibraryTab lazy load** — lần đầu vào dashboard, `documentCount = 0` cho đến khi LibraryTab load xong papers. Suggestions fetch có thể trả về "empty project" gợi ý dù dự án có tài liệu. Chấp nhận cho MVP — refresh lại sau khi papers load xong (useEffect đã cover).

3. **suggestions fetch race condition** — nếu user đổi project nhanh, 2 fetch bay cùng lúc; response cũ về sau đè response mới. Mitigate bằng cách set `setSuggestions([])` ngay khi `activeProjectId` thay đổi (đã làm trong useEffect cleanup `return`). Nếu cần strict: dùng AbortController (xem pattern ở ProjectsPage — defer sang sau nếu không bị).

4. **Không bọc `getSuggestions` trong chat loading** — suggestions là UI enhancement, không liên quan đến `isStreaming`. Pills ẩn khi `isStreaming` (đã guard trong JSX: `!isStreaming`) để không nhiễu loạn UX khi AI đang trả lời.

5. **`SuggestionItem` là dataclass, không phải Pydantic** — nằm trong application layer, không phải presentation. Pydantic schema `SuggestionItemResponse` chỉ ở presentation layer. Giống pattern `ChatThread` domain entity vs `ChatThreadResponse` schema.

6. **`GetSuggestionsUseCase` không cần dependency injection** — không gọi DB, không gọi LLM, không có external dependency. Khởi tạo trực tiếp `GetSuggestionsUseCase()` trong router, không qua `Depends()`.

7. **`active_tab` validation trong backend** — không cần strict enum validation cho MVP (spec chỉ yêu cầu string). Nếu sau này cần: thêm `Literal['library', 'graph', 'writing']` type hint trong DTO.

8. **workspaceStore và CenterWorkspace type** — `CenterWorkspace.tsx` hiện có `type TabKey = 'library' | 'graph' | 'writing'`. Sau khi chuyển sang store, type này thừa và cần xóa hoặc export từ workspaceStore. Cách sạch nhất: export `TabKey` từ `workspaceStore.ts` và import vào bất kỳ nơi nào cần.

### Module & File Map

**Backend — Files UPDATE:**
- `backend/src/modules/orchestrator/application/dtos.py` (thêm `GetSuggestionsDTO`)
- `backend/src/modules/orchestrator/application/use_cases.py` (thêm `SuggestionItem` + `GetSuggestionsUseCase`)
- `backend/src/modules/orchestrator/presentation/schemas.py` (thêm `GetSuggestionsRequest`, `SuggestionItemResponse`)
- `backend/src/modules/orchestrator/presentation/router.py` (thêm route `POST /chat/suggestions`)

**Backend — Files NEW:**
- `tests/unit/orchestrator/test_suggestions.py`

**Frontend — Files NEW:**
- `frontend/src/store/workspaceStore.ts`

**Frontend — Files UPDATE:**
- `frontend/src/features/workspace/CenterWorkspace.tsx` (thay local state bằng workspaceStore)
- `frontend/src/features/workspace/LibraryTab.tsx` (thay showUpload local state + sync documentCount)
- `frontend/src/features/workspace/ChatbotPanel.tsx` (thêm suggestions fetch + pill buttons)
- `frontend/src/features/workspace/ChatbotPanel.module.css` (thêm `.suggestions`, `.suggestionPill`)
- `frontend/src/api/chat.ts` (thêm `getSuggestions` + `Suggestion` type)

### API Endpoint Summary

| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| POST | `/api/chat/suggestions` | JWT cookie | `{activeTab, documentCount, hasDraft}` | `[{label, actionKey}]` (200) |

Tất cả endpoints của Story 3.1 và 3.2 **KHÔNG THAY ĐỔI**.

### Import Patterns

Backend (theo convention hiện có):
```python
from backend.src.modules.orchestrator.application.dtos import GetSuggestionsDTO
from backend.src.modules.orchestrator.application.use_cases import GetSuggestionsUseCase
from backend.src.modules.orchestrator.presentation.schemas import GetSuggestionsRequest, SuggestionItemResponse
```

Frontend (theo path alias `@/`):
```typescript
import { useWorkspaceStore } from '@/store/workspaceStore';
import { getSuggestions, type Suggestion } from '@/api/chat';
```

### Files Cần Đọc Trước Khi Implement

Files UPDATE — đọc kỹ trước khi sửa:
- `frontend/src/features/workspace/CenterWorkspace.tsx` — hiểu cấu trúc tab hiện tại
- `frontend/src/features/workspace/LibraryTab.tsx` — tìm tất cả `showUpload`/`setShowUpload` cần thay
- `frontend/src/features/workspace/ChatbotPanel.tsx` — hiểu layout và state hiện có
- `backend/src/modules/orchestrator/application/use_cases.py` — thêm đúng chỗ, không xung đột import
- `backend/src/modules/orchestrator/presentation/router.py` — thêm imports và route đúng thứ tự

Files tham khảo pattern:
- `frontend/src/store/chatStore.ts` — Zustand store pattern hiện có
- `backend/src/modules/orchestrator/application/dtos.py` — `@dataclass` DTO pattern
- `backend/src/modules/orchestrator/presentation/schemas.py` — `alias_generator=to_camel` pattern

### Learnings từ Story 3.2

1. **`alias_generator=to_camel, populate_by_name=True`** — bắt buộc cho tất cả Pydantic schemas presentation. Frontend nhận `camelCase`, backend internal `snake_case`.
2. **`sonner` toast** (không phải `react-hot-toast`) — codebase đã migrate sang `sonner` (patch trong review 3.2). Không import `toast` từ bất kỳ thư viện khác.
3. **`withCredentials: true` cho EventSource** — auth qua cookie httponly; pattern đã có trong ChatbotPanel.
4. **`useEffect` cleanup** — pattern reset state khi `activeProjectId` thay đổi đã có trong ChatbotPanel (`reset()`). Thêm `setSuggestions([])` vào cùng useEffect hoặc useEffect riêng.
5. **Không dùng `asyncio.create_task` cho sync operations** — `GetSuggestionsUseCase.execute()` là sync method thông thường, không cần `async def`. Chỉ cần `def execute(...)`.

### CSS Variables Available

Từ DESIGN.md (AcademicPaper design system):
- `--accent-blue`: `#2563EB` — dùng cho border và text pill
- `--surface-hover`: background hover state
- `--border-hairline`: `#E2E8F0`
- `--ink-primary`, `--ink-secondary`

Pill style: border `--accent-blue`, hover fill `--accent-blue` với text white — khớp design system.

### Thứ Tự Implement Đề Xuất

1. Task 1 (workspaceStore) → Task 2 (CenterWorkspace) → Task 3 (LibraryTab) — thiết lập nền tảng shared state
2. Task 4-7 (Backend API) — independent, có thể song song với frontend
3. Task 8 (API client) → Task 9-10 (ChatbotPanel UI) — sau khi backend sẵn sàng
4. Task 11 (Unit tests) — sau khi backend hoàn thành

### References

- [Source: epics.md Story 3.6] — Context-Aware Suggestion API AC
- [Source: epics.md Story 3.7] — Quick Reply Action UI AC
- [Source: architecture.md Section 8.2] — Context-Aware User Guiding: `ui_context` payload, `suggested_actions` pattern
- [Source: PRD FR-15] — Context-Aware User Guiding requirements
- [Source: frontend/src/store/chatStore.ts] — Zustand store pattern tham khảo
- [Source: frontend/src/features/workspace/ChatbotPanel.tsx] — Component cần update chính
- [Source: frontend/src/features/workspace/CenterWorkspace.tsx] — Source của activeTab hiện tại
- [Source: frontend/src/features/workspace/LibraryTab.tsx] — Source của showUpload và papers.length

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Không có lỗi nghiêm trọng. Router có prefix `/chat`, route bên trong phải là `/suggestions` (không phải `/chat/suggestions`).
- Test flaky `test_delete_project_writes_sync_outbox_event` là pre-existing (chạy isolated thì pass, full suite fail do ordering — không liên quan đến changes này).

### Completion Notes List

- Tạo `workspaceStore.ts` (Zustand) để share `activeTab`, `documentCount`, `isUploadModalOpen` giữa CenterWorkspace, LibraryTab, và ChatbotPanel.
- CenterWorkspace chuyển từ local `useState` sang `useWorkspaceStore` cho tab navigation.
- LibraryTab chuyển `showUpload` local state sang `isUploadModalOpen` trong store; thêm useEffect sync `papers.length` → `documentCount` trong store.
- Backend: thêm `GetSuggestionsDTO`, `SuggestionItem`, `GetSuggestionsUseCase` (mock logic thuần Python), Pydantic schemas `GetSuggestionsRequest`/`SuggestionItemResponse`, endpoint `POST /chat/suggestions`.
- Frontend API client: thêm `getSuggestions()` + types `Suggestion`/`SuggestionsRequest`.
- ChatbotPanel: thêm suggestions state, fetch useEffect, handler `handleSuggestionClick`, và Quick Reply Buttons JSX trước inputArea.
- CSS: thêm `.suggestions` và `.suggestionPill` styles với hover effect.
- Unit tests: 4 tests pass cho `GetSuggestionsUseCase` (AC#1, AC#2).
- TypeScript: không có lỗi type.

### File List

- `frontend/src/store/workspaceStore.ts` (mới)
- `frontend/src/features/workspace/CenterWorkspace.tsx` (cập nhật)
- `frontend/src/features/workspace/LibraryTab.tsx` (cập nhật)
- `frontend/src/features/workspace/ChatbotPanel.tsx` (cập nhật)
- `frontend/src/features/workspace/ChatbotPanel.module.css` (cập nhật)
- `frontend/src/api/chat.ts` (cập nhật)
- `backend/src/modules/orchestrator/application/dtos.py` (cập nhật)
- `backend/src/modules/orchestrator/application/use_cases.py` (cập nhật)
- `backend/src/modules/orchestrator/presentation/schemas.py` (cập nhật)
- `backend/src/modules/orchestrator/presentation/router.py` (cập nhật)
- `tests/unit/orchestrator/test_suggestions.py` (mới)

### Change Log

- 2026-06-17: Tạo story 3.3 — Chatbot Đinh Hướng Dựa Trên Trạng Thái Dự Án. Bao gồm Epic 3.6 (Backend Suggestions API) + Epic 3.7 (Quick Reply Action UI). (create-story agent: claude-sonnet-4-6)
- 2026-06-17: Implement toàn bộ 11 tasks — workspaceStore Zustand, CenterWorkspace refactor, LibraryTab store sync, Backend Suggestions API (DTO + UseCase + Schema + Router), Frontend API client, ChatbotPanel Quick Reply Buttons + CSS. 4 unit tests pass. TypeScript clean. (dev agent: claude-sonnet-4-6)
- 2026-06-17: Code review (bmad-code-review, 3 lớp: Blind Hunter + Edge Case Hunter + Acceptance Auditor). 2 patch đã sửa, 6 dismiss by-design, 0 defer. Status → done. (review agent: claude-opus-4-8)

### Review Findings

**Code review 2026-06-17 — 2 patch (đã sửa), 6 dismiss, 0 defer.** Tất cả 6 AC được xác nhận đạt; routing `/api/chat/suggestions` khớp FE↔BE; camelCase serialize đúng.

Patch (đã áp dụng):

- [x] [Review][Patch] Stale `documentCount` + upload-modal rò rỉ khi đổi project [frontend/src/features/workspace/LibraryTab.tsx:42] — `workspaceStore` là singleton, không reset khi đổi project → suggestions của project mới có thể tính bằng số tài liệu của project cũ; modal upload dính sang project khác. Fix: reset `papers` (→ `documentCount` đồng bộ về 0 rồi nạp lại) và `isUploadModalOpen` trong `useEffect` theo `projectId`.
- [x] [Review][Patch] Race condition khi fetch suggestions [frontend/src/features/workspace/ChatbotPanel.tsx:62] — `useEffect` fetch không có guard hủy; đổi project/tab nhanh có thể để response cũ đè response mới. Fix: thêm cờ `cancelled` + cleanup (đúng pattern `DocumentList`).

Dismiss (by-design theo spec, không sửa):

- [x] [Review][Dismiss] `has_draft` hardcode `false` ở FE → nhánh draft backend tạm "dead" — đúng theo Task 9.4, ngoài phạm vi AC của 3.3.
- [x] [Review][Dismiss] `active_tab` không ảnh hưởng logic backend & không validate enum — đúng Pitfall #7 (MVP, contract dự phòng cho tab-aware sau này).
- [x] [Review][Dismiss] Handler có nhánh `navigate_library` mà backend hiện không phát — AC#4 liệt kê `navigate_library` là actionKey hợp lệ, handler đúng theo contract.
- [x] [Review][Dismiss] Suggestions refetch khi đổi tab (deps có `activeTab`) — đúng chủ ý Task 9.4 + kiến trúc ui_context tab-aware; race đã được guard ở patch trên.
- [x] [Review][Dismiss] FE không `slice(0,3)` cho "tối đa 3 pill" — backend luôn trả đúng 3 (AC#3 vẫn đạt).
- [x] [Review][Dismiss] `document_count` không có cận trên (`le`) — MVP chỉ phân nhánh `==0` vs `>0`, vô hại.
