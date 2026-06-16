---
baseline_commit: be5b938
---

# Story 2.2: [BE+FE] Tìm kiếm Bài báo Học thuật Song song với Xử lý lỗi Degraded Union

Status: done

## Story

Với vai trò là người dùng đã đăng nhập,
Tôi muốn tìm kiếm bài báo học thuật từ arXiv và Semantic Scholar cùng lúc,
Để nhanh chóng tìm được tài liệu liên quan đến dự án nghiên cứu của mình, kể cả khi một nguồn bị lỗi/timeout.

## Acceptance Criteria

1. **Given** đang ở tab "Thư viện Tài liệu" trong Dashboard và đã chọn một dự án
   **When** nhập từ khóa vào ô tìm kiếm và bấm Enter hoặc nút Tìm
   **Then** giao diện hiển thị spinner/loading và gọi `GET /api/search?q={keyword}`
   **And** kết quả hiển thị dưới dạng danh sách thẻ bài báo (paper cards) với tiêu đề, tác giả, năm, abstract snippet

2. **Given** từ khóa tìm kiếm hợp lệ
   **When** Backend nhận request `GET /api/search?q={keyword}&limit=10`
   **Then** gọi đồng thời (asyncio.gather) arXiv API và Semantic Scholar API với timeout 8.0 giây
   **And** kết quả được gộp lại và loại bỏ trùng lặp qua DOI hoặc arXiv ID
   **And** trả về JSON: `{"results": [...], "warnings": []}`

3. **Given** API Semantic Scholar bị timeout hoặc lỗi HTTP trong khi arXiv thành công
   **When** Backend nhận được lỗi từ một trong hai nguồn
   **Then** vẫn trả về kết quả từ nguồn thành công (Degraded Union)
   **And** kèm theo `"warnings": ["semantic_scholar_timeout"]` (hoặc `"arxiv_timeout"`)
   **And** Frontend hiển thị Toast màu vàng: "Một số nguồn tìm kiếm không khả dụng — kết quả có thể chưa đầy đủ"

4. **Given** cả hai nguồn đều thất bại (timeout/lỗi mạng)
   **When** Backend không nhận được kết quả nào
   **Then** trả về `{"results": [], "warnings": ["arxiv_timeout", "semantic_scholar_timeout"]}`
   **And** Frontend hiển thị Toast đỏ: "Không thể kết nối đến các nguồn tìm kiếm. Vui lòng thử lại."

5. **Given** đã tìm kiếm cùng từ khóa trước đó trong vòng 24 giờ
   **When** gọi lại API với từ khóa đó
   **Then** Backend trả về kết quả từ Redis cache (không gọi lại external APIs)

6. **Given** kết quả tìm kiếm hiển thị trên UI
   **When** nhìn vào một thẻ bài báo
   **Then** thấy: tiêu đề (link mở URL bài báo), tác giả, năm xuất bản, abstract 3 dòng đầu, badge nguồn (arXiv/Semantic Scholar), badge PDF (nếu có)
   **And** có nút "Thêm vào dự án" ở mỗi thẻ (disabled, tooltip: "Chức năng sẽ có ở Story 2.5")

7. **Given** không có kết quả tìm kiếm (kết quả rỗng)
   **When** kết quả trả về `{"results": []}`
   **Then** hiển thị trạng thái empty với text "Không tìm thấy bài báo nào. Thử từ khóa khác."

8. **Given** đang ở tab "Thư viện Tài liệu"
   **When** chuyển ngôn ngữ VI|EN trên Header
   **Then** tất cả nhãn tĩnh (placeholder, nút, thông báo lỗi) đổi ngôn ngữ ngay lập tức

> 🔍 **Cách nghiệm thu trực quan:**
> Web UI: Chọn dự án → tab "Thư viện Tài liệu" → gõ "transformer attention" → Enter → thấy danh sách paper cards với tiêu đề, tác giả, abstract. Swagger: `GET /api/search?q=transformer&limit=5` → nhận JSON với `results` array và `warnings` rỗng.

---

## Tasks / Subtasks

### BACKEND — Module `search`

- [x] Task 1: Khởi tạo module structure + cập nhật dependencies
  - [x] 1.1 Tạo `backend/src/modules/search/__init__.py` (trống)
  - [x] 1.2 Tạo `backend/src/modules/search/domain/__init__.py` (trống)
  - [x] 1.3 Tạo `backend/src/modules/search/application/__init__.py` (trống)
  - [x] 1.4 Tạo `backend/src/modules/search/infrastructure/__init__.py` (trống)
  - [x] 1.5 Tạo `backend/src/modules/search/presentation/__init__.py` (trống)
  - [x] 1.6 Thêm vào `requirements.txt`: `tenacity>=8.0.0` và `redis[asyncio]>=5.0.0`

- [x] Task 2: Domain — Entity `PaperResult`
  - [x] 2.1 Tạo `backend/src/modules/search/domain/entities.py` với `PaperResult` dataclass và `SearchResponse` dataclass (xem Dev Notes § Domain Entities)

- [x] Task 3: Infrastructure — arXiv HTTP Client
  - [x] 3.1 Tạo `backend/src/modules/search/infrastructure/arxiv_client.py` với class `ArxivClient` (xem Dev Notes § arXiv Client)
  - [x] 3.2 Dùng `httpx.AsyncClient(timeout=8.0)` + `tenacity` retry 2 lần với exponential backoff

- [x] Task 4: Infrastructure — Semantic Scholar HTTP Client
  - [x] 4.1 Tạo `backend/src/modules/search/infrastructure/semantic_scholar_client.py` với class `SemanticScholarClient` (xem Dev Notes § Semantic Scholar Client)
  - [x] 4.2 Dùng `httpx.AsyncClient(timeout=8.0)` + `tenacity` retry 2 lần với exponential backoff

