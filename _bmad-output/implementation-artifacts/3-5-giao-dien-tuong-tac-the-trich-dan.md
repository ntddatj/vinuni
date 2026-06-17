---
baseline_commit: fbf805ea528adaab8887c20395244948b35c4496
---

# Story 3.5: Giao Diện Tương Tác Thẻ Trích Dẫn

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn thấy các số trích dẫn `[1]`, `[2]` trong câu trả lời AI hiển thị như thẻ badge có thể hover để xem nội dung gốc,
Để tôi có thể kiểm chứng nguồn trích dẫn mà không mất mạch đọc.

> **Phạm vi story này** tương đương epic 3.5 + epic 3.10:
> - Epic 3.5: [Frontend] Typewriter UI & SSE Receiver (xác nhận + tăng cường animation)
> - Epic 3.10: [Frontend] Interactive Citation Tooltip UI (thẻ trích dẫn + tooltip hover)

## Acceptance Criteria

1. **AC#1 — "AI is thinking..." icon hiển thị đúng lúc [Manual/Visual]**
   **Given** người dùng gửi tin nhắn trên UI.
   **When** POST gửi tin nhắn thành công và SSE stream bắt đầu.
   **Then** hiển thị spinner/icon "AI đang suy nghĩ..." cho đến khi nhận chunk đầu tiên.
   **And** sau khi có chunk đầu tiên, spinner biến mất và text bắt đầu hiện dần theo hiệu ứng typewriter.

2. **AC#2 — Auto-scroll theo tin nhắn mới [Manual/Visual]**
   **Given** luồng chat có nhiều tin nhắn dài hơn viewport.
   **When** có chunk SSE mới hoặc tin nhắn mới được commit.
   **Then** khung chat tự cuộn xuống cuối mượt mà (smooth scroll).

3. **AC#3 — Câu trả lời đã commit render `[N]` thành badge `.citation-link` [Unit Test]**
   **Given** một tin nhắn `assistant` với content `"Nghiên cứu cho thấy [1] và tổng hợp [2]."`.
   **When** component `MessageContent` render tin nhắn này.
   **Then** DOM chứa 2 phần tử `<span class="citation-link">` với text `[1]` và `[2]` tương ứng.
   **And** phần text thông thường `"Nghiên cứu cho thấy "` và `" và tổng hợp "` và `"."` vẫn hiển thị nguyên vẹn.

4. **AC#4 — Badge `.citation-link` có style xanh cobalt phân biệt [Manual/Visual]**
   **Given** câu trả lời AI chứa `[1]`.
   **When** UI hiển thị tin nhắn.
   **Then** badge `[1]` có màu xanh cobalt (`#2563EB` = `var(--accent-blue)`), bo góc `rounded.sm` (4px), cursor pointer, nổi bật khỏi text thông thường.

5. **AC#5 — Hover badge kích hoạt tooltip với loading state [Manual/Visual]**
   **Given** badge `[1]` đang hiển thị.
   **When** người dùng hover chuột vào.
   **Then** một popover nổi lên ngay bên dưới badge hiển thị trạng thái "Đang tải..." (loading spinner hoặc text).

6. **AC#6 — Tooltip hiển thị dữ liệu từ API khi có dữ liệu [Unit Test + Manual]**
   **Given** API `GET /api/citations/{id}` trả về `{"title": "Paper A", "text": "Apple color is red..."}`.
   **When** tooltip đang hiển thị sau hover.
   **Then** tooltip chứa tiêu đề paper (`title`) ở dạng chữ đậm và đoạn text gốc (`text`) bên dưới.
   **And** popover có nền `surface-raised`, viền `border-hairline`, bo góc `rounded.lg` (8px), đổ bóng nhẹ.

7. **AC#7 — Tooltip xử lý lỗi API gracefully (404 / 422 / network) [Unit Test]**
   **Given** API trả về lỗi 404 hoặc 422 (ví dụ: mock RAG không có UUID thật).
   **When** tooltip render.
   **Then** tooltip hiển thị message `"Không tìm thấy thông tin trích dẫn"` thay vì crash hoặc show lỗi kỹ thuật.

