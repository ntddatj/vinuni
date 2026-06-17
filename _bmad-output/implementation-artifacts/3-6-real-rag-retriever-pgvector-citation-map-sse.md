---
baseline_commit: fbf805ea528adaab8887c20395244948b35c4496
---

# Story 3.6: Real RAG Retriever — pgvector Similarity & Citation Map qua SSE

Status: done

## Story

Với vai trò là người dùng,
Tôi muốn câu trả lời của chatbot được trích dẫn từ tài liệu thực tế trong dự án và thẻ `[1]`, `[2]` khi hover hiển thị đúng nội dung từ DB,
Để tôi có thể kiểm chứng độ chính xác của từng phát biểu mà AI đưa ra.

> **Phạm vi story này** gỡ nợ kỹ thuật ghi tại Story 3.2 và thực hiện 4 thay đổi đồng bộ:
> 1. **Backend**: Thay `mock_rag_node` → `real_rag_node` (embed + pgvector cosine + LLM streaming thật)
> 2. **Backend**: Refactor `_stream_graph_to_queue` sang `astream_events` (token stream thật, không còn vòng lặp 50ms giả)
> 3. **Backend**: SSE protocol mở rộng thêm frame `citation_map` + `done.content`
> 4. **Frontend**: `ChatbotPanel` nhận `citation_map`, `MessageContent` resolve ordinal→UUID trước khi gọi API citation

## Acceptance Criteria

1. **AC#1 — `real_rag_node` embed câu hỏi và truy vấn pgvector [Unit Test]**
   **Given** thread thuộc project có ít nhất 1 tài liệu đã ingest (có `child_chunks` với embedding).
   **When** người dùng gửi câu hỏi.
   **Then** backend gọi `GeminiEmbeddingClient.embed_batch([query])` để lấy vector 768 chiều.
   **And** truy vấn `child_chunks` với `embedding <=> query_vec` (cosine distance), scope `project_id`, `ORDER BY distance LIMIT 5`.
   **And** HNSW index `idx_child_chunks_embedding_hnsw` (vector_cosine_ops) được sử dụng.

2. **AC#2 — Build context ordinal và gọi LLM sinh câu trả lời có `[N]` [Integration Test]**
   **Given** retrieval trả về K chunks (K ≤ 5).
   **When** node tạo context prompt.
   **Then** mỗi chunk được đánh ordinal `[1]...[K]` trong context.
   **And** LLM (via `LLMRouter.get_llm_client(user_id)`) nhận prompt có context + câu hỏi và sinh câu trả lời có `[N]`.
   **And** node trả `valid_citation_ids = [1..K]` (cho Guardrail) và `citation_map = {1: "<uuid>", ..., K: "<uuid>"}`.

3. **AC#3 — Empty retrieval không gọi LLM [Unit Test]**
   **Given** project chưa có tài liệu (hoặc không có chunk nào khớp query).
   **When** người dùng gửi câu hỏi.
   **Then** `real_rag_node` trả câu cố định `"Chưa có tài liệu liên quan trong dự án để trích dẫn."` mà **không** gọi LLM.
   **And** `valid_citation_ids = []`, `citation_map = {}`.

4. **AC#4 — Stream token thật qua SSE (không còn giả-stream 50ms) [Manual/Visual]**
   **Given** LLM đang sinh câu trả lời.
   **When** frontend nhận SSE stream.
   **Then** các frame `{"chunk": "token"}` đến với tốc độ tự nhiên của LLM, không đều (khác hẳn 50ms/char đồng đều cũ).
   **And** "AI is thinking..." spinner vẫn hiển thị đến chunk đầu tiên.

5. **AC#5 — SSE phát `citation_map` event trước `done` [Integration Test]**
   **Given** real RAG trả về citation_map không rỗng.
   **When** streaming kết thúc.
   **Then** SSE phát frame `data: {"event": "citation_map", "data": {"1": "<uuid>", "2": "<uuid>", ...}}\n\n` TRƯỚC frame `done`.
   **And** frame `done` mang `content` là câu trả lời đã qua guardrail: `data: {"event": "done", "content": "<cleaned answer>"}\n\n`.

6. **AC#6 — Citation Guardrail nhận `valid_citation_ids` thật và lọc đúng [Unit Test]**
   **Given** LLM sinh câu trả lời có `[1]`, `[2]`, `[7]` nhưng chỉ retrieve 5 chunks.
   **When** `citation_guardrail_node` chạy.
   **Then** `[1]` và `[2]` giữ nguyên, `[7]` bị thay bằng `[Nguồn không xác định]`.
   **And** guardrail logic hiện tại trong `graph.py` **không thay đổi** — chỉ lần đầu nhận data thật.

7. **AC#7 — Frontend `CitationBadge` nhận UUID thật và tooltip hiển thị đúng [Manual/Visual]**
   **Given** frontend nhận `citation_map` từ SSE.
   **When** tin nhắn được commit (done event) và người dùng hover `[1]`.
   **Then** `CitationBadge` gọi `GET /api/citations/<uuid>` (UUID thật, không phải ordinal `"1"`).
   **And** tooltip hiển thị `title` và `text` chunk thật từ DB.
   **And** tooltip không còn nhận 422 như trước.

8. **AC#8 — Tin nhắn lịch sử cũ (không có citation_map) vẫn graceful [Manual/Visual]**
   **Given** tin nhắn được load từ API lịch sử (không có `citationMap` field).
   **When** người dùng hover `[1]` trong tin nhắn lịch sử.
   **Then** `CitationBadge` fallback sang ordinal làm `citationId` → API trả 422 → tooltip hiển thị `"Không tìm thấy thông tin trích dẫn"` (graceful, không crash).

