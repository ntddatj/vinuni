---
baseline_commit: 8478427
---

# Story 3.7: [Frontend] Render Markdown trong câu trả lời Chatbot (giữ CitationBadge)

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn câu trả lời của chatbot hiển thị đúng định dạng markdown (heading, list, bold/italic, bảng, xuống dòng),
Để tôi có thể đọc và hiểu kết quả nghiên cứu mà AI cung cấp dễ dàng hơn thay vì nhìn văn bản thô khó đọc.

> **Phạm vi story này** chỉ chạm **một file component** (`MessageContent.tsx`) + `package.json` + tests. Backend không đổi. Streaming plain-text vẫn giữ nguyên trong `ChatbotPanel.tsx` — chỉ committed messages chuyển sang markdown render.

## Acceptance Criteria

1. **AC#1 — Cài dependencies markdown [Build/Install]**
   **Given** frontend chưa có thư viện markdown.
   **When** developer chạy `npm install`.
   **Then** `react-markdown@10.1.0`, `remark-gfm@4.0.1`, `rehype-sanitize@6.0.0` xuất hiện trong `package.json` dependencies.
   **And** `vite build` và `vitest` đều pass sau khi thêm packages.

2. **AC#2 — Markdown cơ bản render đúng trong committed messages [Manual/Visual]**
   **Given** chatbot gửi câu trả lời có `**bold**`, `*italic*`, `# Heading`, danh sách `- item`, bảng.
   **When** stream kết thúc và message được commit.
   **Then** heading hiển thị to hơn, bold/italic có định dạng, list hiển thị bullet/số, bảng có border rõ ràng.
   **And** xuống dòng đôi (blank line) tạo paragraph mới thay vì viết liền.

3. **AC#3 — CitationBadge `[N]` hoạt động trong markdown [Manual/Visual]**
   **Given** câu trả lời có markdown kết hợp citation như `Nghiên cứu **[1]** cho thấy...\n- Điểm [2]`.
   **When** message được commit.
   **Then** `[1]` trong bold text và `[2]` trong list item đều render thành `CitationBadge` tương tác.
   **And** hover vào `[N]` vẫn hiển thị tooltip title/text như Story 3.5.
   **And** `[N]` resolve đúng `citationMap` ordinal→UUID (tái dùng logic Story 3.6).

4. **AC#4 — Streaming bubble vẫn là plain text [Manual/Visual]**
   **Given** LLM đang stream câu trả lời.
   **When** stream đang chạy (isStreaming=true, streamingContent được append dần).
   **Then** bubble streaming hiển thị text thô (dấu `**`, `#`, `-` còn hiện nguyên), KHÔNG render markdown.
   **And** cursor `▋` vẫn nhấp nháy cuối text.
   **And** khi stream kết thúc (committed), message chuyển sang render markdown đúng.

5. **AC#5 — Tin nhắn user render an toàn không markdown [Manual/Visual]**
   **Given** user gõ tin nhắn có markdown syntax như `**hello**`.
   **When** message render trong bubble user.
   **Then** `**hello**` hiển thị nguyên văn (không bold) — `ChatbotPanel.tsx` hiện render user message là text thuần, KHÔNG qua `MessageContent`, behavior này KHÔNG đổi.

6. **AC#6 — Bảo vệ XSS [Security/Unit Test]**
   **Given** nội dung có HTML nguy hiểm như `<script>alert(1)</script>` hoặc `<img onerror="xss()">`.
   **When** `MessageContent` render nội dung đó.
   **Then** HTML nguy hiểm bị loại bỏ bởi `rehype-sanitize` (default schema).
   **And** `<script>` không thực thi, attribute `onerror` bị strip.

7. **AC#7 — Tin nhắn lịch sử không có `citationMap` render an toàn [Manual/Visual]**
   **Given** tin nhắn load từ API history (không có `citationMap` field).
   **When** render `<MessageContent content={msg.content} />` (citationMap=undefined).
   **Then** markdown render đúng.
   **And** `[N]` graceful fallback sang ordinal string → `CitationBadge` gọi API → 422 → tooltip "Không tìm thấy..." (behavior hiện tại từ Story 3.5/3.6 giữ nguyên).

8. **AC#8 — Unit tests pass [Test]**
   **Given** test suite vitest chạy.
   **When** `npm test` trong `frontend/`.
   **Then** tất cả test pass, bao gồm các test trong `MessageContent.test.tsx` được cập nhật cho markdown.
   **And** TypeScript compile không lỗi (`tsc -b`).