- [x] Task 5: Infrastructure — Redis Cache
  - [x] 5.1 Tạo `backend/src/modules/search/infrastructure/search_cache.py` với class `SearchCache` (xem Dev Notes § Redis Cache)
  - [x] 5.2 Graceful fallback: nếu Redis không kết nối được, log warning và tiếp tục không có cache (KHÔNG raise exception)

- [x] Task 6: Application — SearchPapersUseCase
  - [x] 6.1 Tạo `backend/src/modules/search/application/use_cases.py` với `SearchPapersUseCase` (xem Dev Notes § Use Case)
  - [x] 6.2 asyncio.gather cho cả 2 clients
  - [x] 6.3 Xử lý Degraded Union: nếu một client raise exception → warnings array; nếu cả hai → warnings array rỗng kết quả
  - [x] 6.4 DOI + arXiv ID deduplication
  - [x] 6.5 Cache get/set quanh việc gọi clients

- [x] Task 7: Presentation — Search Router
  - [x] 7.1 Tạo `backend/src/modules/search/presentation/schemas.py` với `SearchResponse` Pydantic schema (xem Dev Notes § Presentation Schemas)
  - [x] 7.2 Tạo `backend/src/modules/search/presentation/router.py` với `GET /search` endpoint (AC: #2) (xem Dev Notes § Router)
  - [x] 7.3 Import ORM models và mount router trong `backend/main.py` (xem Dev Notes § main.py)

### FRONTEND — Library Tab Search UI

- [x] Task 8: Types & API client
  - [x] 8.1 Tạo `frontend/src/types/search.ts` với interfaces `PaperResult`, `SearchResponse` (xem Dev Notes § Frontend Types)
  - [x] 8.2 Tạo `frontend/src/api/search.ts` với function `searchPapers(query, limit?)` (xem Dev Notes § Frontend API Client)

- [x] Task 9: LibraryTab component
  - [x] 9.1 Tạo `frontend/src/features/workspace/LibraryTab.tsx` (xem Dev Notes § LibraryTab Component)
  - [x] 9.2 Tạo `frontend/src/features/workspace/LibraryTab.module.css` theo AcademicPaper design system
  - [x] 9.3 Toast vàng khi `warnings.length > 0`; Toast đỏ khi cả hai nguồn thất bại (kết quả rỗng + warnings ≥ 2)

- [x] Task 10: Tích hợp vào CenterWorkspace
  - [x] 10.1 Cập nhật `frontend/src/features/workspace/CenterWorkspace.tsx`: import và render `<LibraryTab />` trong block `activeTab === 'library'` thay cho placeholder text (xem Dev Notes § CenterWorkspace Update)

- [x] Task 11: i18n Translation Keys
  - [x] 11.1 Thêm các translation keys vào `frontend/src/i18n/translations.ts` (xem Dev Notes § Translation Keys)

- [x] Task 12: Tests
  - [x] 12.1 Tạo `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx` với các test cases (xem Dev Notes § Test Cases)

---

## Dev Notes

### ⚠️ LỖI THƯỜNG GẶP CỦA LLM — PHẢI TRÁNH

1. **KHÔNG dùng Tailwind** — dự án dùng CSS Modules + CSS Variables `AcademicPaper`. Dùng `styles.className` từ `.module.css`. Màu sắc: `var(--surface-base)`, `var(--accent-blue)`, `var(--state-warning)`, `var(--state-danger)`, v.v.

2. **KHÔNG dùng `i18next`** — dùng hook `useTranslation()` từ `frontend/src/i18n/useTranslation.ts`.

3. **KHÔNG quên tham số thứ 2 của `getErrorMessage(err, 'fallback')`** — thiếu sẽ lỗi `TS2554`.

4. **KHÔNG tạo Axios client mới** — dùng `apiClient` từ `frontend/src/api/client.ts` đã có `withCredentials: true` và base URL `/api`.

5. **KHÔNG bỏ `MemoryRouter`** khi render component có `Link`/`useNavigate` trong test.

6. **KHÔNG parse arXiv XML thủ công bằng regex** — dùng Python built-in `xml.etree.ElementTree`.

7. **KHÔNG gọi `asyncio.gather` với coroutine thay vì Task** — wrap mỗi client call bằng `asyncio.create_task` để chúng chạy song song thực sự.

8. **KHÔNG để Redis failure block request** — `SearchCache` phải wrap mọi Redis call trong try/except và log warning; không raise exception.

9. **KHÔNG thêm `"Add to Project"` là clickable** — nút phải `disabled` với tooltip "Chức năng sẽ có ở Story 2.5". Không gọi bất kỳ ingestion API nào.

10. **KHÔNG import `tenacity` decorators trên async function mà không dùng `AsyncRetrying`** — tenacity decorator thông thường không hoạt động với async coroutine; dùng `tenacity.AsyncRetrying` context manager.

---

### § Domain Entities — `entities.py`

```python
# backend/src/modules/search/domain/entities.py
from dataclasses import dataclass, field


@dataclass
class PaperResult:
    title: str
    authors: list[str]
    year: int | None
    abstract: str
    doi: str | None        # dùng cho dedup ưu tiên
    arxiv_id: str | None   # dùng cho dedup thứ cấp
    url: str               # link tới trang bài báo
    pdf_url: str | None    # link PDF trực tiếp (nếu có)
    source: str            # "arxiv" | "semantic_scholar"


@dataclass
class SearchResponse:
    results: list[PaperResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Ghi chú: is_broad_query + suggestions sẽ được thêm vào Story 2.3
```

---

### § arXiv Client — `arxiv_client.py`

arXiv Atom XML API: `http://export.arxiv.org/api/query`

```python
# backend/src/modules/search/infrastructure/arxiv_client.py
import logging
import xml.etree.ElementTree as ET
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

import httpx

from backend.src.modules.search.domain.entities import PaperResult

logger = logging.getLogger(__name__)

ARXIV_API = "http://export.arxiv.org/api/query"
ATOM_NS = "http://www.w3.org/2005/Atom"
ARXIV_NS = "http://arxiv.org/schemas/atom"


class ArxivClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=8.0)

    async def search(self, query: str, limit: int = 10) -> list[PaperResult]:
        params = {
            "search_query": f"all:{query}",
            "max_results": limit,
            "sortBy": "relevance",
        }
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(ARXIV_API, params=params)
                response.raise_for_status()

        return self._parse_atom(response.text)

    def _parse_atom(self, xml_text: str) -> list[PaperResult]:
        results = []
        root = ET.fromstring(xml_text)
        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title_el = entry.find(f"{{{ATOM_NS}}}title")
            abstract_el = entry.find(f"{{{ATOM_NS}}}summary")
            published_el = entry.find(f"{{{ATOM_NS}}}published")
            id_el = entry.find(f"{{{ATOM_NS}}}id")

            title = title_el.text.strip() if title_el is not None else ""
            abstract = abstract_el.text.strip() if abstract_el is not None else ""
            year_str = published_el.text[:4] if published_el is not None else None
            year = int(year_str) if year_str and year_str.isdigit() else None

            # arXiv ID: e.g. "http://arxiv.org/abs/2301.12345v2"
            arxiv_url = id_el.text.strip() if id_el is not None else ""
            arxiv_id = arxiv_url.split("/abs/")[-1].split("v")[0] if "/abs/" in arxiv_url else None

            authors = [
                author.find(f"{{{ATOM_NS}}}name").text.strip()
                for author in entry.findall(f"{{{ATOM_NS}}}author")
                if author.find(f"{{{ATOM_NS}}}name") is not None
            ]

            # DOI tag (nếu có)
            doi_el = entry.find(f"{{{ARXIV_NS}}}doi")
            doi = doi_el.text.strip() if doi_el is not None else None

            # PDF link
            pdf_url = None
            for link in entry.findall(f"{{{ATOM_NS}}}link"):
                if link.get("title") == "pdf":
                    pdf_url = link.get("href")
                    break

            results.append(PaperResult(
                title=title,
                authors=authors,
                year=year,
                abstract=abstract,
                doi=doi,
                arxiv_id=arxiv_id,
                url=arxiv_url,
                pdf_url=pdf_url,
                source="arxiv",
            ))
        return results

    async def aclose(self) -> None:
        await self._client.aclose()
```

---

### § Semantic Scholar Client — `semantic_scholar_client.py`

Semantic Scholar API: `https://api.semanticscholar.org/graph/v1/paper/search`
- Không cần API key cho public access (rate limit 100 req/5 min)
- Trả về JSON

```python
# backend/src/modules/search/infrastructure/semantic_scholar_client.py
import logging
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

import httpx

from backend.src.modules.search.domain.entities import PaperResult

logger = logging.getLogger(__name__)

S2_API = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,year,abstract,externalIds,openAccessPdf"


class SemanticScholarClient:
    def __init__(self) -> None:
        self._client = httpx.AsyncClient(timeout=8.0)

    async def search(self, query: str, limit: int = 10) -> list[PaperResult]:
        params = {"query": query, "fields": S2_FIELDS, "limit": limit}
        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=1, min=1, max=4),
            reraise=True,
        ):
            with attempt:
                response = await self._client.get(S2_API, params=params)
                response.raise_for_status()

        data = response.json()
        return self._parse_response(data.get("data", []))

    def _parse_response(self, papers: list[dict]) -> list[PaperResult]:
        results = []
        for p in papers:
            external_ids = p.get("externalIds") or {}
            doi = external_ids.get("DOI")
            arxiv_id = external_ids.get("ArXiv")

            open_access = p.get("openAccessPdf") or {}
            pdf_url = open_access.get("url")

            authors = [a.get("name", "") for a in (p.get("authors") or [])]
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else (
                f"https://doi.org/{doi}" if doi else ""
            )

            results.append(PaperResult(
                title=p.get("title") or "",
                authors=authors,
                year=p.get("year"),
                abstract=p.get("abstract") or "",
                doi=doi,
                arxiv_id=arxiv_id,
                url=arxiv_url,
                pdf_url=pdf_url,
                source="semantic_scholar",
            ))
        return results

    async def aclose(self) -> None:
        await self._client.aclose()
```

---

### § Redis Cache — `search_cache.py`

```python
# backend/src/modules/search/infrastructure/search_cache.py
import hashlib
import json
import logging
from dataclasses import asdict

import redis.asyncio as aioredis

from backend.src.modules.search.domain.entities import PaperResult, SearchResponse
from backend.src.shared.infra.settings import get_settings

logger = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 86400  # 24 giờ


class SearchCache:
    def __init__(self) -> None:
        try:
            settings = get_settings()
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        except Exception:
            logger.warning("Không thể khởi tạo Redis client, cache bị tắt.")
            self._redis = None

    def _make_key(self, query: str, limit: int) -> str:
        normalized = query.strip().lower()
        return "search:" + hashlib.md5(f"{normalized}:{limit}".encode()).hexdigest()

    async def get(self, query: str, limit: int) -> SearchResponse | None:
        if self._redis is None:
            return None
        try:
            key = self._make_key(query, limit)
            raw = await self._redis.get(key)
            if raw is None:
                return None
            data = json.loads(raw)
            return SearchResponse(
                results=[PaperResult(**r) for r in data["results"]],
                warnings=data["warnings"],
            )
        except Exception as e:
            logger.warning("Redis cache get thất bại: %s", e)
            return None

    async def set(self, query: str, limit: int, response: SearchResponse) -> None:
        if self._redis is None:
            return
        try:
            key = self._make_key(query, limit)
            data = {
                "results": [asdict(r) for r in response.results],
                "warnings": response.warnings,
            }
            await self._redis.setex(key, CACHE_TTL_SECONDS, json.dumps(data))
        except Exception as e:
            logger.warning("Redis cache set thất bại: %s", e)
```

---

### § Use Case — `SearchPapersUseCase`

```python
# backend/src/modules/search/application/use_cases.py
import asyncio
import logging

import httpx

from backend.src.modules.search.domain.entities import PaperResult, SearchResponse
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient

logger = logging.getLogger(__name__)


class SearchPapersUseCase:
    def __init__(
        self,
        arxiv: ArxivClient,
        s2: SemanticScholarClient,
        cache: SearchCache,
    ) -> None:
        self._arxiv = arxiv
        self._s2 = s2
        self._cache = cache

    async def execute(self, query: str, limit: int = 10) -> SearchResponse:
        # 1. Kiểm tra cache
        cached = await self._cache.get(query, limit)
        if cached is not None:
            return cached

        # 2. Gọi song song cả 2 nguồn
        arxiv_task = asyncio.create_task(self._arxiv.search(query, limit))
        s2_task = asyncio.create_task(self._s2.search(query, limit))

        arxiv_results: list[PaperResult] = []
        s2_results: list[PaperResult] = []
        warnings: list[str] = []

        # 3. Degraded Union: xử lý lỗi từng nguồn độc lập
        for coro, name, bucket in [
            (arxiv_task, "arxiv_timeout", arxiv_results),
            (s2_task, "semantic_scholar_timeout", s2_results),
        ]:
            try:
                results = await coro
                bucket.extend(results)
            except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, Exception) as e:
                logger.warning("Tìm kiếm %s thất bại: %s", name, e)
                warnings.append(name)

        # 4. Gộp và khử trùng lặp
        combined = self._deduplicate(arxiv_results + s2_results)

        response = SearchResponse(results=combined[:limit], warnings=warnings)

        # 5. Lưu cache (chỉ khi có ít nhất 1 nguồn thành công)
        if len(warnings) < 2:
            await self._cache.set(query, limit, response)

        return response

    def _deduplicate(self, papers: list[PaperResult]) -> list[PaperResult]:
        seen_dois: set[str] = set()
        seen_arxiv_ids: set[str] = set()
        unique: list[PaperResult] = []

        for p in papers:
            # Ưu tiên DOI
            if p.doi:
                normalized_doi = p.doi.strip().lower()
                if normalized_doi in seen_dois:
                    continue
                seen_dois.add(normalized_doi)

            # Thứ cấp: arXiv ID (không tính version: "2301.12345v2" → "2301.12345")
            if p.arxiv_id:
                base_id = p.arxiv_id.split("v")[0].strip()
                if base_id in seen_arxiv_ids:
                    continue
                seen_arxiv_ids.add(base_id)

            unique.append(p)

        return unique
```

**Lưu ý quan trọng về Degraded Union:** Dùng vòng lặp `for` thay vì `asyncio.gather(return_exceptions=True)` để code rõ ràng hơn. Mỗi Task đã được `create_task` nên chúng chạy song song; `await` chỉ là chờ kết quả.

---

### § Presentation Schemas — `schemas.py`

```python
# backend/src/modules/search/presentation/schemas.py
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PaperResultSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: str
    authors: list[str]
    year: int | None
    abstract: str
    doi: str | None
    arxiv_id: str | None
    url: str
    pdf_url: str | None
    source: str  # "arxiv" | "semantic_scholar"


class SearchResponseSchema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    results: list[PaperResultSchema]
    warnings: list[str]
```

---

### § Router — `router.py`

```python
# backend/src/modules/search/presentation/router.py
from fastapi import APIRouter, Depends, Query

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.search.application.use_cases import SearchPapersUseCase
from backend.src.modules.search.infrastructure.arxiv_client import ArxivClient
from backend.src.modules.search.infrastructure.search_cache import SearchCache
from backend.src.modules.search.infrastructure.semantic_scholar_client import SemanticScholarClient
from backend.src.modules.search.presentation.schemas import PaperResultSchema, SearchResponseSchema

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponseSchema)
async def search_papers(
    q: str = Query(..., min_length=1, max_length=200, description="Từ khóa tìm kiếm"),
    limit: int = Query(default=10, ge=1, le=50),
    _current_user: User = Depends(get_current_user),  # Yêu cầu đăng nhập
) -> SearchResponseSchema:
    use_case = SearchPapersUseCase(
        arxiv=ArxivClient(),
        s2=SemanticScholarClient(),
        cache=SearchCache(),
    )
    response = await use_case.execute(q.strip(), limit)
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
    )
```

---

### § main.py — Đăng ký router

Thêm vào `backend/main.py`:

```python
from backend.src.modules.search.presentation.router import router as search_router
# ...
app.include_router(search_router, prefix="/api")
```

Module `search` không có ORM models nên KHÔNG cần import thêm gì vào `Base.metadata`.

---

### § Frontend Types — `search.ts`

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
}
```

**Lưu ý:** Backend trả về camelCase (qua `alias_generator=to_camel`): `arxivId`, `pdfUrl`. TypeScript interface phải khớp.

---

### § Frontend API Client — `search.ts`

```typescript
// frontend/src/api/search.ts
import { apiClient } from './client';
import type { SearchResponse } from '@/types/search';