9. **AC#9 — Owner scoping: chỉ retrieve chunk thuộc project của user [Unit Test]**
   **Given** có nhiều project với chunks khác nhau.
   **When** RAG query chạy.
   **Then** query luôn có `WHERE child_chunks.project_id = :project_id`.
   **And** không bao giờ leak chunk của project khác (chống IDOR, nhất quán với `GetCitationDetailUseCase`).

10. **AC#10 — Latency RAG < 500ms khi DB < 100k vector [Performance]**
    **Given** HNSW index đã tồn tại (tạo bởi migration 006).
    **When** query pgvector cosine similarity.
    **Then** SELECT với ORDER BY `<=>` + LIMIT 5 chạy dưới 500ms (NFR3).
    **And** truy vấn dùng đúng `vector_cosine_ops` (đã có trong HNSW index migration 006).

> 🔍 **Cách nghiệm thu trực quan (AC#4, #7, #8):**
> 1. Upload ít nhất 1 tài liệu PDF vào project, chờ ingestion done.
> 2. Mở Chat, hỏi câu liên quan đến tài liệu.
> 3. Thấy tokens đến không đều (stream thật). Sau done, thấy `[1]`, `[2]` badge.
> 4. Hover vào `[1]`: tooltip hiện text chunk thật từ tài liệu.
> 5. Reload trang, vào lại chat history, hover badge: tooltip "Không tìm thấy thông tin trích dẫn" (graceful fallback vì history không có citation_map).

---

## Tasks / Subtasks

### BACKEND — graph.py: ChatState + real_rag_node (AC#1, #2, #3, #6, #9)

- [x] **Task 1**: Cập nhật `backend/src/modules/orchestrator/application/graph.py`
  - [x] 1.1 Thêm `citation_map: dict[int, str]` vào `ChatState`:
    ```python
    class ChatState(TypedDict):
        messages: Annotated[list, add_messages]
        valid_citation_ids: list[int]   # ordinals [1..K] cho Guardrail
        citation_map: dict[int, str]    # NEW: ordinal → chunk UUID cho frontend
    ```
    **Lưu ý**: KHÔNG thêm `project_id`/`user_id` vào state — truyền qua `config["configurable"]` để không lưu thừa vào checkpoint.

  - [x] 1.2 Thêm async `real_rag_node`. Import cần thiết ở đầu file:
    ```python
    import logging
    from langchain_core.runnables import RunnableConfig
    from sqlalchemy import select, literal
    from pgvector.sqlalchemy import Vector
    from backend.src.modules.ingestion.infrastructure.chunk_orm_models import ChildChunkORM
    from backend.src.modules.ingestion.infrastructure.embedding_client import GeminiEmbeddingClient
    from backend.src.shared.infra.database import AsyncSessionMaker
    from backend.src.shared.infra.llm.router import LLMRouter
    ```
    
    Triển khai node:
    ```python
    logger = logging.getLogger(__name__)
    TOP_K = 5  # số chunk retrieve tối đa
    
    RAG_SYSTEM_PROMPT = (
        "Bạn là trợ lý nghiên cứu học thuật. Dựa vào các tài liệu sau, hãy trả lời câu hỏi. "
        "Khi trích dẫn, dùng số trong ngoặc vuông như [1], [2] để chỉ tài liệu tương ứng. "
        "Chỉ sử dụng các nguồn được cung cấp, không bịa đặt thông tin."
    )
    
    EMPTY_RETRIEVAL_MSG = "Chưa có tài liệu liên quan trong dự án để trích dẫn."
    
    async def real_rag_node(state: ChatState, config: RunnableConfig) -> dict:
        """RAG thật: embed câu hỏi, cosine search pgvector, stream LLM."""
        user_id: str = config["configurable"]["user_id"]
        project_id: str = config["configurable"]["project_id"]
    
        # Lấy câu hỏi mới nhất từ state
        from langchain_core.messages import HumanMessage as LCHumanMessage
        last_human = next(
            (m for m in reversed(state["messages"]) if isinstance(m, LCHumanMessage)),
            None,
        )
        if not last_human:
            return {
                "messages": [AIMessage(content="Không có câu hỏi để trả lời.")],
                "valid_citation_ids": [],
                "citation_map": {},
            }
        query = last_human.content if isinstance(last_human.content, str) else ""
    
        async with AsyncSessionMaker() as db:
            # 1) Embed câu hỏi
            embedding_client = GeminiEmbeddingClient(user_id, db)
            embeddings = await embedding_client.embed_batch([query])
            query_embedding = embeddings[0]
    
            # 2) Cosine similarity search (HNSW index vector_cosine_ops)
            query_vec = literal(query_embedding, Vector(768))
            stmt = (
                select(ChildChunkORM.id, ChildChunkORM.content)
                .where(ChildChunkORM.project_id == project_id)
                .where(ChildChunkORM.embedding.is_not(None))
                .order_by(ChildChunkORM.embedding.op("<=>")(query_vec))
                .limit(TOP_K)
            )
            result = await db.execute(stmt)
            rows = result.fetchall()
    
            # 3) Empty retrieval → trả câu cố định, không gọi LLM
            if not rows:
                return {
                    "messages": [AIMessage(content=EMPTY_RETRIEVAL_MSG)],
                    "valid_citation_ids": [],
                    "citation_map": {},
                }
    
            # 4) Build citation_map và context
            citation_map: dict[int, str] = {i + 1: str(row.id) for i, row in enumerate(rows)}
            valid_citation_ids: list[int] = list(citation_map.keys())
            context = "\n\n".join(
                f"[{ordinal}] {row.content}"
                for ordinal, row in zip(citation_map.keys(), rows)
            )
    
            # 5) LLM client (lấy trong cùng session để resolve API key)
            llm_router = LLMRouter(db)
            llm = await llm_router.get_llm_client(user_id)
    
        # 6) Gọi LLM (ngoài session đã đóng — chỉ cần llm object)
        prompt = f"{RAG_SYSTEM_PROMPT}\n\nTài liệu nghiên cứu:\n{context}\n\nCâu hỏi: {query}"
        full_response = ""
        async for chunk in llm.astream([HumanMessage(content=prompt)]):
            if isinstance(chunk.content, str):
                full_response += chunk.content
    
        return {
            "messages": [AIMessage(content=full_response)],
            "valid_citation_ids": valid_citation_ids,
            "citation_map": citation_map,
        }
    ```
    **Import HumanMessage từ langchain_core**: đã import ở top của file gốc.
    **Pitfall quan trọng**: `AsyncSessionMaker()` tạo session mới — không tái dùng session của request (đã đóng). Pattern này nhất quán với `_stream_graph_to_queue` hiện tại.

  - [x] 1.3 Cập nhật `build_graph`:
    ```python
    def build_graph(checkpointer: AsyncPostgresSaver):
        builder = StateGraph(ChatState)
        builder.add_node("real_rag", real_rag_node)        # thay mock_rag
        builder.add_node("citation_guardrail", citation_guardrail_node)
        builder.set_entry_point("real_rag")                # thay mock_rag
        builder.add_edge("real_rag", "citation_guardrail") # thay mock_rag
        builder.set_finish_point("citation_guardrail")
        return builder.compile(checkpointer=checkpointer)
    ```
  
  - [x] 1.4 Xóa hàm `mock_rag_node` (và comment "DummyRetriever" liên quan).

### BACKEND — run_registry.py: Queue type (AC#5)

- [x] **Task 2**: Cập nhật `backend/src/modules/orchestrator/infrastructure/run_registry.py`
  - [x] 2.1 Đổi type annotation của `_registry` và hàm `create_run`:
    ```python
    import asyncio
    
    _registry: dict[str, asyncio.Queue[dict | None]] = {}
    _owners: dict[str, str] = {}
    
    def create_run(run_id: str, user_id: str) -> asyncio.Queue[dict | None]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()
        _registry[run_id] = queue
        _owners[run_id] = user_id
        return queue
    
    def get_run_queue(run_id: str) -> asyncio.Queue[dict | None] | None:
        return _registry.get(run_id)
    
    # get_run_owner, delete_run: giữ nguyên
    ```

### BACKEND — use_cases.py: SendMessageUseCase + _stream_graph_to_queue (AC#4, #5)

- [x] **Task 3**: Cập nhật `backend/src/modules/orchestrator/application/use_cases.py`
  - [x] 3.1 Cập nhật `SendMessageUseCase.execute` để truyền `project_id` + `user_id`:
    ```python
    async def execute(self, dto: SendMessageDTO) -> str:
        thread = await self._repo.find_by_id(dto.thread_id)
        if thread is None:
            raise ThreadNotFoundError(dto.thread_id)
        if thread.user_id != dto.user_id:
            raise ThreadAccessDeniedError(dto.thread_id)
    
        await self._repo.save_message(dto.thread_id, "user", dto.message)
    
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        queue = create_run(run_id, dto.user_id)
    
        task = asyncio.create_task(
            _stream_graph_to_queue(
                run_id=run_id,
                thread_id=dto.thread_id,
                user_id=dto.user_id,             # NEW
                project_id=thread.project_id,    # NEW
                message=dto.message,
                queue=queue,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        return run_id
    ```

  - [x] 3.2 Thay thế toàn bộ `_stream_graph_to_queue` bằng implementation dùng `astream_events`:
    ```python
    async def _stream_graph_to_queue(
        run_id: str,
        thread_id: str,
        user_id: str,
        project_id: str,
        message: str,
        queue: "asyncio.Queue[dict | None]",
    ) -> None:
        """Background task: stream token thật từ LangGraph, lưu assistant message, emit citation_map.
    
        Dùng astream_events (version v2) thay vì ainvoke + fake char loop.
        Session DB tự tạo trong node — không leak session request-scoped.
        """
        try:
            from langchain_core.messages import HumanMessage
    
            checkpointer = await get_postgres_checkpointer()
            graph = build_graph(checkpointer)
            config = {
                "configurable": {
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "project_id": project_id,
                }
            }
    
            # Stream token thật qua astream_events
            async for event in graph.astream_events(
                {"messages": [HumanMessage(content=message)]},
                config=config,
                version="v2",
            ):
                kind = event["event"]
                if kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"]
                    if isinstance(chunk.content, str) and chunk.content:
                        await queue.put({"type": "chunk", "data": chunk.content})
    
            # Lấy state cuối (sau khi guardrail đã sửa) qua checkpointer
            final_snapshot = await graph.aget_state(config)
            final_state = final_snapshot.values
    
            citation_map: dict[int, str] = final_state.get("citation_map", {})
            msgs = final_state.get("messages", [])
            final_content: str = ""
            if msgs:
                last = msgs[-1]
                final_content = last.content if isinstance(last.content, str) else ""
    
            # Lưu vào DB
            async with AsyncSessionMaker() as session:
                repo = PostgresChatThreadRepository(session)
                await repo.save_message(thread_id, "assistant", final_content)
    
            # Emit citation_map rồi done (frontend sẽ replace streamingContent bằng final_content đã sạch)
            if citation_map:
                await queue.put({"type": "citation_map", "data": citation_map})
            await queue.put({"type": "done", "content": final_content})
    
        except Exception:
            logger.exception(
                "Lỗi khi stream graph run_id=%s thread_id=%s", run_id, thread_id
            )
        finally:
            # Sentinel failsafe: khi exception xảy ra trước khi emit done, event_generator không bị block mãi.
            await queue.put(None)
            delete_run(run_id)
    ```
    **Quan trọng**: `graph.aget_state(config)` tra cứu state qua PostgresSaver checkpointer — đây là state cuối sau khi `citation_guardrail_node` đã chạy. `final_content` là câu trả lời đã được làm sạch.

### BACKEND — router.py: event_generator (AC#5)

- [x] **Task 4**: Cập nhật `event_generator` trong `backend/src/modules/orchestrator/presentation/router.py`
  - [x] 4.1 Thay `event_generator` cũ:
    ```python
    async def event_generator():
        while True:
            item = await queue.get()
            if item is None:
                # Exception fallback: emit done không có content rồi thoát
                yield f"data: {json.dumps({'event': 'done'})}\n\n"
                break
            t = item.get("type")
            if t == "chunk":
                yield f"data: {json.dumps({'chunk': item['data']})}\n\n"
            elif t == "citation_map":
                yield f"data: {json.dumps({'event': 'citation_map', 'data': item['data']})}\n\n"
            elif t == "done":
                yield f"data: {json.dumps({'event': 'done', 'content': item.get('content', '')})}\n\n"
                break
    ```
    Phần còn lại của handler `stream_chat` (queue check, owner check, StreamingResponse) **giữ nguyên**.

### FRONTEND — types/chat.ts: thêm citationMap (AC#7, #8)

- [x] **Task 5**: Cập nhật `frontend/src/types/chat.ts`
  - [x] 5.1 Thêm optional field `citationMap` vào `ChatMessage`:
    ```typescript
    export interface ChatMessage {
      id: string;
      threadId: string;
      role: 'user' | 'assistant';
      content: string;
      createdAt: string;
      citationMap?: Record<string, string>; // ordinal → chunk UUID (frontend-only, không có trong API response)
    }
    ```
    **Lưu ý**: `Record<string, string>` vì JSON serializes int keys thành string (`{1: "uuid"}` → `{"1": "uuid"}`).

### FRONTEND — chatStore.ts: cập nhật commitStreamingMessage (AC#7)

- [x] **Task 6**: Cập nhật `frontend/src/store/chatStore.ts`
  - [x] 6.1 Thêm signature mới cho `commitStreamingMessage` trong interface `ChatState`:
    ```typescript
    commitStreamingMessage: (cleanedContent?: string, citationMap?: Record<string, string>) => void;
    ```
  - [x] 6.2 Cập nhật implementation:
    ```typescript
    commitStreamingMessage: (cleanedContent?: string, citationMap?: Record<string, string>) => {
        // Dùng cleanedContent từ SSE done event (đã qua guardrail) nếu có,
        // fallback về streamingContent (bản chưa clean) cho backward compat
        const content = cleanedContent ?? get().streamingContent;
        if (!content) {
            set({ streamingContent: '', isStreaming: false });
            return;
        }
        const assistantMsg: ChatMessage = {
            id: `stream-${Date.now()}`,
            threadId: get().activeThreadId ?? '',
            role: 'assistant',
            content,
            createdAt: new Date().toISOString(),
            citationMap,  // undefined nếu không có map (graceful)
        };
        set((s) => ({
            messages: [...s.messages, assistantMsg],
            streamingContent: '',
            isStreaming: false,
        }));
    },
    ```

### FRONTEND — ChatbotPanel.tsx: xử lý citation_map SSE + truyền xuống (AC#5, #7)

- [x] **Task 7**: Cập nhật `frontend/src/features/workspace/ChatbotPanel.tsx`
  - [x] 7.1 Thêm `citationMapRef` (lưu citation_map trong lần stream hiện tại):
    ```tsx
    const citationMapRef = useRef<Record<string, string>>({});
    ```

  - [x] 7.2 Cập nhật `es.onmessage` handler để xử lý frame mới:
    ```tsx
    es.onmessage = (e) => {
        let data: {
            event?: string;
            chunk?: string;
            content?: string;
            data?: Record<string, string>;
        };
        try {
            data = JSON.parse(e.data);
        } catch {
            return;
        }
        if (data.event === 'done') {
            commitStreamingMessage(data.content, citationMapRef.current);
            citationMapRef.current = {};
            closeStream();
        } else if (data.event === 'citation_map') {
            citationMapRef.current = data.data ?? {};
        } else if (typeof data.chunk === 'string') {
            appendChunk(data.chunk);
        }
    };
    ```

  - [x] 7.3 Cập nhật render tin nhắn committed để truyền `citationMap`:
    ```tsx
    {msg.role === 'assistant' ? (
        <MessageContent content={msg.content} citationMap={msg.citationMap} />
    ) : (
        msg.content
    )}
    ```
    **KHÔNG thay đổi** streaming bubble (giữ `{streamingContent}` plain text trong lúc stream).

  - [x] 7.4 Reset `citationMapRef` khi đổi project:
    ```tsx
    useEffect(() => {
        closeStream();
        citationMapRef.current = {};
        reset();
    }, [activeProjectId]);
    ```

### FRONTEND — MessageContent.tsx: resolve ordinal → UUID (AC#7, #8)

- [x] **Task 8**: Cập nhật `frontend/src/components/MessageContent.tsx`
  - [x] 8.1 Thêm prop `citationMap` và resolve trước khi truyền xuống `CitationBadge`:
    ```tsx
    interface Props {
        content: string;
        citationMap?: Record<string, string>; // NEW
    }
    
    const CITATION_RE = /(\[\d+\])/g;
    
    export function MessageContent({ content, citationMap }: Props) {
        const parts = content.split(CITATION_RE);
        return (
            <>
                {parts.map((part, i) => {
                    const match = part.match(/^\[(\d+)\]$/);
                    if (match) {
                        const ordinal = match[1];
                        // Resolve ordinal → UUID nếu có map; fallback ordinal nếu không có (tin nhắn cũ)
                        const citationId = citationMap?.[ordinal] ?? ordinal;
                        return (
                            <CitationBadge
                                key={i}
                                citationId={citationId}
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
    **`CitationBadge.tsx` không thay đổi** — nó đã nhận `citationId: string` và truyền thẳng vào `getCitationDetail(citationId)`. Khi nhận UUID, API trả data thật. Khi nhận ordinal (fallback), API 422 → tooltip graceful "Không tìm thấy..." (AC#8).

### BACKEND — Unit Tests (AC#1, #3, #6, #9)

- [x] **Task 9**: Tạo/cập nhật `tests/unit/orchestrator/test_real_rag_node.py`
  - [x] 9.1 Test `real_rag_node` — empty retrieval không gọi LLM (AC#3):
    ```python
    async def test_real_rag_node_empty_retrieval_no_llm(mock_db_empty):
        # Khi pgvector trả [] → trả EMPTY_RETRIEVAL_MSG, không gọi LLM
        state = ChatState(messages=[HumanMessage("Hỏi về RAG")], valid_citation_ids=[], citation_map={})
        config = {"configurable": {"thread_id": "t1", "user_id": "u1", "project_id": "p1"}}
        result = await real_rag_node(state, config)
        assert result["messages"][0].content == EMPTY_RETRIEVAL_MSG
        assert result["citation_map"] == {}
        assert result["valid_citation_ids"] == []
        # LLM không được gọi
    ```
  - [x] 9.2 Test `real_rag_node` — build citation_map đúng ordinal (AC#2, #9):
    ```python
    async def test_real_rag_node_builds_citation_map(mock_db_with_chunks):
        # Khi pgvector trả 3 chunks → citation_map = {1: uuid1, 2: uuid2, 3: uuid3}
        ...
        result = await real_rag_node(state, config)
        assert result["citation_map"] == {1: "uuid-1", 2: "uuid-2", 3: "uuid-3"}
        assert result["valid_citation_ids"] == [1, 2, 3]
    ```
  - [x] 9.3 Tái dùng `test_citation_guardrail.py` hiện có để test guardrail nhận ordinals thật (AC#6):
    File `tests/unit/orchestrator/test_citation_guardrail.py` đã có — KHÔNG thay đổi logic test.

---

## Dev Notes

### Bối Cảnh & Mục Tiêu

Story này "nối dây" cuối cùng cho FR6 + FR10 hoạt động end-to-end thật. Toàn bộ pipeline ingestion → chunking → embedding → pgvector (HNSW) đã có từ Story 2.5. Citation Guardrail đã có từ Story 3.4. Citation Badge UI đã có từ Story 3.5. Story 3.6 chỉ cần:

1. Thay 1 node trong LangGraph (`mock_rag` → `real_rag`)
2. Refactor cách stream (ainvoke + fake loop → astream_events token thật)
3. Mở rộng SSE protocol thêm 2 frame (`citation_map`, `done.content`)
4. Plumb citation_map từ SSE xuống CitationBadge qua MessageContent

### Sơ Đồ Luồng Hoàn Chỉnh

```
User gõ → POST /chat/threads/{id}/messages
           ↓
      SendMessageUseCase
        - read thread → project_id, user_id
        - save user message
        - create run_id, queue
        - spawn background task
           ↓ (background)
      _stream_graph_to_queue
        - build config = {thread_id, user_id, project_id}
        - astream_events graph
              ↓ (real_rag_node)
              - embed query (GeminiEmbeddingClient)
              - pgvector cosine search (child_chunks, scope project_id)
              - build citation_map {1: uuid, ...}
              - llm.astream(prompt + context)
                  → on_chat_model_stream events → queue.put(chunk frames)
              ↓ (citation_guardrail_node)
              - regex replace [N] không hợp lệ
        - aget_state → final state (sau guardrail)
        - save final_content to DB
        - queue.put(citation_map frame)
        - queue.put(done frame với final_content)
        - finally: queue.put(None)
           ↓ (SSE)
      event_generator (router.py)
        - chunk frames → {"chunk": "token"}
        - citation_map frame → {"event": "citation_map", "data": {...}}
        - done frame → {"event": "done", "content": "<cleaned>"}
        - None → {"event": "done"} (exception fallback)
           ↓ (Frontend)
      ChatbotPanel.tsx es.onmessage
        - chunk → appendChunk
        - citation_map → citationMapRef.current
        - done → commitStreamingMessage(content, citationMapRef)
              → ChatMessage { ..., citationMap: {1: uuid, ...} }
           ↓ (render)
      MessageContent({ content, citationMap })
        - parse [1] → citationId = citationMap["1"] (UUID)
        - CitationBadge(citationId=uuid)
              → hover → GET /api/citations/<uuid> → {title, text} ✅
```

### Phân Tích Code Hiện Tại Cần Thay Đổi

**`graph.py:29` — `mock_rag_node` hiện tại:**
```python
def mock_rag_node(state: ChatState) -> dict:
    return {
        "messages": [AIMessage(content="Đây là câu trả lời mock...")],
        "valid_citation_ids": [],  # Không có chunk thật
    }
```
→ Xóa hoàn toàn. Thay bằng async `real_rag_node(state, config)`.

**`use_cases.py:219-229` — `_stream_graph_to_queue` hiện tại:**
```python
result = await graph.ainvoke(...)
for char in answer:
    await queue.put(char)
    await asyncio.sleep(0.05)  # 50ms per character — giả-stream
```
→ Xóa hoàn toàn. Thay bằng `astream_events` pattern.

**`run_registry.py:3` — type hiện tại:**
```python
_registry: dict[str, asyncio.Queue[str | None]] = {}
```
→ Đổi thành `dict[str, asyncio.Queue[dict | None]]`.

**`router.py:165-171` — `event_generator` hiện tại:**
```python
async def event_generator():
    while True:
        item = await queue.get()
        if item is None:
            yield f"data: {json.dumps({'event': 'done'})}\n\n"
            break
        yield f"data: {json.dumps({'chunk': item})}\n\n"
```
→ Thêm handling cho typed frames.

**`ChatbotPanel.tsx:201-214` — `es.onmessage` hiện tại:**
```typescript
es.onmessage = (e) => {
    ...
    if (data.event === 'done') {
        commitStreamingMessage();  // không tham số
        closeStream();
    } else if (typeof data.chunk === 'string') {
        appendChunk(data.chunk);
    }
};
```
→ Thêm `citation_map` event + truyền `data.content` và map vào `commitStreamingMessage`.

### pgvector Cosine Distance: Chi Tiết Kỹ Thuật

**HNSW index đã tồn tại** (migration 006):
```sql
CREATE INDEX idx_child_chunks_embedding_hnsw
ON child_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64)
```

**SQLAlchemy + pgvector query pattern được dùng:**
```python
from sqlalchemy import select, literal
from pgvector.sqlalchemy import Vector