8. **AC#8 — Move-out ẩn tooltip [Manual/Visual]**
   **Given** tooltip đang hiển thị khi hover.
   **When** người dùng di chuột ra ngoài badge VÀ ra ngoài tooltip.
   **Then** tooltip biến mất.

9. **AC#9 — Streaming text KHÔNG parse citation trong khi stream [Unit Test]**
   **Given** AI đang streaming text có chứa `[1]`.
   **When** `streamingContent` đang tích lũy (isStreaming = true).
   **Then** text trong bubble streaming hiển thị dạng plain text (không có badge), giữ nguyên cursor `▋`.
   **And** chỉ sau `commitStreamingMessage`, tin nhắn committed mới được parse thành badge.

> 🔍 **Cách nghiệm thu trực quan:**
> 1. **AC#1-2**: Mở Web, gõ tin nhắn, thấy spinner "đang suy nghĩ", sau đó chữ hiện từng chunk, cuộn tự động xuống dưới.
> 2. **AC#3-4**: Nếu mock RAG trả về text có `[1]` (hoặc nhìn trong committed message), thấy badge xanh cobalt.
> 3. **AC#5-8**: Hover vào badge `[1]`, thấy popover hiện lên với loading → sau đó data hoặc "Không tìm thấy...". Move chuột ra thấy popover ẩn.
> 4. **AC#9**: Trong khi AI đang stream, text không có badge; sau khi done thì badge xuất hiện.

---

## Tasks / Subtasks

### FRONTEND — Citation API Client (AC#6, #7)

- [x] **Task 1**: Tạo `frontend/src/api/citations.ts`
  - [x] 1.1 Tạo file mới:
    ```typescript
    import apiClient from './client';

    export interface CitationDetail {
      title: string;
      text: string;
    }

    export async function getCitationDetail(citationId: string): Promise<CitationDetail> {
      const { data } = await apiClient.get<CitationDetail>(`/api/citations/${citationId}`);
      return data;
    }
    ```
  - **Lưu ý**: `apiClient` là axios instance từ `./client` — đã có auth cookie và base URL. Không tạo axios instance mới.

### FRONTEND — CitationBadge Component (AC#3-#8)

- [x] **Task 2**: Tạo `frontend/src/components/CitationBadge.tsx`
  - [x] 2.1 Tạo component với tooltip-on-hover logic:
    ```tsx
    import { useState, useRef } from 'react';
    import { getCitationDetail, type CitationDetail } from '@/api/citations';
    import styles from './CitationBadge.module.css';

    interface Props {
      citationId: string; // ordinal N từ [N] hoặc UUID khi real RAG
      label: string;      // ví dụ: "[1]"
    }

    type TooltipState =
      | { status: 'hidden' }
      | { status: 'loading' }
      | { status: 'loaded'; data: CitationDetail }
      | { status: 'error' };

    export function CitationBadge({ citationId, label }: Props) {
      const [tooltip, setTooltip] = useState<TooltipState>({ status: 'hidden' });
      const fetchedRef = useRef(false);

      function handleMouseEnter() {
        setTooltip({ status: 'loading' });
        if (fetchedRef.current) return; // đã fetch rồi, giữ kết quả
        fetchedRef.current = true;
        getCitationDetail(citationId)
          .then((data) => setTooltip({ status: 'loaded', data }))
          .catch(() => setTooltip({ status: 'error' }));
      }

      function handleMouseLeave() {
        setTooltip({ status: 'hidden' });
        fetchedRef.current = false; // reset để fetch lại lần hover tiếp
      }

      return (
        <span
          className={styles.wrapper}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
          <span className={styles.badge}>{label}</span>
          {tooltip.status !== 'hidden' && (
            <span className={styles.tooltip}>
              {tooltip.status === 'loading' && (
                <span className={styles.loading}>Đang tải...</span>
              )}
              {tooltip.status === 'loaded' && (
                <>
                  <span className={styles.tooltipTitle}>{tooltip.data.title}</span>
                  <span className={styles.tooltipText}>{tooltip.data.text}</span>
                </>
              )}
              {tooltip.status === 'error' && (
                <span className={styles.error}>Không tìm thấy thông tin trích dẫn</span>
              )}
            </span>
          )}
        </span>
      );
    }
    ```
  - **Quan trọng**: `fetchedRef.current = false` trong `handleMouseLeave` → mỗi lần hover lại sẽ fetch lại. Nếu muốn cache: giữ `fetchedRef.current = true` và lưu kết quả trong ref khác. MVP: không cache, đơn giản hơn.
  - **Pitfall**: Không dùng `useEffect` với dependency `citationId` để fetch — sẽ fetch ngay khi render, không phải khi hover. Phải fetch trong `onMouseEnter`.

