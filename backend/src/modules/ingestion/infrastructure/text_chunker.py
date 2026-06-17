"""Chia text tài liệu thành parent/child chunks cho parent-child retrieval.

Parent: gộp theo paragraph (\\n\\n) đến tối đa PARENT_MAX_CHARS.
Child: sliding window CHILD_CHUNK_SIZE chars, overlap CHILD_OVERLAP chars từ mỗi parent.
"""

PARENT_MAX_CHARS = 3000
CHILD_CHUNK_SIZE = 500
CHILD_OVERLAP = 100


def chunk_text(text: str) -> list[tuple[str, list[str]]]:
    """Chia text thành list các (parent_content, [child_content, ...])."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        stripped = text.strip()
        if not stripped:
            return []
        paragraphs = [stripped]

    # Gộp paragraphs thành parent chunks
    parents: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= PARENT_MAX_CHARS:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                parents.append(current)
                current = ""
            # Paragraph quá dài? Cắt trực tiếp theo block PARENT_MAX_CHARS
            if len(para) > PARENT_MAX_CHARS:
                for i in range(0, len(para), PARENT_MAX_CHARS):
                    parents.append(para[i : i + PARENT_MAX_CHARS])
            else:
                current = para
    if current:
        parents.append(current)

    result: list[tuple[str, list[str]]] = []
    for parent_content in parents:
        children = _sliding_window(parent_content)
        result.append((parent_content, children))
    return result


def _sliding_window(text: str) -> list[str]:
    """Sliding window CHILD_CHUNK_SIZE chars với overlap CHILD_OVERLAP chars."""
    if len(text) <= CHILD_CHUNK_SIZE:
        return [text]
    chunks: list[str] = []
    start = 0
    step = CHILD_CHUNK_SIZE - CHILD_OVERLAP
    while start < len(text):
        end = start + CHILD_CHUNK_SIZE
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks
