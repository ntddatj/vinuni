---
baseline_commit: 55f3f7b
---

# Story 2.3: [BE+FE] Gợi ý phân ngành MECE cho chủ đề quá rộng

Status: done

## Story

Với vai trò là người dùng đã đăng nhập,
Tôi muốn hệ thống phát hiện khi tôi tìm kiếm một chủ đề quá rộng và đề xuất các phân ngành MECE,
Để tôi có thể nhanh chóng thu hẹp tìm kiếm về kết quả học thuật chính xác hơn bằng một cú click.

## Acceptance Criteria

1. **Given** người dùng nhập từ khóa rất rộng (ví dụ: "AI", "Machine Learning")
   **When** Backend nhận request `GET /api/search?q={keyword}`
   **Then** nếu tổng số kết quả khả dụng từ arXiv hoặc Semantic Scholar vượt `BROAD_QUERY_THRESHOLD` (mặc định: 50)
   **And** response gồm `"isBroadQuery": true` và mảng `"suggestions": ["NLP", "Computer Vision", ...]` (3-5 subfields)

2. **Given** truy vấn được phát hiện là rộng và có `isBroadQuery = true`
   **When** Frontend nhận response
   **Then** hiển thị hàng chip gợi ý phân ngành ngay bên dưới thanh tìm kiếm
   **And** các chip có style: viền `var(--border-hairline)`, bo góc `var(--rounded-sm)` (4px), nền `var(--surface-raised)`, chữ `var(--accent-blue)`
   **And** hover chip: đổi nền sang `var(--accent-blue)` nhạt (opacity 0.1)

3. **Given** các chip gợi ý đang hiển thị
   **When** người dùng click vào một chip (ví dụ: "Computer Vision")
   **Then** ô input tìm kiếm được tự động điền bằng text của chip đó
   **And** tìm kiếm mới được trigger tức thì (không cần bấm nút)
   **And** hàng chip cũ biến mất (kết quả mới không có broad query)

4. **Given** truy vấn không phải rộng (ví dụ: "transformer attention mechanism NLP")
   **When** response trả về
   **Then** `"isBroadQuery": false` và `"suggestions": []`
   **And** Frontend không hiển thị chip nào

5. **Given** Gemini API lỗi hoặc timeout khi sinh gợi ý
   **When** xảy ra lỗi LLM
   **Then** Backend vẫn trả về `"isBroadQuery": true` nhưng `"suggestions": []`
   **And** Frontend không hiển thị chip (không hiển thị hàng chip rỗng)
   **And** lỗi Gemini được log ở WARNING (không raise exception, không ảnh hưởng kết quả tìm kiếm)

6. **Given** đang ở tab "Thư viện Tài liệu"
   **When** chuyển ngôn ngữ VI|EN trên Header
   **Then** label tooltip và aria-label của chip đổi ngôn ngữ ngay lập tức (chip text giữ nguyên vì là tên ngành học thuật tiếng Anh)

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI: Gõ "AI" → bấm Tìm kiếm → thấy danh sách paper cards + hàng 3-5 nút chip phân ngành (ví dụ: "NLP", "Computer Vision") xuất hiện ngay dưới thanh tìm kiếm. Click "Computer Vision" → input tự điền "Computer Vision" và kết quả tìm kiếm mới xuất hiện, không còn chip.

---

## Tasks / Subtasks

### BACKEND — Mở rộng module `search`