- [x] **Task 3**: Tạo `frontend/src/components/CitationBadge.module.css`
  - [x] 3.1 Tạo file CSS:
    ```css
    .wrapper {
      position: relative;
      display: inline-block;
    }

    .badge {
      display: inline-block;
      padding: 0 4px;
      border-radius: 4px; /* rounded.sm */
      background: rgba(37, 99, 235, 0.1); /* accent-blue nhạt */
      color: var(--accent-blue);
      font-size: 0.8em;
      font-weight: 600;
      cursor: pointer;
      vertical-align: super;
      line-height: 1;
      transition: background 0.15s;
    }

    .badge:hover {
      background: rgba(37, 99, 235, 0.2);
    }

    .tooltip {
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      transform: translateX(-50%);
      z-index: 100;
      min-width: 200px;
      max-width: 300px;
      padding: 8px 10px;
      background: var(--surface-raised);
      border: 1px solid var(--border-hairline);
      border-radius: 8px; /* rounded.lg */
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
      display: flex;
      flex-direction: column;
      gap: 4px;
      pointer-events: none;
    }

    .tooltipTitle {
      font-size: 12px;
      font-weight: 600;
      color: var(--ink-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .tooltipText {
      font-size: 11px;
      color: var(--ink-secondary);
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 3;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .loading,
    .error {
      font-size: 11px;
      color: var(--ink-secondary);
      font-style: italic;
    }
    ```
  - **Lưu ý**: Tooltip dùng `pointer-events: none` để không bị hover-out khi chuột di sang tooltip. Nếu muốn tooltip tương tác (copy text), đổi sang `pointer-events: auto` nhưng cần thêm logic phức hơn (setTimeout khi leave).

### FRONTEND — MessageContent Utility (AC#3, #9)

- [x] **Task 4**: Tạo `frontend/src/components/MessageContent.tsx`
  - [x] 4.1 Tạo parser component:
    ```tsx
    import { CitationBadge } from './CitationBadge';

    interface Props {
      content: string;
    }

    const CITATION_RE = /(\[\d+\])/g;

    export function MessageContent({ content }: Props) {
      const parts = content.split(CITATION_RE);
      return (
        <>
          {parts.map((part, i) => {
            const match = part.match(/^\[(\d+)\]$/);
            if (match) {
              return (
                <CitationBadge
                  key={i}
                  citationId={match[1]}
                  label={part}
                />
              );
            }
            return <span key={i}>{part}</span>;
          })}
        </>
      );
    }
    ```
  - **Quan trọng**: `split(CITATION_RE)` với capturing group `()` giữ lại delimiter trong mảng kết quả — pattern chuẩn để split-and-keep. Không cần thư viện thêm.
  - **Lưu ý key**: Dùng index `i` làm key vì `parts` là static per-render (nội dung tin nhắn không thay đổi sau commit). Đây là trường hợp hợp lệ cho index-as-key.