export async function searchPapers(query: string, limit = 10): Promise<SearchResponse> {
  const res = await apiClient.get<SearchResponse>('/search', {
    params: { q: query, limit },
  });
  return res.data;
}
```

---

### § LibraryTab Component

```tsx
// frontend/src/features/workspace/LibraryTab.tsx
import { useState } from 'react';
import { toast } from 'sonner';
import { searchPapers } from '@/api/search';
import { getErrorMessage } from '@/api/errors';
import { useTranslation } from '@/i18n/useTranslation';
import type { PaperResult, SearchResponse } from '@/types/search';
import styles from './LibraryTab.module.css';

export function LibraryTab() {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);

  async function handleSearch() {
    const trimmed = query.trim();
    if (!trimmed) return;

    setIsSearching(true);
    setSearchResult(null);

    try {
      const result = await searchPapers(trimmed);
      setSearchResult(result);

      // Hiển thị toast cảnh báo nếu có warnings
      if (result.warnings.length >= 2) {
        // Cả hai nguồn đều thất bại
        toast.error(t('search.bothSourcesFailed'));
      } else if (result.warnings.length === 1) {
        // Degraded mode
        toast.warning(t('search.partialResults'));
      }
    } catch (err) {
      toast.error(getErrorMessage(err, t('search.searchError')));
    } finally {
      setIsSearching(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      handleSearch();
    }
  }

  return (
    <div className={styles.container}>
      {/* Search Bar */}
      <div className={styles.searchBar}>
        <input
          type="text"
          className={styles.searchInput}
          placeholder={t('search.placeholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          aria-label={t('search.placeholder')}
        />
        <button
          className={styles.searchButton}
          onClick={handleSearch}
          disabled={isSearching || !query.trim()}
          type="button"
        >
          {isSearching ? t('search.searching') : t('search.searchButton')}
        </button>
      </div>

      {/* Kết quả */}
      {isSearching && (
        <div className={styles.loading}>{t('search.loading')}</div>
      )}

      {searchResult && !isSearching && (
        <>
          {searchResult.results.length === 0 ? (
            <div className={styles.empty}>{t('search.noResults')}</div>
          ) : (
            <div className={styles.resultList}>
              {searchResult.results.map((paper, index) => (
                <PaperCard key={paper.doi ?? paper.arxivId ?? index} paper={paper} t={t} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface PaperCardProps {
  paper: PaperResult;
  t: (key: string) => string;
}

function PaperCard({ paper, t }: PaperCardProps) {
  const authorStr = paper.authors.slice(0, 3).join(', ') + (paper.authors.length > 3 ? ' et al.' : '');
  const abstractSnippet = paper.abstract.length > 200
    ? paper.abstract.slice(0, 200) + '...'
    : paper.abstract;

  return (
    <div className={styles.card}>
      <div className={styles.cardHeader}>
        <a
          href={paper.url}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.paperTitle}
        >
          {paper.title}
        </a>
        <div className={styles.badges}>
          <span className={styles.sourceBadge} data-source={paper.source}>
            {paper.source === 'arxiv' ? 'arXiv' : 'Semantic Scholar'}
          </span>
          {paper.pdfUrl && (
            <a
              href={paper.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.pdfBadge}
              aria-label="PDF"
            >
              PDF
            </a>
          )}
        </div>
      </div>
      <div className={styles.cardMeta}>
        <span className={styles.authors}>{authorStr}</span>
        {paper.year && <span className={styles.year}>{paper.year}</span>}
      </div>
      <p className={styles.abstract}>{abstractSnippet}</p>
      <div className={styles.cardActions}>
        <button
          className={styles.addButton}
          disabled
          title={t('search.addComingSoon')}
          type="button"
        >
          {t('search.addToProject')}
        </button>
      </div>
    </div>
  );
}
```

---

### § LibraryTab.module.css — Cấu trúc CSS cần implement

Dùng CSS Variables của AcademicPaper. Các class cần có:
- `.container` — full width, padding top
- `.searchBar` — flex row, gap 8px
- `.searchInput` — flex 1, `border: 1px solid var(--border-hairline)`, `border-radius: var(--rounded-md)`, padding 8px 12px
- `.searchButton` — background `var(--accent-blue)`, color white, disabled: opacity 0.5
- `.loading`, `.empty` — centered text, color `var(--ink-secondary)`
- `.resultList` — flex column, gap 12px, padding top 16px
- `.card` — `background: var(--surface-raised)`, border, border-radius, padding 16px
- `.cardHeader` — flex row space-between, align-items flex-start
- `.paperTitle` — color `var(--accent-blue)`, font-weight 600, hover underline
- `.badges` — flex row, gap 6px
- `.sourceBadge[data-source="arxiv"]` — background xanh nhạt
- `.sourceBadge[data-source="semantic_scholar"]` — background tím nhạt
- `.pdfBadge` — background `var(--state-success)`, color white
- `.cardMeta` — flex row, gap 12px, font-size 11px, color `var(--ink-secondary)`
- `.abstract` — font-size 13px, color `var(--ink-secondary)`, margin top 8px
- `.cardActions` — margin top 12px
- `.addButton:disabled` — opacity 0.4, cursor not-allowed

---

### § CenterWorkspace Update

Thay thế placeholder text trong `CenterWorkspace.tsx`:

```tsx
// HIỆN TẠI:
<div style={{ display: activeTab === 'library' ? 'block' : 'none' }}>
  <p className={styles.placeholder}>{t('tab.library')}</p>
</div>

// SAU KHI CẬP NHẬT:
import { LibraryTab } from './LibraryTab';
// ...
<div style={{ display: activeTab === 'library' ? 'block' : 'none' }}>
  <LibraryTab />
</div>
```

**Lưu ý:** Chỉ thay đổi block `library`. Không chạm vào `graph` và `writing` blocks.

---

### § Translation Keys

Thêm vào `frontend/src/i18n/translations.ts`:

```typescript
// Search
'search.placeholder': { vi: 'Tìm kiếm bài báo học thuật...', en: 'Search academic papers...' },
'search.searchButton': { vi: 'Tìm kiếm', en: 'Search' },
'search.searching': { vi: 'Đang tìm...', en: 'Searching...' },
'search.loading': { vi: 'Đang tải kết quả...', en: 'Loading results...' },
'search.noResults': { vi: 'Không tìm thấy bài báo nào. Thử từ khóa khác.', en: 'No papers found. Try a different keyword.' },
'search.searchError': { vi: 'Lỗi khi tìm kiếm. Vui lòng thử lại.', en: 'Search error. Please try again.' },
'search.partialResults': { vi: 'Một số nguồn tìm kiếm không khả dụng — kết quả có thể chưa đầy đủ', en: 'Some search sources unavailable — results may be incomplete' },
'search.bothSourcesFailed': { vi: 'Không thể kết nối đến các nguồn tìm kiếm. Vui lòng thử lại.', en: 'Cannot connect to search sources. Please try again.' },
'search.addToProject': { vi: '+ Thêm vào dự án', en: '+ Add to Project' },
'search.addComingSoon': { vi: 'Chức năng sẽ có ở Story 2.5', en: 'Feature coming in Story 2.5' },
```

---

### § Test Cases — `LibraryTab.test.tsx`

```tsx
// frontend/src/features/workspace/__tests__/LibraryTab.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { LibraryTab } from '../LibraryTab';
import * as searchApi from '@/api/search';

vi.mock('@/api/search');

const MOCK_RESULT = {
  results: [
    {
      title: 'Attention Is All You Need',
      authors: ['Vaswani, A.', 'Shazeer, N.'],
      year: 2017,
      abstract: 'The dominant sequence transduction models...',
      doi: '10.48550/arXiv.1706.03762',
      arxivId: '1706.03762',
      url: 'https://arxiv.org/abs/1706.03762',
      pdfUrl: 'https://arxiv.org/pdf/1706.03762',
      source: 'arxiv' as const,
    },
  ],
  warnings: [],
};

function renderTab() {
  return render(
    <MemoryRouter>
      <Toaster />
      <LibraryTab />
    </MemoryRouter>
  );
}

describe('LibraryTab', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('hiển thị ô tìm kiếm và nút Tìm kiếm', () => {
    renderTab();
    expect(screen.getByPlaceholderText(/tìm kiếm bài báo/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tìm kiếm/i })).toBeInTheDocument();
  });

  it('nút Tìm kiếm disabled khi input rỗng', () => {
    renderTab();
    const btn = screen.getByRole('button', { name: /tìm kiếm/i });
    expect(btn).toBeDisabled();
  });

  it('hiển thị kết quả sau khi tìm kiếm thành công', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() =>
      expect(screen.getByText('Attention Is All You Need')).toBeInTheDocument()
    );
    expect(screen.getByText(/Vaswani/)).toBeInTheDocument();
    expect(screen.getByText('2017')).toBeInTheDocument();
  });

  it('Enter key kích hoạt tìm kiếm', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() =>
      expect(vi.mocked(searchApi.searchPapers)).toHaveBeenCalledWith('transformer', 10)
    );
  });

  it('hiển thị empty state khi không có kết quả', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue({ results: [], warnings: [] });
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'xyznotfound' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() =>
      expect(screen.getByText(/không tìm thấy bài báo/i)).toBeInTheDocument()
    );
  });

  it('nút "Thêm vào dự án" disabled trên mỗi card', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() => screen.getByText('Attention Is All You Need'));
    const addBtn = screen.getByRole('button', { name: /thêm vào dự án/i });
    expect(addBtn).toBeDisabled();
  });

  it('hiển thị PDF badge khi có pdfUrl', async () => {
    vi.mocked(searchApi.searchPapers).mockResolvedValue(MOCK_RESULT);
    renderTab();

    const input = screen.getByPlaceholderText(/tìm kiếm bài báo/i);
    fireEvent.change(input, { target: { value: 'transformer' } });
    fireEvent.click(screen.getByRole('button', { name: /tìm kiếm/i }));

    await waitFor(() => expect(screen.getByText('PDF')).toBeInTheDocument());
  });
});
```

---

### § Cấu trúc File — Tổng quan

```
backend/
├── src/modules/search/                           # MỚI — module hoàn toàn mới
│   ├── __init__.py
│   ├── domain/
│   │   ├── __init__.py
│   │   └── entities.py                          # PaperResult, SearchResponse
│   ├── application/
│   │   ├── __init__.py
│   │   └── use_cases.py                         # SearchPapersUseCase
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   ├── arxiv_client.py                      # httpx + tenacity, parse Atom XML
│   │   ├── semantic_scholar_client.py           # httpx + tenacity, parse JSON
│   │   └── search_cache.py                      # Redis 24h cache
│   └── presentation/
│       ├── __init__.py
│       ├── schemas.py                           # Pydantic response schemas
│       └── router.py                           # GET /api/search
├── main.py                                      # CẬP NHẬT: +search_router
└── requirements.txt                             # CẬP NHẬT: +tenacity, +redis[asyncio]

