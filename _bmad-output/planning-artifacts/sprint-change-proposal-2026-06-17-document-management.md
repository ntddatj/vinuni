# Sprint Change Proposal — Quản lý Tài liệu (CRUD) & Cache PDF Nguồn

- **Ngày:** 2026-06-17
- **Người đề xuất:** Dat
- **Workflow:** correct-course (BMad)
- **Mode review:** Batch
- **Phân loại phạm vi:** **Moderate** (mở lại `epic-2` → in-progress; thêm 2 story; 1 FR mới + làm rõ 2 FR sẵn có).

> **🔧 Addendum (chốt sau duyệt — 2026-06-17):**
> 1. **Gộp Story 2.7 + 2.8 → một Story 2.7** ("Quản lý Tài liệu trong Dự án — Xóa, Sửa Metadata & Cache/Xem PDF Nguồn") do đồng độ gắn kết cao (cùng `PaperORM`, cùng tab Thư viện, cùng module). Tổng story 28→**27**. Các tham chiếu "Story 2.8" bên dưới nay là phần (3) của Story 2.7.
> 2. **Giữ NFR2 = 20MB** (KHÔNG nâng 50MB lúc này).
> 3. **Thêm key `MAX_UPLOAD_SIZE_MB`** vào scope **Story 5.3** (Admin Settings động — FR12) thay vì hardcode; mặc định 20MB, Admin nâng tay sau.

---

## Section 1 — Issue Summary

Trong lúc rà soát Epic 2 (đã "done"), phát hiện **2 khoảng trống** liên quan vòng đời tài liệu:

1. **Thiếu Update/Delete tài liệu trong dự án.** Endpoint ingestion hiện chỉ có Create + Read ([router.py](backend/src/modules/ingestion/presentation/router.py): `upload`, `confirm`, `from-search`, `ticket`, `sse/stream`, `GET papers`). Không có `DELETE` (xóa 1 tài liệu) và không có `PATCH` (sửa metadata sau khi đã ingest — Form "AI Suggested" ở Story 2.4 chỉ sửa được **trước** confirm). → **Loại issue: New requirement** (FR-2 chỉ là CRUD *dự án*, chưa FR nào nói CRUD *tài liệu*).

2. **PDF nguồn không được lưu lại → mỗi lần xem phải gọi lại arXiv/Scholar.** Worker ingestion **đã tải** PDF từ `pdf_url` (`_download_pdf_text`, có SSRF guard) nhưng chỉ để **trích text rồi bỏ** — không persist `file_path`. Không có endpoint phục vụ xem lại file gốc. → **Loại issue: Incomplete implementation** của FR-4 ("tải PDF ngầm Open Access") + FR-10 ("nút mở/tải tệp gốc"). **Không phải FR mới.**