- [x] Task 1: Cập nhật domain entities (AC: #1, #4, #5)
  - [x] 1.1 Thêm `@dataclass class ClientSearchResult` vào `backend/src/modules/search/domain/entities.py`:
    ```python
    @dataclass
    class ClientSearchResult:
        papers: list[PaperResult]
        total_available: int  # Tổng kết quả có thể có từ API nguồn
    ```
  - [x] 1.2 Thêm `is_broad_query: bool = False` và `suggestions: list[str] = field(default_factory=list)` vào `SearchResponse` (thay thế comment placeholder ở dòng 21)

- [x] Task 2: Cập nhật ArxivClient để trả về total count (AC: #1)
  - [x] 2.1 Sửa `backend/src/modules/search/infrastructure/arxiv_client.py`:
    - Đổi return type `search()` thành `ClientSearchResult`
    - Parse `<opensearch:totalResults>` từ Atom XML (namespace: `http://a9.com/-/spec/opensearch/1.1/`)
    - Nếu không parse được `totalResults` → `total_available = len(papers)` (fallback an toàn)
    - Trả về `ClientSearchResult(papers=results, total_available=total)`

- [x] Task 3: Cập nhật SemanticScholarClient để trả về total count (AC: #1)
  - [x] 3.1 Sửa `backend/src/modules/search/infrastructure/semantic_scholar_client.py`:
    - Đổi return type `search()` thành `ClientSearchResult`
    - Đọc `data.get("total", 0)` từ S2 JSON response (field `total` đã có trong response hiện tại)
    - Trả về `ClientSearchResult(papers=results, total_available=total)`

- [x] Task 4: Tạo BroadQueryDetector (AC: #1, #5)
  - [x] 4.1 Tạo `backend/src/modules/search/infrastructure/broad_query_detector.py`:
    - Class `BroadQueryDetector` nhận `user_id: str`, `db: AsyncSession`
    - Method `async detect(query: str, total_available: int) -> tuple[bool, list[str]]`
    - Nếu `total_available <= threshold` → return `(False, [])`
    - Nếu `total_available > threshold` → gọi Gemini qua LLMRouter, return `(True, suggestions)`
    - Graceful fallback: nếu LLMRouter/Gemini lỗi → log WARNING, return `(True, [])` (KHÔNG raise)
    - Xem Dev Notes § BroadQueryDetector cho prompt template và chi tiết
  - [x] 4.2 Thêm `broad_query_threshold: int = 50` vào class `Settings` trong `backend/src/shared/infra/settings.py`

- [x] Task 5: Cập nhật SearchPapersUseCase (AC: #1, #4, #5)
  - [x] 5.1 Sửa `backend/src/modules/search/application/use_cases.py`:
    - Constructor nhận thêm `detector: BroadQueryDetector`
    - Sau khi lấy kết quả từ 2 clients, tính `max_total = max(arxiv_result.total_available, s2_result.total_available)`
    - Gọi `detector.detect(query, max_total)` để lấy `(is_broad, suggestions)`
    - Cập nhật `SearchResponse` với `is_broad_query=is_broad, suggestions=suggestions`
    - Cache: vẫn chỉ cache khi `not warnings` (đủ 2 nguồn). Lưu `is_broad_query` và `suggestions` cùng response vào cache
    - Cập nhật `SearchCache.get/set` để serialize/deserialize 2 field mới

- [x] Task 6: Cập nhật SearchCache (AC: #1)
  - [x] 6.1 Sửa `backend/src/modules/search/infrastructure/search_cache.py`:
    - Thêm `is_broad_query` và `suggestions` vào data dict khi serialize (`set`)
    - Thêm `is_broad_query=data.get("is_broad_query", False)` và `suggestions=data.get("suggestions", [])` khi deserialize (`get`)

- [x] Task 7: Cập nhật Presentation layer (AC: #1, #4)
  - [x] 7.1 Sửa `backend/src/modules/search/presentation/schemas.py`:
    - Thêm `is_broad_query: bool` và `suggestions: list[str]` vào `SearchResponseSchema`
    - camelCase tự động qua `alias_generator=to_camel`: `isBroadQuery`, `suggestions`
  - [x] 7.2 Sửa `backend/src/modules/search/presentation/router.py`:
    - Thêm dependency `db: AsyncSession = Depends(get_db)` (import từ `backend.src.shared.infra.database`)
    - Khởi tạo `BroadQueryDetector(user_id=_current_user.id, db=db)` và truyền vào `SearchPapersUseCase`
    - Map `is_broad_query` và `suggestions` vào `SearchResponseSchema` khi build response

### FRONTEND — Cập nhật LibraryTab

- [x] Task 8: Cập nhật Types (AC: #1, #4)
  - [x] 8.1 Sửa `frontend/src/types/search.ts`:
    - Thêm `isBroadQuery: boolean` và `suggestions: string[]` vào interface `SearchResponse`

- [x] Task 9: Cập nhật LibraryTab component (AC: #2, #3, #4, #5, #6)
  - [x] 9.1 Sửa `frontend/src/features/workspace/LibraryTab.tsx`:
    - Render `<BroadQuerySuggestions>` component ngay sau `<div className={styles.searchBar}>`
    - Chỉ hiển thị khi `searchResult?.isBroadQuery && searchResult.suggestions.length > 0`
    - Click chip: gọi `setQuery(suggestion)` rồi trigger `handleSearch()` với suggestion đó
    - Xem Dev Notes § LibraryTab Updates cho code template

- [x] Task 10: Thêm CSS cho chip gợi ý (AC: #2)
  - [x] 10.1 Sửa `frontend/src/features/workspace/LibraryTab.module.css`:
    - Thêm `.suggestionsBar` — flex row, flex-wrap, gap 8px, padding 8px 0
    - Thêm `.suggestionChip` — border `1px solid var(--border-hairline)`, `border-radius: var(--rounded-sm)` (4px), background `var(--surface-raised)`, color `var(--accent-blue)`, font-size 12px, padding 4px 10px, cursor pointer, transition background 0.15s
    - Thêm `.suggestionChip:hover` — background `rgba(37, 99, 235, 0.1)` (accent-blue ~10% opacity)

- [x] Task 11: Thêm Translation Keys (AC: #6)
  - [x] 11.1 Sửa `frontend/src/i18n/translations.ts`:
    - Thêm `'search.broadQueryHint'`, `'search.suggestionAriaLabel'` (xem Dev Notes § Translation Keys)

- [x] Task 12: Cập nhật Tests (AC: #1-5)
  - [x] 12.1 Sửa `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx`:
    - Cập nhật `MOCK_RESULT` để thêm `isBroadQuery: false, suggestions: []`
    - Thêm test: "hiển thị chip gợi ý khi isBroadQuery = true"
    - Thêm test: "click chip gợi ý trigger tìm kiếm mới"
    - Thêm test: "không hiển thị chip khi suggestions rỗng dù isBroadQuery = true" (AC #5 graceful fallback)

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG dùng Tailwind** — CSS Modules + CSS Variables `AcademicPaper`. Dùng `var(--border-hairline)`, `var(--rounded-sm)`, `var(--surface-raised)`, `var(--accent-blue)`.

2. **KHÔNG dùng `i18next`** — dùng `useTranslation()` từ `frontend/src/i18n/useTranslation.ts`.

3. **KHÔNG quên tham số thứ 2 của `getErrorMessage(err, 'fallback')`** — thiếu sẽ lỗi `TS2554`.

4. **KHÔNG tạo Axios client mới** — dùng `apiClient` từ `frontend/src/api/client.ts`.

5. **KHÔNG bỏ `MemoryRouter`** khi render component có `Link`/`useNavigate` trong test.

6. **KHÔNG để LLM failure block search** — `BroadQueryDetector` phải wrap mọi LLM call trong try/except và graceful fallback về `(True, [])` khi lỗi.

7. **KHÔNG raise exception từ BroadQueryDetector** — lỗi Gemini chỉ log WARNING, không ảnh hưởng response tìm kiếm.

8. **KHÔNG hiển thị chip rỗng** — Frontend chỉ render `<BroadQuerySuggestions>` khi `suggestions.length > 0`.

9. **KHÔNG quên TranslationKey type** — `t()` nhận `TranslationKey`, không phải `string`. Thêm key mới vào `translations.ts` trước khi dùng.

10. **KHÔNG inject db dependency trong test** — mock `BroadQueryDetector.detect()` ở layer use case trong unit tests.

11. **KHÔNG sửa interface client `search()`** mà không cập nhật cả `ArxivClient` và `SemanticScholarClient` cùng lúc — `SearchPapersUseCase` dùng cả hai.

---

### § Domain Entities — Cập nhật `entities.py`

```python
# backend/src/modules/search/domain/entities.py
from dataclasses import dataclass, field


@dataclass
class PaperResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str
    doi: str | None
    arxiv_id: str | None
    url: str
    pdf_url: str | None
    source: str  # "arxiv" | "semantic_scholar"


@dataclass
class ClientSearchResult:
    papers: list[PaperResult]
    total_available: int  # Tổng kết quả có thể có từ API nguồn (để detect broad query)


@dataclass
class SearchResponse:
    results: list[PaperResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_broad_query: bool = False
    suggestions: list[str] = field(default_factory=list)
```

---

### § ArxivClient — Cập nhật `arxiv_client.py`

arXiv Atom XML có namespace `opensearch`: `http://a9.com/-/spec/opensearch/1.1/`

```python
OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"

async def search(self, query: str, limit: int = 10) -> ClientSearchResult:
    # ... (giữ nguyên HTTP request + retry logic)
    return self._parse_atom(response.text, limit)

def _parse_atom(self, xml_text: str, limit: int) -> ClientSearchResult:
    root = ET.fromstring(xml_text)
    
    # Parse total count
    total_el = root.find(f"{{{OPENSEARCH_NS}}}totalResults")
    try:
        total_available = int(total_el.text) if total_el is not None and total_el.text else 0
    except (ValueError, AttributeError):
        total_available = 0
    
    results = []
    for entry in root.findall(f"{{{ATOM_NS}}}entry"):
        # ... giữ nguyên parse logic hiện tại ...
        results.append(PaperResult(...))
    
    # Fallback: nếu không parse được total, dùng len(results)
    if total_available == 0:
        total_available = len(results)
    
    return ClientSearchResult(papers=results, total_available=total_available)
```

**Lưu ý:** `PaperResult` parse logic giữ nguyên từ Story 2.2 (đã có các fix: safe `.text`, re.sub version strip, HTTPS URL, v.v.). Chỉ thêm `total_available` parsing.

---

### § SemanticScholarClient — Cập nhật `semantic_scholar_client.py`

S2 response JSON: `{ "total": 12345, "data": [...] }`

```python
async def search(self, query: str, limit: int = 10) -> ClientSearchResult:
    # ... (giữ nguyên HTTP request + retry logic)
    data = response.json()
    total_available = int(data.get("total", 0))
    papers = self._parse_response(data.get("data", []))
    if total_available == 0:
        total_available = len(papers)
    return ClientSearchResult(papers=papers, total_available=total_available)
```

**`_parse_response` giữ nguyên** từ Story 2.2 (đã có các fix: int cast year, v.v.).

---

### § BroadQueryDetector — `broad_query_detector.py`

```python
# backend/src/modules/search/infrastructure/broad_query_detector.py
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.shared.infra.llm.router import LLMRouter
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)

MECE_PROMPT = """You are a research assistant helping to narrow down a broad academic search query.

The user searched for: "{query}"
The search returned {total} total available results, indicating this is a very broad topic.

Generate 4-5 MECE (Mutually Exclusive, Collectively Exhaustive) subfield suggestions to help the user narrow down their search.

Rules:
- Each suggestion must be a specific, well-known subfield or application area
- Suggestions must be in English (academic field names)
- Keep each suggestion short (1-4 words max)
- Suggestions must be relevant to the original query
- Return ONLY a JSON array of strings, nothing else

Example for "Machine Learning": ["Natural Language Processing", "Computer Vision", "Reinforcement Learning", "Graph Neural Networks"]

Respond with ONLY the JSON array:"""


class BroadQueryDetector:
    def __init__(self, user_id: str, db: AsyncSession) -> None:
        self._user_id = user_id
        self._db = db

    async def detect(self, query: str, total_available: int) -> tuple[bool, list[str]]:
        settings = get_settings()
        threshold = settings.broad_query_threshold

        if total_available <= threshold:
            return False, []

        # Broad query detected — gọi Gemini để sinh MECE suggestions
        try:
            router = LLMRouter(self._db)
            llm = await router.get_llm_client(self._user_id, model_name="gemini-2.5-flash")
            prompt = MECE_PROMPT.format(query=query, total=total_available)
            result = await llm.ainvoke(prompt)
            content = result.content.strip()
            suggestions = json.loads(content)
            if isinstance(suggestions, list):
                return True, [str(s) for s in suggestions[:5]]
        except Exception as e:
            logger.warning(
                "BroadQueryDetector: không thể sinh gợi ý MECE cho query '%s': %s",
                query, e,
            )

        return True, []
```

**Lưu ý quan trọng:**
- `LLMRouter` tại `backend/src/shared/infra/llm/router.py` đã tồn tại từ Story 2.1
- `LLMRouter.get_llm_client()` trả về `ChatGoogleGenerativeAI` từ `langchain_google_genai`
- `langchain_google_genai>=2.0.0` đã có trong `requirements.txt`
- Gọi `llm.ainvoke(prompt)` (async) → `result.content` là string
- Fallback: nếu JSON parse thất bại hoặc bất kỳ lỗi nào → return `(True, [])`, KHÔNG raise

---

### § Settings — Thêm `broad_query_threshold`

```python
# backend/src/shared/infra/settings.py — thêm vào class Settings

# Search
broad_query_threshold: int = 50
```

Biến môi trường tương ứng: `BROAD_QUERY_THRESHOLD=50`

---

### § SearchPapersUseCase — Cập nhật `use_cases.py`

```python
# backend/src/modules/search/application/use_cases.py
import asyncio
import logging
import re
from itertools import zip_longest

from backend.src.modules.search.domain.entities import ClientSearchResult, PaperResult, SearchResponse
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.broad_query_detector import BroadQueryDetector
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient

logger = logging.getLogger(__name__)


class SearchPapersUseCase:
    def __init__(
        self,
        arxiv: ArxivClient,
        s2: SemanticScholarClient,
        cache: SearchCache,
        detector: BroadQueryDetector,
    ) -> None:
        self._arxiv = arxiv
        self._s2 = s2
        self._cache = cache
        self._detector = detector

    async def execute(self, query: str, limit: int = 10) -> SearchResponse:
        cached = await self._cache.get(query, limit)
        if cached is not None:
            return cached

        arxiv_task = asyncio.create_task(self._arxiv.search(query, limit))
        s2_task = asyncio.create_task(self._s2.search(query, limit))

        arxiv_client_result: ClientSearchResult | None = None
        s2_client_result: ClientSearchResult | None = None
        warnings: list[str] = []

        for coro, name in [
            (arxiv_task, "arxiv_timeout"),
            (s2_task, "semantic_scholar_timeout"),
        ]:
            try:
                result = await coro
                if name == "arxiv_timeout":
                    arxiv_client_result = result
                else:
                    s2_client_result = result
            except Exception as e:
                logger.warning("Tìm kiếm %s thất bại: %s", name, e, exc_info=True)
                warnings.append(name)

        arxiv_papers = arxiv_client_result.papers if arxiv_client_result else []
        s2_papers = s2_client_result.papers if s2_client_result else []
        arxiv_total = arxiv_client_result.total_available if arxiv_client_result else 0
        s2_total = s2_client_result.total_available if s2_client_result else 0

        interleaved = [p for pair in zip_longest(arxiv_papers, s2_papers) for p in pair if p is not None]
        combined = self._deduplicate(interleaved)

        # Broad query detection dùng tổng kết quả khả dụng từ nguồn dồi dào nhất
        max_total = max(arxiv_total, s2_total)
        is_broad, suggestions = await self._detector.detect(query, max_total)

        response = SearchResponse(
            results=combined[:limit],
            warnings=warnings,
            is_broad_query=is_broad,
            suggestions=suggestions,
        )

        if not warnings:
            await self._cache.set(query, limit, response)

        return response

    def _deduplicate(self, papers: list[PaperResult]) -> list[PaperResult]:
        # Giữ nguyên từ Story 2.2 (đã fix dedup bug)
        seen_dois: set[str] = set()
        seen_arxiv_ids: set[str] = set()
        unique: list[PaperResult] = []

        for p in papers:
            normalized_doi = p.doi.strip().lower() if p.doi else None
            base_id = re.sub(r'v\d+$', '', p.arxiv_id).strip() if p.arxiv_id else None

            if (normalized_doi and normalized_doi in seen_dois) or \
               (base_id and base_id in seen_arxiv_ids):
                continue

            if normalized_doi:
                seen_dois.add(normalized_doi)
            if base_id:
                seen_arxiv_ids.add(base_id)

            unique.append(p)

        return unique
```

---

### § SearchCache — Cập nhật `search_cache.py`

Thêm serialize/deserialize `is_broad_query` và `suggestions`:

```python
# Trong method get():
return SearchResponse(
    results=[PaperResult(**r) for r in data["results"]],
    warnings=data["warnings"],
    is_broad_query=data.get("is_broad_query", False),
    suggestions=data.get("suggestions", []),
)

# Trong method set():
data = {
    "results": [asdict(r) for r in response.results],
    "warnings": response.warnings,
    "is_broad_query": response.is_broad_query,
    "suggestions": response.suggestions,
}
```

---

### § Presentation Schemas — Cập nhật `schemas.py`

```python
# backend/src/modules/search/presentation/schemas.py
class SearchResponseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    results: list[PaperResultSchema]
    warnings: list[str]
    is_broad_query: bool          # → isBroadQuery (camelCase)
    suggestions: list[str]        # → suggestions (giữ nguyên)
```

---

### § Router — Cập nhật `router.py`

```python
# backend/src/modules/search/presentation/router.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.search.application.use_cases import SearchPapersUseCase
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.broad_query_detector import BroadQueryDetector
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient
from backend.src.modules.search.presentation.schemas import PaperResultSchema, SearchResponseSchema
from backend.src.shared.infra.database import get_db

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponseSchema)
async def search_papers(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(default=10, ge=1, le=50),
    _current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SearchResponseSchema:
    q_stripped = q.strip()
    if not q_stripped:
        raise HTTPException(status_code=422, detail="Query không được chỉ gồm khoảng trắng")

    arxiv = ArxivClient()
    s2 = SemanticScholarClient()
    cache = SearchCache()
    detector = BroadQueryDetector(user_id=str(_current_user.id), db=db)
    try:
        use_case = SearchPapersUseCase(arxiv=arxiv, s2=s2, cache=cache, detector=detector)
        response = await use_case.execute(q_stripped, limit)
        return SearchResponseSchema(
            results=[
                PaperResultSchema(
                    title=r.title,
                    authors=r.authors,
                    year=r.year,
                    abstract=r.abstract,
                    doi=r.doi,
                    arxiv_id=r.arxiv_id,
                    url=r.url,
                    pdf_url=r.pdf_url,
                    source=r.source,
                )
                for r in response.results
            ],
            warnings=response.warnings,
            is_broad_query=response.is_broad_query,
            suggestions=response.suggestions,
        )
    finally:
        await arxiv.aclose()
        await s2.aclose()
```

**Lưu ý:** `get_db` đã tồn tại tại `backend/src/shared/infra/database.py` (được dùng bởi các modules identity, workspace). Import đúng path này, KHÔNG tự tạo dependency mới.

---

### § Frontend Types — Cập nhật `search.ts`

```typescript
// frontend/src/types/search.ts
export interface PaperResult {
  title: string;
  authors: string[];
  year: number | null;
  abstract: string;
  doi: string | null;
  arxivId: string | null;
  url: string;
  pdfUrl: string | null;
  source: 'arxiv' | 'semantic_scholar';
}

export interface SearchResponse {
  results: PaperResult[];
  warnings: string[];
  isBroadQuery: boolean;
  suggestions: string[];
}
```

---

### § LibraryTab Updates

Thêm sub-component `BroadQuerySuggestions` vào `LibraryTab.tsx`:

```tsx
// Thêm vào cuối file LibraryTab.tsx (sau PaperCard)

interface BroadQuerySuggestionsProps {
  suggestions: string[];
  onSelect: (suggestion: string) => void;
  t: (key: TranslationKey) => string;
}

function BroadQuerySuggestions({ suggestions, onSelect, t }: BroadQuerySuggestionsProps) {
  if (suggestions.length === 0) return null;
  return (
    <div className={styles.suggestionsBar} role="group" aria-label={t('search.suggestionAriaLabel')}>
      {suggestions.map((s) => (
        <button
          key={s}
          type="button"
          className={styles.suggestionChip}
          onClick={() => onSelect(s)}
        >
          {s}
        </button>
      ))}
    </div>
  );
}
```

Cập nhật `LibraryTab`:

```tsx
// Thêm handler cho suggestion click
async function handleSuggestionClick(suggestion: string) {
  setQuery(suggestion);
  // Trigger search ngay với suggestion value (không qua state vì async)
  const currentId = ++searchIdRef.current;
  setIsSearching(true);
  setSearchResult(null);
  try {
    const result = await searchPapers(suggestion, 10);
    if (currentId !== searchIdRef.current) return;
    setSearchResult(result);
    if (result.warnings.length >= 2) {
      toast.error(t('search.bothSourcesFailed'));
    } else if (result.warnings.length === 1) {
      toast.warning(t('search.partialResults'));
    }
  } catch (err) {
    if (currentId !== searchIdRef.current) return;
    toast.error(getErrorMessage(err, t('search.searchError')));
  } finally {
    if (currentId === searchIdRef.current) {
      setIsSearching(false);
    }
  }
}

// Trong JSX — thêm sau <div className={styles.searchBar}>:
{searchResult?.isBroadQuery && searchResult.suggestions.length > 0 && (
  <BroadQuerySuggestions
    suggestions={searchResult.suggestions}
    onSelect={handleSuggestionClick}
    t={t}
  />
)}
```

**Lưu ý về handleSuggestionClick:**
- Không dùng `setQuery` rồi gọi `handleSearch()` vì React state update là async — state cũ sẽ được dùng
- Phải truyền `suggestion` trực tiếp vào `searchPapers()` thay vì đọc từ `query` state
- Vẫn dùng `searchIdRef` để tránh race condition

---

### § CSS Classes — Cập nhật `LibraryTab.module.css`

```css
/* Thêm vào cuối LibraryTab.module.css */

.suggestionsBar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0 4px;
}

.suggestionChip {
  border: 1px solid var(--border-hairline);
  border-radius: var(--rounded-sm); /* 4px */
  background: var(--surface-raised);
  color: var(--accent-blue);
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  transition: background 0.15s ease;
  white-space: nowrap;
}

.suggestionChip:hover {
  background: rgba(37, 99, 235, 0.1);
}
```

---

### § Translation Keys — Cập nhật `translations.ts`

```typescript
// Thêm vào object translations trong frontend/src/i18n/translations.ts
'search.suggestionAriaLabel': { vi: 'Gợi ý phân ngành', en: 'Subfield suggestions' },
'search.broadQueryHint': { vi: 'Chủ đề quá rộng — thử thu hẹp:', en: 'Topic too broad — try narrowing:' },
```

---

### § API Contract — GET /api/search (Updated)

**Response 200 (normal query):**
```json
{
  "results": [...],
  "warnings": [],
  "isBroadQuery": false,
  "suggestions": []
}
```

**Response 200 (broad query, Gemini OK):**
```json
{
  "results": [...],
  "warnings": [],
  "isBroadQuery": true,
  "suggestions": ["Natural Language Processing", "Computer Vision", "Reinforcement Learning", "Graph Neural Networks"]
}
```

**Response 200 (broad query, Gemini failed — graceful fallback):**
```json
{
  "results": [...],
  "warnings": [],
  "isBroadQuery": true,
  "suggestions": []
}
```

---

### § Cấu trúc File — Tổng quan

```
backend/
├── src/modules/search/
│   ├── domain/
│   │   └── entities.py              # CẬP NHẬT: +ClientSearchResult, +is_broad_query, +suggestions trên SearchResponse
│   ├── application/
│   │   └── use_cases.py             # CẬP NHẬT: +detector param, broad query detection
│   ├── infrastructure/
│   │   ├── arxiv_client.py          # CẬP NHẬT: search() trả về ClientSearchResult
│   │   ├── semantic_scholar_client.py # CẬP NHẬT: search() trả về ClientSearchResult
│   │   ├── search_cache.py          # CẬP NHẬT: serialize/deserialize is_broad_query + suggestions
│   │   └── broad_query_detector.py  # MỚI: BroadQueryDetector dùng LLMRouter + Gemini
│   └── presentation/
│       ├── schemas.py               # CẬP NHẬT: +is_broad_query, +suggestions
│       └── router.py               # CẬP NHẬT: +db dependency, +detector injection
├── src/shared/infra/
│   └── settings.py                  # CẬP NHẬT: +broad_query_threshold: int = 50

frontend/src/
├── types/
│   └── search.ts                    # CẬP NHẬT: +isBroadQuery, +suggestions
├── features/workspace/
│   ├── LibraryTab.tsx               # CẬP NHẬT: +BroadQuerySuggestions, +handleSuggestionClick
│   ├── LibraryTab.module.css        # CẬP NHẬT: +.suggestionsBar, +.suggestionChip
│   └── __tests__/
│       └── LibraryTab.test.tsx      # CẬP NHẬT: mock isBroadQuery, +3 test cases
├── i18n/
│   └── translations.ts             # CẬP NHẬT: +2 search.* keys
```

**Files KHÔNG được chỉnh sửa:**
- `backend/src/shared/infra/llm/router.py` — LLMRouter đã hoàn chỉnh
- `frontend/src/api/search.ts` — API client giữ nguyên (response type tự suy luận từ interface)
- `frontend/src/api/client.ts` — Axios client không đổi
- `backend/src/shared/infra/database.py` — `get_db` dependency đã có

---

### § Kiểm tra `get_db` dependency

Trước khi implement router, xác nhận `get_db` tồn tại:
```bash
grep -n "get_db\|async_session\|AsyncSession" backend/src/shared/infra/database.py
```
Nếu không tìm thấy, tìm ở:
```bash
grep -rn "def get_db" backend/src/
```
Dùng đúng path import theo kết quả tìm thấy.

---

### § Learnings từ Stories 2.1 và 2.2 (áp dụng cho 2.3)

1. **`asyncio.create_task` + await tuần tự** — giữ pattern Degraded Union (không dùng `asyncio.gather`).
2. **camelCase qua `alias_generator=to_camel`** — `is_broad_query` → `isBroadQuery` trên response, TypeScript interface phải khớp.
3. **LLMRouter đã hoạt động** — được dùng thành công ở Story 2.1 để giải mã API key. Không tái tạo.
4. **langchain_google_genai** — `llm.ainvoke(prompt)` (async), result `.content` là string.
5. **searchIdRef race condition guard** — giữ nguyên pattern từ Story 2.2, áp dụng cho `handleSuggestionClick` cũng cần guard.
6. **CSS `var(--rounded-sm)` = 4px** — dùng cho chip, không hardcode pixel.
7. **TranslationKey type** — thêm key vào `translations.ts` trước khi dùng trong `t()`.
8. **`int(data.get("year"))` S2 cast** — pattern đã fix ở Story 2.2, giữ khi sửa S2 client.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

Không có vấn đề kỹ thuật đặc biệt trong quá trình triển khai.

### Completion Notes List

- Đã thêm `ClientSearchResult` dataclass vào entities.py để wrap danh sách paper + total count từ API nguồn
- Đã cập nhật `SearchResponse` với 2 field mới: `is_broad_query: bool` và `suggestions: list[str]`
- ArxivClient và SemanticScholarClient đều trả về `ClientSearchResult` thay vì `list[PaperResult]`; parse `opensearch:totalResults` từ Atom XML và `total` field từ S2 JSON
- `BroadQueryDetector` dùng LLMRouter để gọi Gemini sinh MECE suggestions, graceful fallback `(True, [])` khi lỗi LLM
- `SearchPapersUseCase` dùng `max(arxiv_total, s2_total)` để detect broad query, truyền detector qua constructor
- SearchCache serialize/deserialize thêm `is_broad_query` + `suggestions`
- Frontend: `SearchResponse` type mở rộng với `isBroadQuery` và `suggestions`; component `BroadQuerySuggestions` hiển thị chip dưới search bar; `handleSuggestionClick` truyền suggestion trực tiếp vào API (không qua React state) để tránh race condition
- Đã thêm 2 translation keys: `search.suggestionAriaLabel` và `search.broadQueryHint`
- Backend tests: 13 unit tests mới (7 cho BroadQueryDetector, 6 cho use case)
- Frontend tests: 3 tests mới (chip hiển thị, click trigger search mới, không hiển thị chip rỗng)
- Toàn bộ regression: 70 backend + 62 frontend tests đều pass

### File List

- `backend/src/modules/search/domain/entities.py` — CẬP NHẬT: +ClientSearchResult, +is_broad_query, +suggestions
- `backend/src/modules/search/infrastructure/arxiv_client.py` — CẬP NHẬT: search() → ClientSearchResult, parse opensearch:totalResults
- `backend/src/modules/search/infrastructure/semantic_scholar_client.py` — CẬP NHẬT: search() → ClientSearchResult, parse total field
- `backend/src/modules/search/infrastructure/broad_query_detector.py` — MỚI: BroadQueryDetector với LLMRouter + Gemini
- `backend/src/modules/search/infrastructure/search_cache.py` — CẬP NHẬT: serialize/deserialize is_broad_query + suggestions
- `backend/src/modules/search/application/use_cases.py` — CẬP NHẬT: +detector param, broad query detection logic
- `backend/src/modules/search/presentation/schemas.py` — CẬP NHẬT: +is_broad_query, +suggestions
- `backend/src/modules/search/presentation/router.py` — CẬP NHẬT: +db dependency, +detector injection
- `backend/src/shared/infra/settings.py` — CẬP NHẬT: +broad_query_threshold: int = 50
- `frontend/src/types/search.ts` — CẬP NHẬT: +isBroadQuery, +suggestions
- `frontend/src/features/workspace/LibraryTab.tsx` — CẬP NHẬT: +BroadQuerySuggestions, +handleSuggestionClick
- `frontend/src/features/workspace/LibraryTab.module.css` — CẬP NHẬT: +.suggestionsBar, +.suggestionChip
- `frontend/src/i18n/translations.ts` — CẬP NHẬT: +search.suggestionAriaLabel, +search.broadQueryHint
- `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx` — CẬP NHẬT: +3 test cases, update MOCK_RESULT
- `tests/unit/search/__init__.py` — MỚI
- `tests/unit/search/test_search_use_case.py` — MỚI: 6 unit tests cho SearchPapersUseCase
- `tests/unit/search/test_broad_query_detector.py` — MỚI: 7 unit tests cho BroadQueryDetector

### Change Log

- 2026-06-17: Triển khai story 2.3 — Gợi ý phân ngành MECE cho chủ đề quá rộng. Thêm BroadQueryDetector tích hợp LLM Gemini, mở rộng toàn bộ search pipeline BE+FE.

---

## Review Findings

_Code review đối kháng (Blind Hunter + Edge Case Hunter + Acceptance Auditor) — 2026-06-17. Tất cả 6 AC được xác nhận PASS; các mục dưới là robustness/độ tin cậy._

### Decision Needed (đã giải quyết)

- [x] [Review][Decision→Patch] Chính sách cache khi Gemini lỗi → **Quyết định: chỉ cache khi có suggestions thật** (nếu `is_broad` và `suggestions` rỗng thì bỏ qua cache để lần sau retry LLM). [use_cases.py:62-73]

### Patch (đã sửa ✅)

- [x] [Review][Patch] Cache: chỉ `cache.set` khi `not is_broad or suggestions` (tránh cache poisoning khi Gemini fail trả suggestions rỗng) [use_cases.py:72-76] — đã sửa + test `test_broad_query_with_suggestions_is_cached`, `test_broad_query_gemini_fails_graceful_fallback`
- [x] [Review][Patch] S2 `int(data.get("total", 0))` bọc try/except `(ValueError, TypeError)` → không còn rớt nguồn S2 khi `total` null/non-numeric [semantic_scholar_client.py:32-35]
- [x] [Review][Patch] Parse phản hồi LLM: thêm `_strip_code_fence` (gỡ ```json) + unwrap object + `_coerce_to_text` (content dạng list block) [broad_query_detector.py:47-58] — test code-fence/unwrap/content-list
- [x] [Review][Patch] `_clean_suggestions`: lọc phần tử non-string, bỏ chuỗi rỗng, dedup giữ thứ tự, cắt ≤200 ký tự, tối đa 5 → diệt chip rác, hết React key collision, tránh 422 [broad_query_detector.py:60] — test filter/dedup

### Deferred (đã ghi nhận, độ ưu tiên thấp)

- [x] [Review][Defer] `detect()` vẫn được gọi khi cả 2 nguồn lỗi / threshold âm có thể bắn LLM mỗi query [broad_query_detector.py:39, use_cases.py:63] — deferred, low impact (threshold mặc định 50 đã chặn)
- [x] [Review][Defer] Heuristic `total == 0 → len(papers)` che giấu "missing field" vs "zero thật"; total âm không guard → broad query thiếu field totalResults không bao giờ được flag [arxiv_client.py:105, semantic_scholar_client.py:35] — deferred, phụ thuộc upstream API, ít xảy ra
- [x] [Review][Defer] Key dịch `search.broadQueryHint` đã thêm nhưng không render ở đâu (orphaned) [frontend/src/i18n/translations.ts:67] — deferred, cleanup UX (AC#2 chỉ yêu cầu chip, không yêu cầu hint text)