frontend/src/
├── types/
│   └── search.ts                               # MỚI: PaperResult, SearchResponse
├── api/
│   └── search.ts                               # MỚI: searchPapers()
├── i18n/
│   └── translations.ts                         # CẬP NHẬT: +10 search keys
└── features/workspace/
    ├── CenterWorkspace.tsx                     # CẬP NHẬT: import + render LibraryTab
    ├── LibraryTab.tsx                          # MỚI: search UI + paper cards
    ├── LibraryTab.module.css                   # MỚI: AcademicPaper styles
    └── __tests__/
        └── LibraryTab.test.tsx                 # MỚI: 6 test cases
```

**Files KHÔNG được chỉnh sửa:**
- `frontend/src/api/client.ts` — Axios client đã đúng
- `frontend/src/i18n/useTranslation.ts` — hook i18n đã đúng
- `backend/src/shared/infra/settings.py` — `redis_url` đã có sẵn
- `backend/src/modules/identity/` — không liên quan
- `backend/src/modules/workspace/` — không liên quan
- `frontend/src/features/workspace/ChatbotPanel.tsx` — không liên quan
- `frontend/src/features/workspace/ProjectSidebar.tsx` — không liên quan

---

### § Dependencies cần thêm vào `requirements.txt`

```
tenacity>=8.0.0
redis[asyncio]>=5.0.0
```

**Lưu ý:**
- `httpx` đã có: `httpx>=0.28.0` — dùng cho cả arXiv và Semantic Scholar clients
- `redis[asyncio]>=5.0.0` — async Redis client (package `redis` với extra `asyncio`). Import: `import redis.asyncio as aioredis`
- `tenacity>=8.0.0` — retry logic. Dùng `AsyncRetrying` context manager cho async code (KHÔNG dùng decorator `@retry` với async function)

---

### § API Contract — GET /api/search

**Endpoint:** `GET /api/search`
**Auth:** JWT cookie (yêu cầu đăng nhập)
**Query params:**
- `q` (required, string, 1-200 ký tự): từ khóa tìm kiếm
- `limit` (optional, int, 1-50, default 10): số kết quả tối đa

**Response 200:**
```json
{
  "results": [
    {
      "title": "Attention Is All You Need",
      "authors": ["Vaswani, A.", "Shazeer, N."],
      "year": 2017,
      "abstract": "The dominant sequence transduction models...",
      "doi": "10.48550/arXiv.1706.03762",
      "arxivId": "1706.03762",
      "url": "https://arxiv.org/abs/1706.03762",
      "pdfUrl": "https://arxiv.org/pdf/1706.03762",
      "source": "arxiv"
    }
  ],
  "warnings": []
}
```

**Response 200 (degraded mode — một nguồn lỗi):**
```json
{
  "results": [...],
  "warnings": ["semantic_scholar_timeout"]
}
```

**Response 200 (cả hai nguồn lỗi):**
```json
{
  "results": [],
  "warnings": ["arxiv_timeout", "semantic_scholar_timeout"]
}
```

**Response 422:** Query validation error (q rỗng hoặc vượt 200 ký tự)
**Response 401:** Chưa đăng nhập

**Lưu ý:** API trả về 200 kể cả khi degraded — frontend kiểm tra `warnings` array để hiển thị Toast cảnh báo.

---

### § Learnings từ Stories Trước (Epic 1 + Story 2.1)

1. **`getErrorMessage(err, 'fallback string')`** — BẮT BUỘC tham số thứ 2.

2. **CSS Modules + CSS Variables AcademicPaper** — không inline style màu sắc; dùng `var(--surface-raised)`, `var(--accent-blue)`, `var(--state-warning)`, v.v.

3. **`useTranslation()` stability** — hook trả về `t` stable (đã fix bug ở story 2.1). Không cần `useCallback` wrap nếu chỉ dùng `t` trong handler.

4. **`MemoryRouter` bắt buộc** khi render component có `Link`/`useNavigate` trong test.

5. **`waitFor()` thay vì `act()`** trong RTL tests.

6. **Pydantic camelCase**: `alias_generator=to_camel` trên models Pydantic → Frontend nhận `arxivId`, `pdfUrl` (camelCase). TypeScript interface phải khớp.

7. **Module structure pattern**: mỗi module có `domain/`, `application/`, `infrastructure/`, `presentation/` — theo đúng pattern của `identity` và `workspace` modules.

8. **`asyncio.create_task` thay vì `asyncio.gather`** khi cần xử lý lỗi từng task độc lập (Degraded Union pattern).

9. **Redis graceful fallback** — KHÔNG để Redis failure block request. Wrap trong try/except và tiếp tục.

10. **arXiv API**: namespace Atom XML là `http://www.w3.org/2005/Atom`. arXiv-specific: `http://arxiv.org/schemas/atom`. Dùng `{NAMESPACE}tagname` syntax trong ElementTree.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Completion Notes List