### FRONTEND — Tích hợp vào ChatbotPanel (AC#1, #2, #9)

- [x] **Task 5**: Cập nhật `frontend/src/features/workspace/ChatbotPanel.tsx`
  - [x] 5.1 Thêm import:
    ```tsx
    import { MessageContent } from '@/components/MessageContent';
    ```
  - [x] 5.2 Thay đổi render tin nhắn committed (dòng 290):
    ```tsx
    // Trước:
    {msg.content}

    // Sau:
    {msg.role === 'assistant' ? (
      <MessageContent content={msg.content} />
    ) : (
      msg.content
    )}
    ```
  - **Quan trọng**: Chỉ parse citation trong tin nhắn `assistant`. Tin nhắn `user` không cần parse (người dùng không viết citation tag). Streaming bubble giữ nguyên `{streamingContent}` — KHÔNG dùng `MessageContent` trong lúc stream.
  - **Không thay đổi** bất kỳ logic SSE, state management, suggestion pills, hay resize handle. Chỉ thay đổi render phần content của tin nhắn assistant.

### FRONTEND — Unit Tests (AC#3, #6, #7, #9)

- [x] **Task 6**: Tạo `frontend/src/components/__tests__/CitationBadge.test.tsx`
  - [x] 6.1 Tạo test file:
    ```tsx
    import { render, screen, waitFor } from '@testing-library/react';
    import userEvent from '@testing-library/user-event';
    import { vi } from 'vitest';
    import { CitationBadge } from '../CitationBadge';

    vi.mock('@/api/citations', () => ({
      getCitationDetail: vi.fn(),
    }));

    import { getCitationDetail } from '@/api/citations';

    const mockGet = getCitationDetail as ReturnType<typeof vi.fn>;

    describe('CitationBadge', () => {
      beforeEach(() => {
        mockGet.mockReset();
      });

      it('renders badge with label', () => {
        render(<CitationBadge citationId="1" label="[1]" />);
        expect(screen.getByText('[1]')).toBeInTheDocument();
      });

      it('shows loading on hover', async () => {
        mockGet.mockReturnValue(new Promise(() => {})); // never resolves
        render(<CitationBadge citationId="1" label="[1]" />);
        await userEvent.hover(screen.getByText('[1]'));
        expect(screen.getByText('Đang tải...')).toBeInTheDocument();
      });

      it('shows citation data after successful fetch', async () => {
        mockGet.mockResolvedValue({ title: 'Paper A', text: 'Apple color is red...' });
        render(<CitationBadge citationId="1" label="[1]" />);
        await userEvent.hover(screen.getByText('[1]'));
        await waitFor(() => expect(screen.getByText('Paper A')).toBeInTheDocument());
        expect(screen.getByText('Apple color is red...')).toBeInTheDocument();
      });

      it('shows error message on API failure', async () => {
        mockGet.mockRejectedValue(new Error('404'));
        render(<CitationBadge citationId="999" label="[999]" />);
        await userEvent.hover(screen.getByText('[999]'));
        await waitFor(() =>
          expect(screen.getByText('Không tìm thấy thông tin trích dẫn')).toBeInTheDocument()
        );
      });

      it('hides tooltip on mouse leave', async () => {
        mockGet.mockResolvedValue({ title: 'Paper A', text: 'content' });
        render(<CitationBadge citationId="1" label="[1]" />);
        const badge = screen.getByText('[1]');
        await userEvent.hover(badge);
        await userEvent.unhover(badge);
        expect(screen.queryByText('Đang tải...')).not.toBeInTheDocument();
      });
    });
    ```

