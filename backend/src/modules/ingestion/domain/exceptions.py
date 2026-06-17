class FileTooLargeError(Exception):
    def __init__(self, max_mb: int) -> None:
        super().__init__(f"File vượt quá giới hạn {max_mb}MB")
        self.max_mb = max_mb


class UnsupportedFileTypeError(Exception):
    def __init__(self, mime_type: str) -> None:
        super().__init__(f"Định dạng file không được hỗ trợ: {mime_type}. Chỉ chấp nhận PDF và DOCX.")
        self.mime_type = mime_type


class IngestionFileNotFoundError(Exception):
    def __init__(self, file_id: str) -> None:
        super().__init__(f"Không tìm thấy file đã upload: {file_id}")
        self.file_id = file_id


class ProjectAccessDeniedError(Exception):
    def __init__(self, project_id: str) -> None:
        super().__init__(f"Không có quyền truy cập dự án: {project_id}")
        self.project_id = project_id


class FileStorageError(Exception):
    """Lỗi khi ghi file lên đĩa (thiếu quyền, hết dung lượng, ...)."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"Không thể lưu file lên server: {detail}")
        self.detail = detail


class ProjectPaperLimitExceededError(Exception):
    def __init__(self, project_id: str, limit: int) -> None:
        super().__init__("Dự án đã đạt giới hạn tài liệu")
        self.project_id = project_id
        self.limit = limit