### Bằng chứng
- [orm_models.py:40](backend/src/modules/ingestion/infrastructure/orm_models.py#L40): `PaperORM.file_path` (nullable) + `is_deleted` đã tồn tại — hạ tầng sẵn, chỉ thiếu lớp dùng.
- [postgres_repository.py:105](backend/src/modules/ingestion/infrastructure/postgres_repository.py#L105) `save_from_search` chỉ lưu `pdf_url` (chuỗi), không lưu file nhị phân.
- Story 2.5 [worker download](backend/worker.py): tải PDF → `_download_pdf_text` trả **text**, không set `file_path`.
- [prd.md:145](_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md): FR-10 đã yêu cầu "nút tải xuống/mở tệp gốc"; [prd.md:180](_bmad-output/planning-artifacts/prds/prd-C2-App-053-2026-06-11/prd.md) Non-Goals: paywalled → upload thủ công, không Sci-Hub.

---

## Section 2 — Impact Analysis (checklist findings)

### Epic Impact (§2)
- **Epic 2** (sprint-status: `in-progress`; epics.md ghi "done"): thêm **Story 2.7** (quản lý tài liệu) + **Story 2.8** (cache PDF). Giữ `epic-2 = in-progress` tới khi xong.
- Epic 3/4/5: không ảnh hưởng trực tiếp. _Lưu ý dây chuyền tích cực:_ Story 2.8 persist `file_path` giúp **Story 3.4/3.6** (tooltip citation) có nút "mở tệp gốc" thật.

### Artifact Conflicts (§3)
| Artifact | Cần đổi |
|---|---|
| **PRD** | **Thêm FR-16** (Quản lý vòng đời Tài liệu: Delete + Edit metadata) vào §4.2. **Làm rõ FR-4** (persist PDF Open Access vào secure storage) + ghi chú FR-10 do Story 2.8 hiện thực. |
| **Epics** | Thêm Story 2.7, 2.8; cập nhật FR Coverage Map (FR-16 → Epic 2); cập nhật dòng trạng thái (26→28 story). |
| **Architecture** | Không cần req mới — **tái dùng pattern ARCH-9** (Secure Media Access `FileResponse`). Endpoint mới: `GET /api/projects/{project_id}/papers/{paper_id}/file`. |
| **sprint-status.yaml** | Thêm `2-7-...`, `2-8-...` = backlog. |

### Technical Impact (§3.2)
**Story 2.7 (Document CRUD):**
- `DELETE /api/projects/{project_id}/papers/{paper_id}`: set `is_deleted=true`, ghi `sync_outbox` (ARCH-2 GC cứng sau 7 ngày), cascade `parent_chunks`/`child_chunks` (FK `ondelete=CASCADE` đã có), **giảm bộ đếm `MAX_PAPERS_PER_PROJECT`** (Story 2.6 — chú ý Redis lock/counter), owner scoping chống IDOR.
- `PATCH /api/projects/{project_id}/papers/{paper_id}`: cập nhật `{title, authors, abstract, year}`. **Không re-chunk/re-embed** (chỉ metadata). Validate độ dài (đồng bộ deferred item 2.5 về giới hạn title/abstract).
- UI tab "Thư viện tài liệu": nút xóa (popup xác nhận) + form sửa metadata.

**Story 2.8 (Cache PDF + serve):**
- Worker: sau khi tải PDF Open Access, **persist** qua `file_storage` (đã có) → set `paper.file_path` thay vì bỏ. Enforce **NFR2 (20MB)** khi lưu.
- Endpoint bảo mật `GET .../papers/{paper_id}/file` → `FileResponse` sau khi check JWT + quyền workspace (mirror ARCH-9). Content-Disposition cho tải / inline cho xem.
- Paywalled / tải fail → `file_path` NULL → UI ẩn nút "Xem file nguồn", hiện link ngoài + nhãn **"nguồn cần trả phí"**.
- SSRF/scheme guard đã patch ở 2.5 — giữ nguyên khi persist.

### UI/UX (§3.3)
- Tab Thư viện: thêm hành động xóa/sửa per-row + nút "Xem file nguồn"/nhãn "nguồn cần trả phí". Nhất quán FR-10/UX-DR6 (nút mở tệp gốc trong tooltip citation).

### Artifacts khác (§3.4)
- Storage: thư mục bảo mật cho PDF (vd `/app/data/papers/`) — cùng họ `/app/data/images/` của ARCH-9. Lưu ý tăng trưởng đĩa (counter-metric SM-C1 không bị ảnh hưởng).

---

## Section 3 — Recommended Approach (§4)

**Hybrid → nghiêng Direct Adjustment:** thêm 2 story vào Epic 2.
- **Story 2.7** = Option 1 thuần (new stories trong epic hiện có). FR mới FR-16.
- **Story 2.8** = hoàn thiện FR-4/FR-10 đã cam kết (không phải tăng scope MVP — đúng ra là **trả nợ** scope đã hứa).

**Vì sao không rollback / không review MVP:** Không có gì để revert (chỉ bổ sung). MVP không bị thu hẹp; ngược lại Story 2.8 giúp MVP đạt đúng cam kết FR-4/FR-10.

- **Effort:** 2.7 = Medium (CRUD + counter rollback + cascade). 2.8 = Medium (persist + secure serve, phần lớn hạ tầng đã có).
- **Risk:** Thấp–trung. Rủi ro chính: (a) đồng bộ bộ đếm MAX_PAPERS khi xóa (đua Redis); (b) dung lượng đĩa khi cache nhiều PDF; (c) inline-view PDF cần `Content-Type`/`X-Content-Type-Options` đúng.

---

## Section 4 — Detailed Change Proposals

### 4.1 — PRD: thêm FR-16 (chèn vào §4.2, sau FR-5)

```
- **FR-16: Quản lý vòng đời Tài liệu trong Dự án (Document Lifecycle Management)**
  - Người dùng có thể Xóa một tài liệu khỏi dự án và Chỉnh sửa siêu dữ liệu
    (Tiêu đề, Tác giả, Năm, Tóm tắt) của một tài liệu ĐÃ được nạp.
  - *Consequences*:
    - Xóa tài liệu dùng cơ chế xóa mềm (`is_deleted`), ghi sự kiện vào `sync_outbox`
      để đồng bộ gỡ node khỏi Neo4j (theo ARCH-2 GC), cascade xóa các chunk vector,
      và GIẢI PHÓNG 1 suất trong giới hạn `MAX_PAPERS_PER_PROJECT` (FR-11).
    - Chỉnh sửa metadata chỉ cập nhật thông tin hiển thị/đồ thị, KHÔNG nhúng lại vector.
    - Mọi thao tác kiểm tra quyền sở hữu dự án (owner scoping) chống truy cập trái phép.
```

### 4.2 — PRD: làm rõ FR-4 (thêm 1 gạch đầu dòng *Consequences*)

```
THÊM vào phần *Consequences* của FR-4:
- Đối với tài liệu Open Access tải tự động, hệ thống LƯU TRỮ tệp PDF đã tải vào kho
  lưu trữ bảo mật phía server (`paper.file_path`) để phục vụ xem/tải lại sau này mà
  KHÔNG cần gọi lại API arXiv/Semantic Scholar. Tệp gốc được phục vụ qua endpoint bảo
  mật (xác thực JWT + quyền dự án, theo pattern Secure Media Access). Link có phí
  (paywalled/không tải được) giữ nguyên liên kết ngoài kèm nhãn "nguồn cần trả phí"
  (nhất quán Non-Goals — không tích hợp Sci-Hub).
```

### 4.3 — Epics: thêm Story 2.7 & 2.8 (sau Story 2.6)

```
### Story 2.7: [BE+FE] Quản lý Vòng đời Tài liệu — Xóa & Sửa Metadata — ⏳ backlog

DELETE tài liệu (soft-delete `is_deleted` + ghi `sync_outbox` cho Neo4j GC + cascade
chunks + giảm bộ đếm MAX_PAPERS_PER_PROJECT) và PATCH sửa metadata {title, authors,
abstract, year} của tài liệu đã ingest (không re-embed). UI tab Thư viện: nút xóa
(popup xác nhận) + form sửa metadata. Owner scoping chống IDOR.

- **Gộp từ kế hoạch cũ:** Story mới phát sinh (correct-course 2026-06-17). Hiện thực FR-16.
- **FRs:** FR-16 (mới), FR-11 (đồng bộ counter).

### Story 2.8: [BE+FE] Cache PDF Nguồn về Server & Xem lại Offline — ⏳ backlog

Persist PDF Open Access đã tải (worker set `paper.file_path` thay vì bỏ sau khi trích
text), endpoint bảo mật `GET /api/projects/{id}/papers/{paper_id}/file` (FileResponse,
mirror ARCH-9) để xem/tải lại không cần gọi lại arXiv/Scholar. Paywalled/tải fail →
giữ link ngoài + nhãn "nguồn cần trả phí". Tôn trọng NFR2 (20MB). UI: nút "Xem file nguồn".

- **Gộp từ kế hoạch cũ:** Hoàn thiện FR-4 (tải PDF Open Access) + FR-10 (mở/tải tệp gốc),
  vốn đã cam kết nhưng Story 2.5 chỉ tải để trích text rồi bỏ.
- **FRs:** FR-4, FR-10. NFR2. (Tái dùng pattern ARCH-9.)
```

### 4.4 — Epics: cập nhật FR Coverage Map + dòng trạng thái

```
THÊM vào FR Coverage Map:
- **FR-16 (Document Lifecycle):** Epic 2 - Academic Search & Paper Ingestion Engine

SỬA dòng trạng thái thực thi:
OLD: ... Epic 2 ✅ done · Epic 3 ⏳ in-progress (3.1–3.5 done, 3.6 backlog) ...
     Tổng: **26 story** ...
NEW: ... Epic 2 ⏳ in-progress (2.1–2.6 done, 2.7/2.8 backlog) · Epic 3 ⏳ in-progress
     (3.1–3.5 done, 3.6 backlog) ...
     Tổng: **28 story** ...
```

### 4.5 — sprint-status.yaml

```
THÊM dưới 2-6-...:
  2-7-quan-ly-vong-doi-tai-lieu-xoa-sua-metadata: backlog
  2-8-cache-pdf-nguon-ve-server-xem-lai-offline: backlog
```

---

## Section 5 — Implementation Handoff

- **Phân loại:** Moderate.
- **Bước kế tiếp:** `bmad-create-story` cho 2.7 rồi 2.8 (sinh AC chi tiết + dev notes + test plan), sau đó `bmad-dev-story`.
- **Người nhận:** Developer agent (Amelia). Cập nhật PRD (FR-16 + làm rõ FR-4) có thể do PM (John) hoặc áp trực tiếp trong correct-course này.
- **Sequencing:** 2.7 và 2.8 độc lập, làm song song được. 2.8 nên chú ý phối hợp với 3.4/3.6 (nút mở tệp gốc trong tooltip).
- **Success criteria:** Xóa tài liệu giải phóng đúng 1 suất MAX_PAPERS + gỡ node Neo4j; sửa metadata phản ánh tức thì; PDF Open Access xem lại được offline không gọi lại API ngoài; paywalled hiện đúng nhãn; NFR2 enforced.
</content>