query_vec = literal(query_embedding, Vector(768))
stmt = (
    select(ChildChunkORM.id, ChildChunkORM.content)
    .where(ChildChunkORM.project_id == project_id)
    .where(ChildChunkORM.embedding.is_not(None))
    .order_by(ChildChunkORM.embedding.op("<=>")(query_vec))
    .limit(TOP_K)
)
```
`Vector(768)` import từ `pgvector.sqlalchemy`. Operator `<=>` là cosine distance của pgvector. `literal(list_float, Vector(768))` cast Python list sang vector literal cho SQLAlchemy.

**Pitfall**: Đừng dùng `text("embedding <=> '...'::vector")` với f-string — SQL injection risk. Luôn dùng SQLAlchemy bound parameter qua `literal()`.

### LangGraph `astream_events` v2 — Event Filtering

Khi dùng `graph.astream_events(..., version="v2")`:
- `on_chat_model_stream`: emit cho mỗi token từ LLM. `event["data"]["chunk"]` là `AIMessageChunk`. Token nằm ở `chunk.content`.
- `on_llm_stream`: tương tự nhưng low-level hơn — ưu tiên dùng `on_chat_model_stream`.
- `on_chain_end` với `name="LangGraph"`: event cho biết toàn bộ graph đã kết thúc.

**Lấy state cuối qua `aget_state`** (tin cậy hơn parsing `on_chain_end`):
```python
final_snapshot = await graph.aget_state(config)
final_state = final_snapshot.values  # dict với keys: messages, valid_citation_ids, citation_map
```
`aget_state` đọc từ PostgresSaver checkpoint — state này ĐÃ qua `citation_guardrail_node`, nên `messages[-1]` là bản sạch.

### SSE Protocol: Trước vs Sau

**Trước (Story 3.2):**
```
data: {"chunk": "t"}           # từng ký tự, 50ms/char
data: {"chunk": "o"}
...
data: {"event": "done"}
```

**Sau (Story 3.6):**
```
data: {"chunk": "Nghiên"}      # token thật từ LLM, không đều
data: {"chunk": " cứu"}
data: {"chunk": " cho thấy"}
data: {"chunk": " [1]"}
...
data: {"event": "citation_map", "data": {"1": "uuid-abc", "2": "uuid-xyz"}}
data: {"event": "done", "content": "Nghiên cứu cho thấy [1] và [2]..."}
```

`done.content` là bản đã qua guardrail (nếu LLM viết `[7]` ảo sẽ bị thay bằng `[Nguồn không xác định]` trước khi save DB và emit done).

### Luồng Streaming Token và Guardrail

**Quan trọng**: Người dùng thấy streaming bản CHƯA guardrail (các token đến theo thứ tự từ LLM). Sau khi stream xong, `commitStreamingMessage(final_content)` thay `streamingContent` bằng `final_content` đã sạch (từ `done.content`). Sự chênh lệch này chỉ xảy ra khi LLM viết citation ảo — rất hiếm nếu system prompt chặt chẽ. Hành vi này NHẤT QUÁN với ghi chú Story 3.5: "streaming KHÔNG parse citation, chỉ committed message mới parse".

### Vòng Đời `citationMapRef`

```
beginStreaming()
  → citationMapRef.current = {}  (implicit — không reset vì project reset đã handle)