- [x] **Task 7**: Tạo `frontend/src/components/__tests__/MessageContent.test.tsx`
  - [x] 7.1 Tạo test file:
    ```tsx
    import { render, screen } from '@testing-library/react';
    import { vi } from 'vitest';
    import { MessageContent } from '../MessageContent';

    vi.mock('../CitationBadge', () => ({
      CitationBadge: ({ label }: { label: string }) => (
        <span data-testid="citation-badge">{label}</span>
      ),
    }));

    describe('MessageContent', () => {
      it('renders plain text without citations', () => {
        render(<MessageContent content="Đây là câu trả lời." />);
        expect(screen.getByText('Đây là câu trả lời.')).toBeInTheDocument();
        expect(screen.queryByTestId('citation-badge')).toBeNull();
      });

      it('renders citation badge for [N] pattern', () => {
        render(<MessageContent content="Nghiên cứu [1] xác nhận." />);
        const badge = screen.getByTestId('citation-badge');
        expect(badge).toHaveTextContent('[1]');
      });

      it('renders multiple citation badges', () => {
        render(<MessageContent content="Xem [1] và [2] để biết thêm." />);
        const badges = screen.getAllByTestId('citation-badge');
        expect(badges).toHaveLength(2);
        expect(badges[0]).toHaveTextContent('[1]');
        expect(badges[1]).toHaveTextContent('[2]');
      });

      it('preserves text segments between citations', () => {
        render(<MessageContent content="A [1] B [2] C" />);
        expect(screen.getByText('A ')).toBeInTheDocument();
        expect(screen.getByText(' B ')).toBeInTheDocument();
        expect(screen.getByText(' C')).toBeInTheDocument();
      });

      it('handles content with no text between citations', () => {
        render(<MessageContent content="[1][2]" />);
        const badges = screen.getAllByTestId('citation-badge');
        expect(badges).toHaveLength(2);
      });
    });
    ```

---

## Dev Notes

### Bối Cảnh & Mục Tiêu

Story này hoàn thiện **UX của vòng lặp chat** bằng 2 tính năng:
1. **Xác nhận + tăng cường Typewriter UX** (epic 3.5) — phần SSE receiver đã có từ story 3.2. Story này đảm bảo spinner "thinking" và auto-scroll hoạt động đúng (đã có code, cần verify visual).
2. **Citation Badge + Tooltip** (epic 3.10) — TỪ ĐẦU, FRONTEND ONLY.

Backend citation API (`GET /api/citations/{chunk_id}`) đã được implement ở **Story 3.4** (`citation_router.py`). Story 3.5 là frontend consumer của API đó.

### Đặc Điểm Quan Trọng: Ordinal vs UUID

Hiện tại mock RAG node trả về text không có citation tags. Khi real RAG được implement (story sau), LLM sẽ sinh `[1]`, `[2]` tương ứng với ordinal của chunks được retrieved.

**Vấn đề mapping**: Citation API dùng UUID (`GET /api/citations/{uuid}`), nhưng text chứa ordinal `[1]`. Mapping ordinal → UUID thuộc trách nhiệm của real RAG node (story tương lai, sẽ embed UUID vào SSE metadata).

**MVP Story 3.5**: `CitationBadge` nhận `citationId = ordinal` (e.g. `"1"`), truyền trực tiếp vào `/api/citations/1`. Backend FastAPI sẽ trả 422 (invalid UUID format). Frontend xử lý gracefully → tooltip hiển thị "Không tìm thấy thông tin trích dẫn". **Đây là hành vi đúng cho MVP** — UI interaction pattern hoàn chỉnh, data sẽ populate khi real RAG online.

Khi real RAG implement, SSE stream sẽ gửi `citation_map: {"1": "uuid-abc-...", "2": "uuid-xyz-..."}` qua event riêng. Frontend lúc đó cần update `CitationBadge` để nhận UUID thay vì ordinal. Thiết kế `citationId: string` prop đã sẵn sàng cho điều này.

### Phân Tích Code Hiện Tại (ChatbotPanel.tsx)

**AC#1 & AC#2 đã có sẵn:**
- `streamingContent === ''` → render `<span className={styles.thinking}>` ✅ (line 295-296)
- `messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })` ✅ (line 116)
- Blinking cursor `▋` trong streaming ✅ (line 300)