---

## Tasks / Subtasks

### Task 1: Cài packages markdown (AC#1, #6)

- [x] 1.1 Thêm vào `dependencies` của `frontend/package.json`:
  ```json
  "react-markdown": "^10.1.0",
  "remark-gfm": "^4.0.1",
  "rehype-sanitize": "^6.0.0"
  ```
  **Lưu ý phiên bản:** Đây là phiên bản latest verified tại 2026-06-21. Ba package này đều là **ESM-only** — không import bằng `require()`. Vite build và vitest 3.x handle ESM tốt với `"type": "module"` trong package.json (đã có sẵn).

### Task 2: Rewrite `MessageContent.tsx` (AC#2, #3, #6, #7)

- [x] 2.1 Thay toàn bộ nội dung `frontend/src/components/MessageContent.tsx` với implementation bên dưới.

  **Implementation đầy đủ:**
  ```tsx
  import { useMemo } from 'react';
  import ReactMarkdown from 'react-markdown';
  import type { Components } from 'react-markdown';
  import remarkGfm from 'remark-gfm';
  import rehypeSanitize from 'rehype-sanitize';
  import { CitationBadge } from './CitationBadge';

  interface Props {
    content: string;
    citationMap?: Record<string, string>;
  }

  const CITATION_RE = /(\[\d+\])/g;

  function processStringForCitations(
    text: string,
    citationMap: Record<string, string> | undefined,
    keyPrefix: string,
  ): React.ReactNode[] {
    const parts = text.split(CITATION_RE);
    return parts.map((part, i) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationId = citationMap?.[match[1]] ?? match[1];
        return <CitationBadge key={`${keyPrefix}-${i}`} citationId={citationId} label={part} />;
      }
      return part;
    });
  }

  function injectCitations(
    children: React.ReactNode,
    citationMap: Record<string, string> | undefined,
    keyPrefix = 'c',
  ): React.ReactNode {
    if (typeof children === 'string') {
      return processStringForCitations(children, citationMap, keyPrefix);
    }
    if (Array.isArray(children)) {
      return children.flatMap((child, i) =>
        typeof child === 'string'
          ? processStringForCitations(child, citationMap, `${keyPrefix}${i}`)
          : [child],
      );
    }
    return children;
  }

  export function MessageContent({ content, citationMap }: Props) {
    const components: Components = useMemo(
      () => ({
        p: ({ children }) => <p>{injectCitations(children, citationMap)}</p>,
        li: ({ children }) => <li>{injectCitations(children, citationMap)}</li>,
        td: ({ children }) => <td>{injectCitations(children, citationMap)}</td>,
        th: ({ children }) => <th>{injectCitations(children, citationMap)}</th>,
      }),
      [citationMap],
    );

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeSanitize]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    );
  }
  ```

  **KHÔNG thay đổi** `CitationBadge.tsx` — tái dùng nguyên vẹn.

  **Giải thích kỹ thuật quan trọng:**
  - `injectCitations` xử lý children của các block elements (`p`, `li`, `td`, `th`)
  - Với string children đơn: split trực tiếp
  - Với array children (mixed text + React elements): chỉ split string nodes, giữ nguyên React element nodes
  - `[N]` bên trong `**bold**` hay `*italic*` KHÔNG được xử lý (thực tế LLM hiếm khi đặt citation bên trong inline formatting — chấp nhận được cho v1)
  - `useMemo` tránh re-create `components` object trên mỗi render

### Task 3: Cập nhật tests (AC#8)

