import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from backend.src.modules.identity.domain.entities import User
from backend.src.modules.identity.infrastructure.auth_dependencies import get_current_user
from backend.src.modules.orchestrator.application.dtos import (
    CreateThreadDTO,
    DeleteThreadDTO,
    GetSuggestionsDTO,
    GetThreadMessagesDTO,
    InvokeDTO,
    ListThreadsDTO,
    RenameThreadDTO,
    SendMessageDTO,
)
from backend.src.modules.orchestrator.application.use_cases import (
    CreateThreadUseCase,
    DeleteThreadUseCase,
    GetSuggestionsUseCase,
    GetThreadMessagesUseCase,
    InvokeUseCase,
    ListThreadsUseCase,
    RenameThreadUseCase,
    SendMessageUseCase,
)
from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
from backend.src.modules.orchestrator.domain.repositories import ChatThreadRepository
from backend.src.modules.orchestrator.infrastructure.dependencies import get_thread_repository
from backend.src.modules.orchestrator.infrastructure.run_registry import get_run_owner, get_run_queue
from backend.src.modules.orchestrator.presentation.schemas import (
    ChatMessageResponse,
    ChatThreadResponse,
    CreateThreadRequest,
    GetSuggestionsRequest,
    InvokeRequest,
    InvokeResponse,
    RenameThreadRequest,
    SendMessageRequest,
    SendMessageResponse,
    SuggestionItemResponse,
)
from backend.src.modules.workspace.domain.exceptions import ProjectAccessDeniedError, ProjectNotFoundError
from backend.src.modules.workspace.domain.repositories import ProjectRepository
from backend.src.modules.workspace.infrastructure.dependencies import get_project_repository

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/threads", response_model=ChatThreadResponse, status_code=201)
async def create_thread(
    request: CreateThreadRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> ChatThreadResponse:
    use_case = CreateThreadUseCase(repo, project_repo)
    try:
        result = await use_case.execute(
            CreateThreadDTO(user_id=current_user.id, project_id=str(request.project_id), title=request.title)
        )
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dự án không tồn tại") from e
    except ProjectAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập") from e
    return ChatThreadResponse.model_validate(result, from_attributes=True)


@router.get("/threads", response_model=list[ChatThreadResponse])
async def list_threads(
    project_id: UUID = Query(..., alias="projectId"),
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
    project_repo: ProjectRepository = Depends(get_project_repository),
) -> list[ChatThreadResponse]:
    use_case = ListThreadsUseCase(repo, project_repo)
    try:
        results = await use_case.execute(ListThreadsDTO(user_id=current_user.id, project_id=str(project_id)))
    except ProjectNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dự án không tồn tại") from e
    except ProjectAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập") from e
    return [ChatThreadResponse.model_validate(t, from_attributes=True) for t in results]


@router.get("/threads/{thread_id}/messages", response_model=list[ChatMessageResponse])
async def get_thread_messages(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
) -> list[ChatMessageResponse]:
    use_case = GetThreadMessagesUseCase(repo)
    try:
        messages = await use_case.execute(
            GetThreadMessagesDTO(thread_id=str(thread_id), requesting_user_id=current_user.id)
        )
    except ThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ThreadAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return [ChatMessageResponse.model_validate(m, from_attributes=True) for m in messages]


@router.patch("/threads/{thread_id}", response_model=ChatThreadResponse)
async def rename_thread(
    thread_id: UUID,
    request: RenameThreadRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
) -> ChatThreadResponse:
    use_case = RenameThreadUseCase(repo)
    try:
        result = await use_case.execute(
            RenameThreadDTO(thread_id=str(thread_id), title=request.title, user_id=current_user.id)
        )
    except ThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ThreadAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return ChatThreadResponse.model_validate(result, from_attributes=True)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
) -> None:
    use_case = DeleteThreadUseCase(repo)
    try:
        await use_case.execute(
            DeleteThreadDTO(thread_id=str(thread_id), user_id=current_user.id)
        )
    except ThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ThreadAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/invoke", response_model=InvokeResponse)
async def invoke_chat(
    request: InvokeRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
) -> InvokeResponse:
    use_case = InvokeUseCase(repo)
    try:
        answer = await use_case.execute(
            InvokeDTO(thread_id=str(request.thread_id), message=request.message, user_id=current_user.id)
        )
    except ThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ThreadAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return InvokeResponse(answer=answer, thread_id=str(request.thread_id))


@router.post("/threads/{thread_id}/messages", response_model=SendMessageResponse, status_code=202)
async def send_message(
    thread_id: UUID,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    repo: ChatThreadRepository = Depends(get_thread_repository),
) -> SendMessageResponse:
    use_case = SendMessageUseCase(repo)
    try:
        run_id = await use_case.execute(
            SendMessageDTO(thread_id=str(thread_id), message=request.message, user_id=current_user.id)
        )
    except ThreadNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ThreadAccessDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    return SendMessageResponse(run_id=run_id)


@router.post("/suggestions", response_model=list[SuggestionItemResponse])
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


@router.get("/stream")
async def stream_chat(
    run_id: str = Query(..., alias="runId"),
    current_user: User = Depends(get_current_user),
):
    queue = get_run_queue(run_id)
    if queue is None:
        raise HTTPException(status_code=404, detail=f"Run {run_id} không tồn tại hoặc đã hoàn thành")
    if get_run_owner(run_id) != current_user.id:
        raise HTTPException(status_code=403, detail="Không có quyền truy cập run này")

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
            elif t == "agent_thinking":
                yield f"data: {json.dumps({'event': 'agent_thinking', 'status': item['status']})}\n\n"
            elif t == "done":
                yield f"data: {json.dumps({'event': 'done', 'content': item.get('content', '')})}\n\n"
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