**Cần thêm (Task 5):**
- Import `MessageContent` và dùng trong render committed assistant messages (line 290)
- Streaming bubble KHÔNG dùng `MessageContent` — giữ nguyên `{streamingContent}` với cursor

### Cấu Trúc Component

```
ChatbotPanel.tsx (UPDATE)
  └── MessageContent.tsx (NEW)
        └── CitationBadge.tsx (NEW)
              └── getCitationDetail() in citations.ts (NEW)
```

**ChatbotPanel** không gọi citation API trực tiếp — delegate hoàn toàn qua CitationBadge.

### Tooltip Positioning Strategy

Dùng `position: absolute; bottom: calc(100% + 6px); left: 50%; transform: translateX(-50%)` — tooltip nổi lên TRÊN badge. Lý do: tin nhắn AI nằm phía trên chat, tooltip lên trên tránh bị che bởi các bubble phía dưới.

Nếu badge ở gần đầu conversation (đầu chat), tooltip có thể bị clip bởi top của `.messages` container. **MVP**: chấp nhận corner case này. Fix tương lai: dùng `getBoundingClientRect` để flip hướng.

### Tooltip Interaction: pointer-events: none

Tooltip có `pointer-events: none` vì MVP không cần interaction trong tooltip (không có nút copy, không có link). Nếu tương lai cần click trong tooltip, cần dùng hover-delay pattern:
```
onMouseLeave → setTimeout(200ms) → ẩn tooltip
onMouseEnter tooltip → clearTimeout → giữ tooltip
```

### Dependencies & Library

**Không cần thêm npm package mới.** CSS tooltip thuần + React state đủ cho MVP. Không dùng Radix UI, Floating UI, Tippy.js, v.v. — không có trong package.json và không nên thêm vào.

CSS Variables đã có trong codebase: `--accent-blue`, `--surface-raised`, `--border-hairline`, `--ink-primary`, `--ink-secondary`, `--surface-hover`.

### Thứ Tự Implement Đề Xuất

1. **Task 1** (`citations.ts`) → **Task 2 + 3** (`CitationBadge` + CSS) → **Task 6** (tests CitationBadge)
2. **Task 4** (`MessageContent`) → **Task 7** (tests MessageContent)
3. **Task 5** (update `ChatbotPanel`) → Visual verify

### Module & File Map

**Frontend — Files NEW:**
- `frontend/src/api/citations.ts`
- `frontend/src/components/CitationBadge.tsx`
- `frontend/src/components/CitationBadge.module.css`
- `frontend/src/components/MessageContent.tsx`
- `frontend/src/components/__tests__/CitationBadge.test.tsx`
- `frontend/src/components/__tests__/MessageContent.test.tsx`

**Frontend — Files UPDATE:**
- `frontend/src/features/workspace/ChatbotPanel.tsx` (import MessageContent + sửa render msg.content)

### CSS Pattern Hiện Tại

Tất cả components dùng CSS Modules (`.module.css`). Naming convention: camelCase class names (`.aiBubble`, `.userBubble`, `.suggestionPill`). Theo đúng pattern này cho CitationBadge.

### Test Setup

Vitest + React Testing Library + jsdom. Pattern mock module:
```typescript
vi.mock('@/api/citations', () => ({
  getCitationDetail: vi.fn(),
}));
```
Import lại sau `vi.mock` để có typed reference. Pattern này khớp với `ChatbotPanel.test.tsx` và các tests hiện tại.

### Rủi ro Cần Tránh

1. **KHÔNG dùng `MessageContent` trong streaming bubble** (line 298-302 của ChatbotPanel) — chunk có thể chứa `[1` chưa đóng ngoặc, parse sẽ không chính xác.
2. **KHÔNG thêm `useEffect` trong CitationBadge để auto-fetch khi mount** — phải fetch khi hover.
3. **KHÔNG sửa bất kỳ logic SSE/streaming hiện có** — chỉ thêm import + sửa render committed messages.
4. **KHÔNG dùng library tooltip bên ngoài** — không có trong package.json, thêm mới sẽ tăng bundle size không cần thiết cho MVP.