- Tạo module `backend/src/modules/search/` với cấu trúc DDD đầy đủ (domain/application/infrastructure/presentation)
- `ArxivClient`: parse Atom XML từ arXiv API dùng `xml.etree.ElementTree` + tenacity `AsyncRetrying` retry 2 lần
- `SemanticScholarClient`: parse JSON từ S2 Graph API + tenacity `AsyncRetrying` retry 2 lần
- `SearchCache`: Redis cache TTL 24h với graceful fallback (nếu Redis không có → tiếp tục không cache, không raise exception)
- `SearchPapersUseCase`: dùng `asyncio.create_task` để gọi song song 2 clients; Degraded Union — nếu 1 nguồn lỗi vẫn trả về kết quả; deduplication theo DOI rồi arXiv ID
- `GET /api/search` endpoint: yêu cầu JWT cookie auth, camelCase response qua `alias_generator=to_camel`
- Frontend: `LibraryTab` component với CSS Modules + CSS Variables AcademicPaper; toast vàng/đỏ theo trạng thái warnings; nút "Thêm vào dự án" disabled với tooltip Story 2.5
- 59 frontend tests pass (6 tests mới cho LibraryTab), TypeScript clean
- Sửa: component gọi `searchPapers(trimmed, 10)` tường minh để test `toHaveBeenCalledWith('transformer', 10)` pass

