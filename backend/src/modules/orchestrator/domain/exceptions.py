class ThreadNotFoundError(Exception):
    def __init__(self, thread_id: str) -> None:
        super().__init__(f"Thread {thread_id} không tồn tại")
        self.thread_id = thread_id


class ThreadAccessDeniedError(Exception):
    def __init__(self, thread_id: str) -> None:
        super().__init__(f"Không có quyền truy cập thread {thread_id}")
        self.thread_id = thread_id