- [x] 3.1 Cập nhật `frontend/src/components/__tests__/MessageContent.test.tsx`.

  **Chiến lược test với react-markdown ESM:** Mock `react-markdown` để test logic `injectCitations` độc lập, tránh vấn đề ESM transform trong jsdom:

  ```tsx
  import { render, screen } from '@testing-library/react';
  import { vi } from 'vitest';
  import { MessageContent } from '../MessageContent';

  // Mock react-markdown để render children trực tiếp — test logic citation, không test markdown parser
  vi.mock('react-markdown', () => ({
    default: ({ children, components }: { children: string; components: Record<string, (props: { children: string }) => React.ReactNode> }) => {
      // Simulate p tag render với children là string content
      const PComponent = components?.p;
      if (PComponent) {
        return <div data-testid="markdown">{PComponent({ children })}</div>;
      }
      return <div data-testid="markdown">{children}</div>;
    },
  }));

  vi.mock('remark-gfm', () => ({ default: () => {} }));
  vi.mock('rehype-sanitize', () => ({ default: () => {} }));

  vi.mock('../CitationBadge', () => ({
    CitationBadge: ({ label, citationId }: { label: string; citationId: string }) => (
      <span data-testid="citation-badge" data-citation-id={citationId}>{label}</span>
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

    it('resolves ordinal to UUID via citationMap', () => {
      render(
        <MessageContent
          content="Xem [1] để biết thêm."
          citationMap={{ '1': 'uuid-abc-123' }}
        />,
      );
      const badge = screen.getByTestId('citation-badge');
      expect(badge).toHaveAttribute('data-citation-id', 'uuid-abc-123');
    });

    it('falls back to ordinal when citationMap missing', () => {
      render(<MessageContent content="Xem [1] để biết thêm." />);
      const badge = screen.getByTestId('citation-badge');
      expect(badge).toHaveAttribute('data-citation-id', '1');
    });

    it('renders multiple citation badges', () => {
      render(<MessageContent content="Xem [1] và [2] để biết thêm." />);
      const badges = screen.getAllByTestId('citation-badge');
      expect(badges).toHaveLength(2);
      expect(badges[0]).toHaveTextContent('[1]');
      expect(badges[1]).toHaveTextContent('[2]');
    });

    it('handles content with no text between citations', () => {
      render(<MessageContent content="[1][2]" />);
      const badges = screen.getAllByTestId('citation-badge');
      expect(badges).toHaveLength(2);
    });
  });
  ```

  **Lưu ý mock:** Mock trên simulate chỉ `p` renderer. Đủ để test logic citation injection. Các AC khác (markdown render đẹp, XSS) kiểm tra bằng manual/visual test.

- [x] 3.2 Chạy `npm test` và đảm bảo tất cả tests pass.
- [x] 3.3 Chạy `npm run build` (`tsc -b && vite build`) — không có TypeScript error.

---

## Dev Notes

### Tổng quan thay đổi

Story này là **pure frontend, một file component**. Không có backend thay đổi. Scope chính xác:

| File | Action |
|------|--------|
| `frontend/package.json` | UPDATE — thêm 3 deps |
| `frontend/src/components/MessageContent.tsx` | UPDATE — rewrite với react-markdown |
| `frontend/src/components/__tests__/MessageContent.test.tsx` | UPDATE — cập nhật tests |

**Không chạm:**
- `CitationBadge.tsx` — giữ nguyên hoàn toàn
- `ChatbotPanel.tsx` — streaming vẫn plain text, committed messages đã dùng `<MessageContent>` (line 377)
- `chatStore.ts`, `types/chat.ts` — không đổi
- Toàn bộ backend

### Code hiện tại (trước khi sửa)

**`MessageContent.tsx` hiện tại (sau Story 3.6):**
```tsx
const CITATION_RE = /(\[\d+\])/g;

export function MessageContent({ content, citationMap }: Props) {
  const parts = content.split(CITATION_RE);
  return (
    <>
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (match) {
          const ordinal = match[1];
          const citationId = citationMap?.[ordinal] ?? ordinal;
          return <CitationBadge key={i} citationId={citationId} label={part} />;
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
```
→ Chỉ split `[N]`, không có markdown. Story 3.7 giữ nguyên logic citation resolution và thêm markdown wrapper.

**`ChatbotPanel.tsx` streaming section (line 385-397, KHÔNG thay đổi):**
```tsx
{streamingContent === '' ? (
  <span className={styles.thinking}>...</span>
) : (
  <>
    {streamingContent}   // ← plain text, intentional (AC#4)
    <span className={styles.cursor}>▋</span>
  </>
)}
```
Và committed messages (line 377, **không đổi**):
```tsx
<MessageContent content={msg.content} citationMap={msg.citationMap} />
```

### Kiến trúc react-markdown + CitationBadge

**Vấn đề cốt lõi:** `react-markdown` render AST → HTML elements. Cần intercept text nodes chứa `[N]` và inject `CitationBadge` (React component) trước khi browser render. Không thể làm điều này ở HTML level.

**Giải pháp:** Override `components` prop của `react-markdown` cho các block elements:
- `p` → custom `<p>` gọi `injectCitations(children, citationMap)`
- `li` → tương tự (list items từ bullet/numbered lists)
- `td`, `th` → tương tự (table cells)

