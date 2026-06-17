"""Unit tests cho SendMessageUseCase và InvokeUseCase."""
from unittest.mock import AsyncMock, patch

import pytest

from backend.src.modules.orchestrator.application.dtos import InvokeDTO, SendMessageDTO
from backend.src.modules.orchestrator.application.use_cases import InvokeUseCase, SendMessageUseCase
from backend.src.modules.orchestrator.domain.exceptions import ThreadAccessDeniedError, ThreadNotFoundError
from tests.unit.orchestrator.test_chat_threads import _make_thread


@pytest.mark.asyncio
async def test_send_message_raises_not_found_when_thread_missing():
    repo = AsyncMock()
    repo.find_by_id.return_value = None
    uc = SendMessageUseCase(repo)
    with pytest.raises(ThreadNotFoundError):
        await uc.execute(SendMessageDTO(thread_id="ghost", message="hi", user_id="u1"))


@pytest.mark.asyncio
async def test_send_message_raises_access_denied_when_wrong_user():
    repo = AsyncMock()
    repo.find_by_id.return_value = _make_thread(user_id="owner")
    uc = SendMessageUseCase(repo)
    with pytest.raises(ThreadAccessDeniedError):
        await uc.execute(SendMessageDTO(thread_id="t1", message="hi", user_id="other"))


@pytest.mark.asyncio
async def test_send_message_saves_user_message_and_returns_run_id():
    repo = AsyncMock()
    repo.find_by_id.return_value = _make_thread(user_id="u1")
    repo.save_message.return_value = AsyncMock()
    with patch("backend.src.modules.orchestrator.application.use_cases.get_postgres_checkpointer") as mock_cp, \
         patch("asyncio.create_task"):
        mock_cp.return_value = AsyncMock()
        uc = SendMessageUseCase(repo)
        run_id = await uc.execute(SendMessageDTO(thread_id="t1", message="hi", user_id="u1"))
    repo.save_message.assert_called_once_with("t1", "user", "hi")
    assert run_id.startswith("run_")


@pytest.mark.asyncio
async def test_invoke_raises_not_found_when_thread_missing():
    repo = AsyncMock()
    repo.find_by_id.return_value = None
    uc = InvokeUseCase(repo)
    with pytest.raises(ThreadNotFoundError):
        await uc.execute(InvokeDTO(thread_id="ghost", message="hi", user_id="u1"))


@pytest.mark.asyncio
async def test_invoke_raises_access_denied_when_wrong_user():
    repo = AsyncMock()
    repo.find_by_id.return_value = _make_thread(user_id="owner")
    uc = InvokeUseCase(repo)
    with pytest.raises(ThreadAccessDeniedError):
        await uc.execute(InvokeDTO(thread_id="t1", message="hi", user_id="other"))


@pytest.mark.asyncio
async def test_invoke_returns_answer_from_graph():
    repo = AsyncMock()
    repo.find_by_id.return_value = _make_thread(user_id="u1")

    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {
        "messages": [AsyncMock(content="Mock RAG answer")]
    }

    with patch("backend.src.modules.orchestrator.application.use_cases.get_postgres_checkpointer") as mock_cp, \
         patch("backend.src.modules.orchestrator.application.use_cases.build_graph", return_value=mock_graph):
        mock_cp.return_value = AsyncMock()
        uc = InvokeUseCase(repo)
        answer = await uc.execute(InvokeDTO(thread_id="t1", message="test", user_id="u1"))
    assert answer == "Mock RAG answer"
