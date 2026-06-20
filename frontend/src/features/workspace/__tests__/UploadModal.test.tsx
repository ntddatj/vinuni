import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import { UploadModal } from '../UploadModal';
import * as ingestionApi from '@/api/ingestion';

vi.mock('@/api/ingestion');

const MOCK_UPLOAD_RESPONSE = {
  fileId: 'file-uuid-123',
  title: 'Deep Learning for NLP',
  authors: ['John Doe', 'Jane Smith'],
  abstract: 'This paper presents a comprehensive study...',
  year: 2023,
  doi: null,
};

const MOCK_CONFIRM_RESPONSE = {
  documentId: 'paper-uuid-456',
  message: 'Tài liệu đã được thêm vào hàng đợi xử lý',
};

function makeFile(name: string, sizeBytes: number) {
  const content = new Array(sizeBytes).fill('a').join('');
  return new File([content], name, { type: 'application/pdf' });
}

function renderModal(
  projectId = 'proj-123',
  onClose = vi.fn(),
  onSuccess = vi.fn(),
) {
  return render(
    <MemoryRouter>
      <Toaster />
      <UploadModal projectId={projectId} onClose={onClose} onSuccess={onSuccess} />
    </MemoryRouter>
  );
}

describe('UploadModal', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('hiển thị nút "Upload Tài liệu" ở phase idle', () => {
    renderModal();
    expect(screen.getByText(/upload tài liệu/i)).toBeInTheDocument();
    expect(screen.getByText(/xác nhận thông tin tài liệu/i)).toBeInTheDocument();
  });

  it('hiển thị spinner + text "extracting" khi đang gọi API upload', async () => {
    let resolveUpload: (value: typeof MOCK_UPLOAD_RESPONSE) => void;
    vi.mocked(ingestionApi.uploadDocument).mockReturnValue(
      new Promise((resolve) => { resolveUpload = resolve; })
    );

    renderModal();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdfFile = makeFile('paper.pdf', 100);
    Object.defineProperty(fileInput, 'files', { value: [pdfFile] });
    fireEvent.change(fileInput);

    await waitFor(() =>
      expect(screen.getByText(/đang trích xuất metadata/i)).toBeInTheDocument()
    );

    resolveUpload!(MOCK_UPLOAD_RESPONSE);
  });

  it('hiển thị form với badge "AI Suggested" sau khi upload thành công', async () => {
    vi.mocked(ingestionApi.uploadDocument).mockResolvedValue(MOCK_UPLOAD_RESPONSE);

    renderModal();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdfFile = makeFile('paper.pdf', 100);
    Object.defineProperty(fileInput, 'files', { value: [pdfFile] });
    fireEvent.change(fileInput);

    await waitFor(() =>
      expect(screen.getByDisplayValue('Deep Learning for NLP')).toBeInTheDocument()
    );

    const badges = screen.getAllByText('AI Suggested');
    expect(badges.length).toBeGreaterThanOrEqual(4);
  });

  it('gọi confirmMetadata khi click "Xác nhận"', async () => {
    vi.mocked(ingestionApi.uploadDocument).mockResolvedValue(MOCK_UPLOAD_RESPONSE);
    vi.mocked(ingestionApi.confirmMetadata).mockResolvedValue(MOCK_CONFIRM_RESPONSE);

    const onSuccess = vi.fn();
    const onClose = vi.fn();
    renderModal('proj-123', onClose, onSuccess);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdfFile = makeFile('paper.pdf', 100);
    Object.defineProperty(fileInput, 'files', { value: [pdfFile] });
    fireEvent.change(fileInput);

    await waitFor(() =>
      expect(screen.getByDisplayValue('Deep Learning for NLP')).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole('button', { name: /xác nhận/i }));

    await waitFor(() =>
      expect(vi.mocked(ingestionApi.confirmMetadata)).toHaveBeenCalledWith(
        expect.objectContaining({
          fileId: 'file-uuid-123',
          projectId: 'proj-123',
        })
      )
    );
    expect(onSuccess).toHaveBeenCalledWith('paper-uuid-456');
    expect(onClose).toHaveBeenCalled();
  });

  it('hiển thị Toast lỗi khi file quá 20MB', async () => {
    renderModal();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const largeFile = makeFile('large.pdf', 21 * 1024 * 1024);
    Object.defineProperty(fileInput, 'files', { value: [largeFile] });
    fireEvent.change(fileInput);

    await waitFor(() =>
      expect(screen.getByText(/vượt quá giới hạn 20MB/i)).toBeInTheDocument()
    );

    expect(vi.mocked(ingestionApi.uploadDocument)).not.toHaveBeenCalled();
  });

  it('đóng modal khi click "Hủy"', async () => {
    vi.mocked(ingestionApi.uploadDocument).mockResolvedValue(MOCK_UPLOAD_RESPONSE);
    const onClose = vi.fn();
    renderModal('proj-123', onClose);

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const pdfFile = makeFile('paper.pdf', 100);
    Object.defineProperty(fileInput, 'files', { value: [pdfFile] });
    fireEvent.change(fileInput);

    await waitFor(() =>
      expect(screen.getByDisplayValue('Deep Learning for NLP')).toBeInTheDocument()
    );

    fireEvent.click(screen.getByRole('button', { name: /hủy/i }));

    expect(onClose).toHaveBeenCalled();
  });
});