### File List

**Backend — MỚI:**
- `backend/src/modules/search/__init__.py`
- `backend/src/modules/search/domain/__init__.py`
- `backend/src/modules/search/domain/entities.py`
- `backend/src/modules/search/application/__init__.py`
- `backend/src/modules/search/application/use_cases.py`
- `backend/src/modules/search/infrastructure/__init__.py`
- `backend/src/modules/search/infrastructure/arxiv_client.py`
- `backend/src/modules/search/infrastructure/semantic_scholar_client.py`
- `backend/src/modules/search/infrastructure/search_cache.py`
- `backend/src/modules/search/presentation/__init__.py`
- `backend/src/modules/search/presentation/schemas.py`
- `backend/src/modules/search/presentation/router.py`

**Backend — CẬP NHẬT:**
- `backend/main.py` (thêm search_router)
- `requirements.txt` (thêm tenacity>=8.0.0, redis[asyncio]>=5.0.0)

**Frontend — MỚI:**
- `frontend/src/types/search.ts`
- `frontend/src/api/search.ts`
- `frontend/src/features/workspace/LibraryTab.tsx`
- `frontend/src/features/workspace/LibraryTab.module.css`
- `frontend/src/features/workspace/__tests__/LibraryTab.test.tsx`

**Frontend — CẬP NHẬT:**
- `frontend/src/features/workspace/CenterWorkspace.tsx` (import + render LibraryTab)
- `frontend/src/i18n/translations.ts` (thêm 10 search.* keys)