### References

- [Source: epics.md Story 3.5] — [Frontend] Typewriter UI & SSE Receiver AC
- [Source: epics.md Story 3.10] — [Frontend] Interactive Citation Tooltip UI AC
- [Source: architecture.md Section 8.3] — Citation Tooltip API: `GET /api/citations/{citation_id}`, fetch metadata + text chunk
- [Source: ux-designs/DESIGN.md Section 7] — Interactive Citation Tooltip: nền `surface-raised`, viền `border-hairline`, bo góc `rounded.lg`, `pointer-events: none`, tooltip nhỏ nổi
- [Source: ux-designs/DESIGN.md Section 4] — Chat panel: badge trích dẫn `[1]` màu `accent-blue` trong AI messages
- [Source: backend/src/modules/orchestrator/presentation/citation_router.py] — API endpoint `GET /api/citations/{chunk_id}`, response `{title, text}`
- [Source: frontend/src/features/workspace/ChatbotPanel.tsx] — State management, SSE logic, render messages
- [Source: frontend/src/api/chat.ts] — Pattern API client (axios, apiClient import)
- [Source: frontend/src/store/chatStore.ts] — `commitStreamingMessage` tạo ChatMessage với content string

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

(none)

### Completion Notes List

- Tạo `frontend/src/api/citations.ts`: API client dùng `apiClient` (axios instance có auth cookie), export `getCitationDetail(citationId)` → `CitationDetail { title, text }`.
- Tạo `frontend/src/components/CitationBadge.tsx`: Component badge với hover-on-demand fetch. TooltipState union type (hidden/loading/loaded/error). `fetchedRef` reset mỗi lần unhover → fetch lại.
- Tạo `frontend/src/components/CitationBadge.module.css`: Badge màu `--accent-blue` (rgba nhạt), tooltip absolute với `pointer-events: none`, `rounded.lg` 8px, shadow nhẹ.
- Tạo `frontend/src/components/MessageContent.tsx`: Split content bằng `CITATION_RE = /(\[\d+\])/g` (capturing group giữ delimiter), map từng part thành `CitationBadge` hoặc `<span>`.
- Cập nhật `frontend/src/features/workspace/ChatbotPanel.tsx`: Import `MessageContent`, render `<MessageContent content={msg.content} />` chỉ cho `msg.role === 'assistant'`. Streaming bubble không thay đổi.
- AC#1 & AC#2 đã có sẵn trong code hiện tại (spinner `thinking` + auto-scroll `scrollIntoView`).
- 10 unit tests: 5 cho `CitationBadge` + 5 cho `MessageContent` — tất cả pass. Không có regression mới (5 `ChatbotPanel` tests là pre-existing failures từ trước story này, do `scrollIntoView` không được mock trong jsdom).

### File List

- frontend/src/api/citations.ts (NEW)
- frontend/src/components/CitationBadge.tsx (NEW)
- frontend/src/components/CitationBadge.module.css (NEW)
- frontend/src/components/MessageContent.tsx (NEW)
- frontend/src/components/__tests__/CitationBadge.test.tsx (NEW)
- frontend/src/components/__tests__/MessageContent.test.tsx (NEW)
- frontend/src/features/workspace/ChatbotPanel.tsx (MODIFIED)

### Change Log

- 2026-06-17: Tạo story 3.5 — Giao Diện Tương Tác Thẻ Trích Dẫn. Bao gồm Epic 3.5 (Typewriter UI xác nhận) + Epic 3.10 (Interactive Citation Tooltip UI). (create-story agent: claude-sonnet-4-6)
- 2026-06-17: Implement story 3.5 — Citation Badge UI: API client, CitationBadge component, MessageContent parser, tích hợp vào ChatbotPanel. 10 unit tests pass. (dev agent: claude-sonnet-4-6)