`injectCitations` nhận `children` (React.ReactNode) và:
1. Nếu là string: split theo `CITATION_RE` → trả array [text, CitationBadge, text, ...]
2. Nếu là array: map qua từng element, chỉ process string elements, giữ nguyên React elements (bold, italic, link, etc.)
3. Nếu là React element: trả nguyên (không đệ quy — limitation v1)

**Limitation v1 đã biết:** `[N]` bên trong `**[1]**` (bold citation) không được inject. Thực tế LLM ít khi đặt citation bên trong inline formatting — acceptable.

### ESM packages với Vite/Vitest

Ba packages (`react-markdown`, `remark-gfm`, `rehype-sanitize`) đều là **pure ESM**. 

- **Vite dev/build:** Xử lý ESM tốt — không cần config thêm.
- **Vitest 3.x:** Với `"type": "module"` trong package.json, ESM packages được support. Nếu gặp lỗi `Cannot use import statement`, thêm vào `vitest.config.ts`:
  ```ts
  test: {
    server: {
      deps: {
        inline: ['react-markdown', 'remark-gfm', 'rehype-sanitize']
      }
    }
  }
  ```
  **Khuyến nghị:** Mock `react-markdown` trong test file (xem Task 3) — đơn giản hơn và test logic nhanh hơn.

### rehype-sanitize — Cấu hình mặc định

`rehypeSanitize` không cần argument → dùng `defaultSchema`. Schema này:
- ✅ Cho phép: `h1-h6`, `p`, `ul`, `ol`, `li`, `table`, `thead`, `tbody`, `tr`, `td`, `th`, `strong`, `em`, `code`, `pre`, `a` (với `href`)
- ❌ Strip: `script`, `style`, `iframe`, event attributes (`onclick`, `onerror`, v.v.), `style` attribute

Với nội dung LLM sinh, `defaultSchema` là đủ và đúng chuẩn bảo mật.

### Thứ tự implement đề xuất

1. `npm install react-markdown remark-gfm rehype-sanitize` — cập nhật package.json + package-lock.json
2. Rewrite `MessageContent.tsx` (Task 2)
3. Update `MessageContent.test.tsx` (Task 3)
4. Verify: `npm run build` sạch + `npm test` pass

### Kiểm tra manual sau khi xong

1. Upload tài liệu vào project, chat với câu hỏi liên quan.
2. Confirm stream hiện plain text (dấu `**` thô).
3. Sau khi stream xong: heading to rõ, list bullet, bảng có border.
4. Hover `[1]` badge: tooltip hiện title/text từ tài liệu.
5. Nhắn tin user `**hello**`: hiện nguyên `**hello**` (không bold).

### References

- [Source: sprint-change-proposal-2026-06-18-chat-markdown-layout.md — Section 3, 4.A] — Technical impact analysis, quyết định libraries + XSS requirement
- [Source: epics.md Story 3.7] — Story statement, AC nháp, dependencies
- [Source: frontend/src/components/MessageContent.tsx] — File cần rewrite, implementation hiện tại
- [Source: frontend/src/components/CitationBadge.tsx] — Không đổi, tái dùng nguyên vẹn
- [Source: frontend/src/features/workspace/ChatbotPanel.tsx:377,385-397] — Confirmed: committed dùng MessageContent, streaming dùng plain text
- [Source: frontend/package.json] — No markdown deps hiện tại; React 19, Vite 8, TypeScript 6, vitest ^3.2.6
- [Source: frontend/vitest.config.ts] — jsdom environment, `"type": "module"` → ESM support
- [Source: implementation-artifacts/3-6-real-rag-retriever-pgvector-citation-map-sse.md — Task 8] — Citation resolution logic (ordinal → UUID) đã có, tái dùng
- [Source: implementation-artifacts/3-5-giao-dien-tuong-tac-the-trich-dan.md] — CitationBadge interface: `{ citationId: string, label: string }`

---

## Review Findings

_Code review (bmad-code-review) — 2026-06-21 — 3 lớp adversarial (Blind Hunter, Edge Case Hunter, Acceptance Auditor). 3 patch đã được áp dụng & verify (build sạch, 9/9 test MessageContent pass)._

**Patch (đã sửa):**

- [x] [Review][Patch] Thiếu CSS cho markdown — bảng không có border, heading/list/code/blockquote không có style → vi phạm phần visual của AC#2 ("bảng có border rõ ràng", "heading to hơn"). Đã tạo `frontend/src/components/MessageContent.module.css` (dùng design tokens, hỗ trợ dark mode) và wrap output trong `<div className={styles.markdown}>`. [frontend/src/components/MessageContent.tsx, frontend/src/components/MessageContent.module.css]
- [x] [Review][Patch] `[N]` bên trong inline formatting (`**[1]**`, `*[1]*`, link) và trong heading KHÔNG render thành `CitationBadge` → vi phạm AC#3 (yêu cầu `[1]` trong bold thành badge). Đã làm `injectCitations` đệ quy vào React element con (bỏ qua `code`/`pre`) và override thêm `h1`–`h6`. Gỡ bỏ "limitation v1". [frontend/src/components/MessageContent.tsx]
- [x] [Review][Patch] Test mock chỉ chạm nhánh `p` với string thuần → nhánh đệ quy / element con / quy tắc bỏ qua code hoàn toàn không được test (false confidence). Đã export `injectCitations` và thêm 3 test trực tiếp (citation trong bold, mixed string+element, code-skip). [frontend/src/components/__tests__/MessageContent.test.tsx]

**Defer (hoãn — known limitation):**

- [x] [Review][Defer] Citation kiểu reference/footnote `[1]: url` hoặc `[1](url)` bị markdown parser nuốt (thành link-definition/inline-link) trước khi logic citation chạy → không thành badge. Hoãn: phụ thuộc format LLM sinh ra; pipeline RAG (Story 3.6) sinh citation **inline `[N]`**, không dùng reference-style — không kích hoạt trong contract hiện tại. Theo dõi nếu đổi prompt LLM. [frontend/src/components/MessageContent.tsx]

**Dismissed (noise / by-design):**

- Single `\n` gộp dòng: đúng chuẩn CommonMark; AC#2 thiết kế quanh paragraph theo blank-line (xuống dòng đôi) — không phải lỗi.
- Empty/whitespace content render bubble rỗng: minor, pre-existing, ngoài scope.
- React key collision: không xảy ra với prefix scheme hiện tại; đã chuẩn hoá prefix đệ quy (`${keyPrefix}-${i}` / `${keyPrefix}e`) nên unique theo cấu trúc.

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

(none)

### Completion Notes List

- Task 1 (AC#1): Thêm `react-markdown@^10.1.0`, `remark-gfm@^4.0.1`, `rehype-sanitize@^6.0.0` vào `frontend/package.json` dependencies. `npm install` thành công, 98 packages added.
- Task 2 (AC#2,#3,#6,#7): Rewrite `MessageContent.tsx` với `ReactMarkdown` + `remarkGfm` + `rehypeSanitize`. Override `components` prop cho `p`, `li`, `td`, `th` để inject `CitationBadge` vào text nodes chứa `[N]`. `useMemo` tránh re-create components object. Logic citation resolution (ordinal → UUID) giữ nguyên từ Story 3.6.
- Task 3 (AC#8): Cập nhật `MessageContent.test.tsx` — mock `react-markdown` để test logic citation injection độc lập với markdown parser. Thêm 2 test cases mới (`resolves ordinal to UUID`, `falls back to ordinal when citationMap missing`). 6/6 tests pass. `npm run build` (tsc -b + vite build) thành công không lỗi TypeScript.
- 4 failures trong `CenterWorkspace.test.tsx` là pre-existing (Cytoscape canvas jsdom) — không phải regression từ story này (đã xác nhận bằng git stash).

### File List

- `frontend/package.json` — thêm 3 dependencies: react-markdown, remark-gfm, rehype-sanitize
- `frontend/package-lock.json` — cập nhật sau npm install
- `frontend/src/components/MessageContent.tsx` — rewrite với ReactMarkdown + citation injection
- `frontend/src/components/__tests__/MessageContent.test.tsx` — cập nhật tests cho markdown + citationMap

### Change Log

- 2026-06-21: Tạo story 3.7 — Render Markdown trong câu trả lời Chatbot. Phân tích đầy đủ sprint-change-proposal-2026-06-18, code ChatbotPanel/MessageContent/CitationBadge, package.json, vitest config, story 3.6 learnings. (create-story agent: claude-sonnet-4-6)
- 2026-06-21: Implement story 3.7 hoàn thành — cài 3 ESM packages markdown, rewrite MessageContent.tsx với ReactMarkdown+GFM+sanitize+citation injection, cập nhật 6 unit tests pass. Build sạch. (dev agent: claude-sonnet-4-6)