SSE stream chunks...
SSE citation_map event → citationMapRef.current = {"1": "uuid", "2": "uuid"}
SSE done event → commitStreamingMessage(content, citationMapRef.current)
                  → citationMapRef.current = {}  (reset sau commit)
```

Reset thêm khi: đổi project (`useEffect [activeProjectId]`). Vì mỗi lần gửi message là một stream riêng biệt, ref sẽ được overwrite đúng cách.

### Vấn Đề Ordinal vs UUID (Lý Do Citation Cũ Graceful Fail)

Tin nhắn load từ API history (`GET /chat/threads/{id}/messages`) trả `ChatMessage[]` từ DB — không có `citationMap` field. Khi `msg.citationMap` là `undefined`, `MessageContent` dùng `citationMap?.[ordinal] ?? ordinal` → fallback về ordinal string (e.g. `"1"`). `CitationBadge` gọi `GET /api/citations/1` → backend nhận UUID `"1"` (không phải UUID format) → 422 → tooltip "Không tìm thấy..." ✅ Graceful, không crash — nhất quán với thiết kế Story 3.5.

### Không Thay Đổi (Để Tránh Regression)

- `citation_guardrail_node` — logic regex + `valid_citation_ids` check giữ nguyên
- `CitationBadge.tsx` — không thay đổi component, chỉ nhận UUID thay ordinal
- `getCitationDetail` trong `citations.ts` — không thay đổi
- `citation_router.py` — endpoint `GET /api/citations/{chunk_id: UUID}` không đổi
- `GetCitationDetailUseCase` — không đổi (owner scoping theo `user_id`, không `project_id`)
- SSE ticket auth (ARCH-3) — không áp dụng ở đây vì đây là EventSource với cookie HttpOnly (SameSite=Lax)
- Tất cả API khác của chat (threads, suggestions, invoke)

### Module & File Map

**Backend — Files CẦN UPDATE:**
- `backend/src/modules/orchestrator/application/graph.py` (ChatState + real_rag_node + build_graph)
- `backend/src/modules/orchestrator/application/use_cases.py` (_stream_graph_to_queue + SendMessageUseCase)
- `backend/src/modules/orchestrator/infrastructure/run_registry.py` (queue type)
- `backend/src/modules/orchestrator/presentation/router.py` (event_generator)

**Frontend — Files CẦN UPDATE:**
- `frontend/src/types/chat.ts` (ChatMessage + citationMap field)
- `frontend/src/store/chatStore.ts` (commitStreamingMessage signature)
- `frontend/src/features/workspace/ChatbotPanel.tsx` (citationMapRef + SSE handler + render)
- `frontend/src/components/MessageContent.tsx` (citationMap prop + UUID resolution)

**Tests — Files CẦN TẠO/UPDATE:**
- `tests/unit/orchestrator/test_real_rag_node.py` (NEW)
- `tests/unit/orchestrator/test_citation_guardrail.py` (tái dùng, không cần đổi)

**Không tạo file mới** ngoài danh sách trên.

### Dependencies: Đã Có Sẵn, Không Cần Thêm

- `pgvector` — đã có (migration 006, chunk_orm_models.py)
- `langchain-google-genai` — đã có (GeminiEmbeddingClient, LLMRouter)
- `langchain-core`, `langgraph` — đã có (orchestrator)
- `sqlalchemy` — đã có
- Không cần `npm install` package mới cho frontend

### Thứ Tự Implement Đề Xuất

1. **Backend graph.py** (Task 1) — independent, có thể kiểm tra bằng unit test
2. **Backend run_registry.py** (Task 2) — type change đơn giản
3. **Backend use_cases.py** (Task 3) — sau khi graph.py và run_registry xong
4. **Backend router.py** (Task 4) — sau run_registry xong
5. **Frontend types/chat.ts** (Task 5) — independent
6. **Frontend chatStore.ts** (Task 6) — sau types/chat.ts
7. **Frontend MessageContent.tsx** (Task 8) — independent (prop change)
8. **Frontend ChatbotPanel.tsx** (Task 7) — sau Task 5+6+8
9. **Tests** (Task 9) — cuối cùng

### References

- [Source: sprint-change-proposal-2026-06-17.md — Section 2] — Technical Impact analysis đầy đủ
- [Source: sprint-change-proposal-2026-06-17.md — Section 4.1] — AC nháp và quyết định thiết kế
- [Source: epics.md Story 3.6] — Story statement và FR coverage
- [Source: backend/src/modules/orchestrator/application/graph.py] — ChatState hiện tại, mock_rag_node, citation_guardrail_node, build_graph
- [Source: backend/src/modules/orchestrator/application/use_cases.py] — _stream_graph_to_queue, SendMessageUseCase
- [Source: backend/src/modules/orchestrator/infrastructure/run_registry.py] — Queue type hiện tại
- [Source: backend/src/modules/orchestrator/presentation/router.py:165] — event_generator hiện tại
- [Source: backend/src/modules/ingestion/infrastructure/embedding_client.py] — GeminiEmbeddingClient (tái dùng)
- [Source: backend/src/shared/infra/llm/router.py] — LLMRouter.get_llm_client (tái dùng)
- [Source: backend/src/modules/ingestion/infrastructure/chunk_orm_models.py] — ChildChunkORM schema
- [Source: backend/alembic/versions/006_create_chunks_tables.py] — HNSW index (vector_cosine_ops, m=16, ef_construction=64)
- [Source: backend/src/modules/orchestrator/domain/entities.py] — ChatThread.project_id (đã có)
- [Source: frontend/src/types/chat.ts] — ChatMessage interface
- [Source: frontend/src/store/chatStore.ts] — commitStreamingMessage, ChatMessage creation
- [Source: frontend/src/features/workspace/ChatbotPanel.tsx:201-214] — es.onmessage handler
- [Source: frontend/src/components/MessageContent.tsx] — parser + CitationBadge render
- [Source: frontend/src/components/CitationBadge.tsx] — tooltip logic (không đổi)
- [Source: architecture.md Section 5.1] — vector_search cosine similarity API spec
- [Source: architecture.md Section 6.3] — Parent-Child chunking strategy
- [Source: architecture.md Section 6.4] — Citation Guardrail Node hoạt động

---

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

(none)

### Completion Notes List

- ✅ Triển khai `real_rag_node` thay thế `mock_rag_node` với embed câu hỏi qua GeminiEmbeddingClient và cosine similarity search trên pgvector HNSW index.
- ✅ Thêm `citation_map: dict[int, str]` vào ChatState để truyền ordinal→UUID mapping từ backend sang frontend.
- ✅ Refactor `_stream_graph_to_queue` sang `astream_events` (token streaming thật, không còn vòng lặp 50ms).
- ✅ Cập nhật SSE protocol thêm frame `citation_map` và `done.content` (câu trả lời sau guardrail).
- ✅ Frontend: `citationMapRef`, SSE handler nhận `citation_map` event, `commitStreamingMessage` nhận cleaned content + map.
- ✅ `MessageContent` resolve ordinal → UUID trước khi truyền vào `CitationBadge` (tin nhắn lịch sử graceful fallback).
- ✅ InvokeUseCase cũng được cập nhật truyền `user_id` + `project_id` vào config để tránh KeyError với real_rag_node.
- ✅ 27/27 backend unit tests pass; 11/11 frontend component tests pass (MessageContent + CitationBadge); TypeScript check sạch.

### File List

- backend/src/modules/orchestrator/application/graph.py (modified)
- backend/src/modules/orchestrator/application/use_cases.py (modified)
- backend/src/modules/orchestrator/infrastructure/run_registry.py (modified)
- backend/src/modules/orchestrator/presentation/router.py (modified)
- frontend/src/types/chat.ts (modified)
- frontend/src/store/chatStore.ts (modified)
- frontend/src/features/workspace/ChatbotPanel.tsx (modified)
- frontend/src/components/MessageContent.tsx (modified)
- tests/unit/orchestrator/test_real_rag_node.py (created)
- tests/unit/orchestrator/test_citation_guardrail.py (modified — edge check mock_rag → real_rag)

### Change Log

- 2026-06-17: Tạo story 3.6 — Real RAG Retriever, pgvector Similarity & Citation Map qua SSE. Phân tích đầy đủ từ sprint-change-proposal-2026-06-17.md + toàn bộ code hiện tại. (create-story agent: claude-sonnet-4-6)
- 2026-06-17: Triển khai story 3.6 hoàn chỉnh — real_rag_node, astream_events, SSE citation_map frame, frontend citationMap plumbing. 27/27 backend tests + 11 frontend component tests pass. (dev agent: claude-sonnet-4-6)
- 2026-06-17: Code review (bmad-code-review, 3 lớp: Blind Hunter / Edge Case Hunter / Acceptance Auditor). 3 patch đã áp dụng, 4 defer, phần còn lại dismiss. 29/29 backend tests + 13 frontend tests pass. (review agent: claude-opus-4-8)

---

## Review Findings (2026-06-17)

### Patch — đã áp dụng (fixed)

- [x] **[Review][Patch] Đường lỗi im lặng nuốt mất câu trả lời** [backend/.../application/use_cases.py:263] — Khi node raise exception trước khi emit `done` (lỗi embedding/LLM/DB), `finally` chỉ put `None` → router phát `done` không `content` → frontend `commitStreamingMessage('')` drop message → người dùng mất tăm, không thấy lỗi. **Fix:** `except` giờ emit `done` với content xin lỗi để người dùng luôn thấy phản hồi.
- [x] **[Review][Patch] Query rỗng/khoảng trắng → retrieve chunk vô nghĩa** [backend/.../application/graph.py:67] — Query rỗng → `GeminiEmbeddingClient` trả zero-vector → cosine `<=>` ra NaN → pgvector xếp hạng tùy ý, trả TOP_K chunk không liên quan rồi trích dẫn. **Fix:** guard `if not query.strip()` trả `EMPTY_RETRIEVAL_MSG` trước khi embed. Có test mới `test_real_rag_node_blank_query_no_embed`.
- [x] **[Review][Patch] `citationMapRef` cũ dính sang câu trả lời mới** [frontend/.../ChatbotPanel.tsx:186] — Ref chỉ reset ở `done`/đổi project. Hai tin nhắn liên tiếp (tin sau không có citation) có thể dính map của tin trước → `[1]` resolve sai nguồn. **Fix:** reset `citationMapRef.current = {}` ngay đầu `handleSend`.

### Defer — thật nhưng pre-existing / kiến trúc / cố ý (không sửa trong story này)

- [x] **[Review][Defer] Race nhiều message cùng thread_id** [backend/.../application/use_cases.py:243] — `aget_state(config)` chỉ key theo `thread_id`; hai run đồng thời cùng thread có thể đọc state lẫn nhau → commit `final_content`/`citation_map` sai. Pre-existing (mô hình checkpoint theo thread_id có từ trước 3.6; đường `ainvoke` cũ cũng vướng). Cần khóa per-thread hoặc chặn gửi khi đang stream.
- [x] **[Review][Defer] Owner scoping: retrieval theo project_id vs citation-detail theo user_id** [backend/.../application/graph.py:79 vs use_cases.py:273] — Hai key scope khác nhau; cả hai đều chặn IDOR cross-user nhưng không nhất quán như AC#9 mô tả. Đã ghi nhận cố ý trong Dev Notes.
- [x] **[Review][Defer] Lỗi embedding tạm thời degrade thành zero-vector → chunk tùy ý** [backend/.../ingestion/infrastructure/embedding_client.py:44] — Graceful degradation (dùng chung với ingestion worker) khiến lỗi API tạm thời không phân biệt được với retrieve thành công. Patch query-rỗng chỉ chặn 1 nhánh; gốc nằm ở embedding_client (ngoài phạm vi 3.6).
- [x] **[Review][Defer] Content dạng list (multimodal) → lưu message rỗng, mất lượt** [backend/.../application/use_cases.py:251] — `final_content=""` khi content không phải str → DB lưu rỗng + frontend drop. Rất hiếm với Gemini text; guardrail đã skip multimodal.

### Note quy trình (không phải lỗi code 3.6)

- Story 3.4 & 3.5 đánh dấu `done` trong sprint-status nhưng **code chưa commit** — toàn bộ (citation_guardrail, citation_router, CitationBadge, MessageContent) nằm chung trong working tree với 3.6. Vì vậy claim của spec "guardrail không thay đổi / test_citation_guardrail.py đã có sẵn" đúng so với 3.4 nhưng diff-vs-HEAD (fbf805e) hiển thị là file mới. Khuyến nghị commit 3.4/3.5 trước, rồi 3.6, để lịch sử git phản ánh đúng ranh giới story.

### Dismiss (noise / by-design / false positive)

- Flicker token thô (pre-guardrail) → bản sạch khi commit: by-design theo Story 3.5 (streaming không parse citation), chỉ xảy ra khi LLM bịa citation — hiếm.
- `citation_map` int key → JSON string key: hoạt động đúng theo thiết kế, TS type `Record<string,string>` khớp wire.
- Badge lịch sử gọi `/api/citations/<ordinal>` → 422: đây chính là hành vi graceful AC#8 mong muốn.
- SSE frame collision, `Queue[dict]` producer consistency, `add_messages` overwrite-by-id: đã verify an toàn.