### Review Findings

_Code review 2026-06-17 (bmad-code-review, 3 lớp: Blind Hunter + Edge Case Hunter + Acceptance Auditor). Tất cả 8 AC và checklist "must avoid" đều PASS. Các phát hiện dưới đây là về robustness/correctness, không phải vi phạm AC._

**[Patch] — fix rõ ràng, không cần quyết:**

- [x] [Review][Patch] (decision đã chốt: **xen kẽ 2 nguồn**) `combined[:limit]` cắt mất toàn bộ nguồn thứ hai — interleave arXiv/S2 trước khi `[:limit]` để cả 2 nguồn đại diện công bằng [use_cases.py:48-49] ✅ fixed
- [x] [Review][Patch] (decision đã chốt: **chỉ cache khi đủ 2 nguồn**) Đổi `if len(warnings) < 2` thành `if not warnings` — không đóng băng kết quả degraded 24h [use_cases.py:51-52] ✅ fixed

- [x] [Review][Patch] Rò rỉ httpx client + Redis mỗi request — `ArxivClient()/SemanticScholarClient()/SearchCache()` tạo mới mỗi request, `aclose()` định nghĩa nhưng KHÔNG BAO GIỜ được gọi → cạn FD/socket dưới tải [router.py:20-24] ✅ fixed (try/finally aclose)
- [x] [Review][Patch] Bug logic dedup — khi DOI trùng thì `continue` sớm khiến `arxiv_id` của bản đó không được đăng ký vào `seen_arxiv_ids`; trạng thái dedup không nhất quán [use_cases.py:61-74] ✅ fixed
- [x] [Review][Patch] Parser arXiv crash khi `title`/`summary`/`<name>` có `.text = None` (thẻ rỗng `<title/>`) → `AttributeError` làm mất TOÀN BỘ kết quả arXiv [arxiv_client.py:47-58] ✅ fixed
- [x] [Review][Patch] Parser arXiv: `published_el.text[:4]` crash nếu `.text=None`; năm 2 ký tự ("20") qua được `isdigit()` → năm rác [arxiv_client.py:49-50] ✅ fixed
- [x] [Review][Patch] Race condition frontend — tìm "A" (chậm) rồi "B" (nhanh); A về sau ghi đè kết quả B. Thiếu guard request-id/abort [LibraryTab.tsx handleSearch] ✅ fixed (searchIdRef)
- [x] [Review][Patch] `except (... , Exception)` thừa `Exception` ở cuối tuple → bug nội bộ (parse lỗi) bị nuốt và báo sai thành `*_timeout`. Nên log `exc_info` và/hoặc tách nhãn lỗi nội bộ [use_cases.py:44] ✅ fixed (exc_info=True)
- [x] [Review][Patch] Strip version arxiv_id bằng `split("v")[0]` thiếu chính xác — nên dùng regex `vN$` [arxiv_client.py:53, use_cases.py:69] ✅ fixed (re.sub)
- [x] [Review][Patch] `q` chỉ gồm khoảng trắng vượt `min_length=1` rồi `.strip()` → query rỗng gửi lên API ngoài [router.py:16,25] ✅ fixed (422 guard)
- [x] [Review][Patch] `year` từ Semantic Scholar dùng nguyên `p.get("year")` không ép kiểu — nếu S2 trả string/float sẽ vi phạm `int | None` [semantic_scholar_client.py] ✅ fixed (int cast)
- [x] [Review][Patch] `HTTPStatusError`/429 không nằm trong `retry_if_exception_type` → 5xx/rate-limit không retry mà thành warning ngay [arxiv_client.py:27, semantic_scholar_client.py] ✅ fixed (_is_retryable)
- [x] [Review][Patch] MD5 cache key thiếu `usedforsecurity=False` (Bandit B324) [search_cache.py] ✅ fixed
- [x] [Review][Patch] arXiv gọi qua HTTP cleartext — nên dùng `https://export.arxiv.org` [arxiv_client.py:11] ✅ fixed
- [x] [Review][Patch] Prop `t: (key: string) => string` làm mất type-safety key i18n — dùng kiểu `TranslationKey` [LibraryTab.tsx] ✅ fixed

**[Defer] — thật nhưng để sau:**

- [x] [Review][Defer] Dedup không bắt trùng chéo nguồn khi định danh rời rạc (arXiv chỉ có arxiv_id, S2 chỉ có DOI cho cùng 1 bài) — cần fuzzy/title matching, là tính năng lớn hơn — deferred
- [x] [Review][Defer] User input đưa thẳng vào `search_query=all:{query}` của arXiv (grammar injection nhẹ) — cần escape grammar arXiv — deferred

## Change Log

- 2026-06-17: Tạo Story 2.2 — BMad Method v6.8.0 (create-story). Story về tìm kiếm bài báo học thuật song song (arXiv + Semantic Scholar) với Degraded Union error handling và Redis caching.
- 2026-06-17: Triển khai Story 2.2 — Tất cả 12 Tasks hoàn thành. 59 frontend tests pass, TypeScript clean. Module `search` BE + LibraryTab FE.
