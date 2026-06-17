import { render, screen, waitFor, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { IngestionProgress } from '../IngestionProgress';
import * as ingestionApi from '@/api/ingestion';

vi.mock('@/api/ingestion');

// ---- Mock EventSource ----
class MockEventSource {
  static instances: MockEventSource[] = [];
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSED = 2;
  url: string;
  onmessage: ((evt: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  closed = false;
  readyState = MockEventSource.OPEN;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close() {
    this.closed = true;
    this.readyState = MockEventSource.CLOSED;
  }

  emit(payload: object) {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }

  emitError(readyState: number) {
    this.readyState = readyState;
    this.onerror?.();
  }
}

function latestES(): MockEventSource {
  return MockEventSource.instances[MockEventSource.instances.length - 1];
}

describe('IngestionProgress', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    MockEventSource.instances = [];
    vi.stubGlobal('EventSource', MockEventSource);
    vi.mocked(ingestionApi.getSSETicket).mockResolvedValue({ ticket: 'tkt-123' });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('gọi getSSETicket và mở EventSource khi mount', async () => {
    render(<IngestionProgress documentId="doc-1" onComplete={vi.fn()} onError={vi.fn()} />);
    await waitFor(() => expect(vi.mocked(ingestionApi.getSSETicket)).toHaveBeenCalledWith('doc-1'));
    await waitFor(() => expect(latestES()).toBeDefined());
    expect(latestES().url).toContain('ticket=tkt-123');
  });

  it('cập nhật progress bar khi nhận event progress', async () => {
    render(<IngestionProgress documentId="doc-1" onComplete={vi.fn()} onError={vi.fn()} />);
    await waitFor(() => expect(latestES()).toBeDefined());

    act(() => {
      latestES().emit({
        event: 'progress',
        taskId: 'doc-1',
        status: 'embedding',
        percent: 60,
        message: 'Đang tạo vector nhúng...',
      });
    });

    await waitFor(() => expect(screen.getByText('60%')).toBeInTheDocument());
    expect(screen.getByText('Đang tạo vector nhúng...')).toBeInTheDocument();
  });

  it('gọi onComplete khi nhận event completed', async () => {
    const onComplete = vi.fn();
    render(<IngestionProgress documentId="doc-1" onComplete={onComplete} onError={vi.fn()} />);
    await waitFor(() => expect(latestES()).toBeDefined());

    act(() => {
      latestES().emit({ event: 'completed', taskId: 'doc-1', documentId: 'doc-1' });
    });

    await waitFor(() => expect(onComplete).toHaveBeenCalledTimes(1));
    expect(latestES().closed).toBe(true);
  });

  it('gọi onError khi nhận event error', async () => {
    const onError = vi.fn();
    render(<IngestionProgress documentId="doc-1" onComplete={vi.fn()} onError={onError} />);
    await waitFor(() => expect(latestES()).toBeDefined());

    act(() => {
      latestES().emit({ event: 'error', taskId: 'doc-1', message: 'Lỗi xử lý' });
    });

    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
    expect(latestES().closed).toBe(true);
  });

  it('gọi onError khi getSSETicket thất bại', async () => {
    const onError = vi.fn();
    vi.mocked(ingestionApi.getSSETicket).mockRejectedValue(new Error('network'));
    render(<IngestionProgress documentId="doc-1" onComplete={vi.fn()} onError={onError} />);
    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
  });

  it('KHÔNG gọi onError khi onerror tạm thời (EventSource đang reconnect)', async () => {
    const onError = vi.fn();
    render(<IngestionProgress documentId="doc-1" onComplete={vi.fn()} onError={onError} />);
    await waitFor(() => expect(latestES()).toBeDefined());

    act(() => {
      latestES().emitError(MockEventSource.CONNECTING);
    });

    // Drop tạm thời → browser tự reconnect, không được báo lỗi.
    expect(onError).not.toHaveBeenCalled();
  });

  it('gọi onError khi onerror với trạng thái CLOSED (không reconnect được)', async () => {
    const onError = vi.fn();
    render(<IngestionProgress documentId="doc-1" onComplete={vi.fn()} onError={onError} />);
    await waitFor(() => expect(latestES()).toBeDefined());

    act(() => {
      latestES().emitError(MockEventSource.CLOSED);
    });

    await waitFor(() => expect(onError).toHaveBeenCalledTimes(1));
  });

  it('gọi onTimeout khi nhận event timeout', async () => {
    const onTimeout = vi.fn();
    const onError = vi.fn();
    render(
      <IngestionProgress
        documentId="doc-1"
        onComplete={vi.fn()}
        onError={onError}
        onTimeout={onTimeout}
      />,
    );
    await waitFor(() => expect(latestES()).toBeDefined());

    act(() => {
      latestES().emit({ event: 'timeout', taskId: 'doc-1' });
    });

    await waitFor(() => expect(onTimeout).toHaveBeenCalledTimes(1));
    expect(onError).not.toHaveBeenCalled();
    expect(latestES().closed).toBe(true);
  });
});
