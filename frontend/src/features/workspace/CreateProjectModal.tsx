import { useState } from 'react';
import { toast } from 'sonner';
import { createProject } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useProjectStore } from '@/store/projectStore';

interface CreateProjectModalProps {
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateProjectModal({ onClose, onSuccess }: CreateProjectModalProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const addProject = useProjectStore((s) => s.addProject);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setIsSubmitting(true);
    try {
      const project = await createProject(name.trim(), description.trim() || undefined);
      addProject(project);
      toast.success('Đã tạo dự án');
      onSuccess?.();
      onClose();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Không thể tạo dự án'));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: '0 0 16px', fontSize: '1.125rem', color: 'var(--ink-primary)' }}>
          Tạo dự án mới
        </h2>
        <form onSubmit={handleSubmit}>
          <label style={labelStyle}>
            Tên dự án <span style={{ color: 'var(--state-danger)' }}>*</span>
            <input
              style={inputStyle}
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={255}
              required
              autoFocus
              placeholder="Nhập tên dự án..."
            />
          </label>
          <label style={labelStyle}>
            Mô tả
            <textarea
              style={{ ...inputStyle, resize: 'vertical', minHeight: '80px' }}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Nhập mô tả (tùy chọn)..."
            />
          </label>
          <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '16px' }}>
            <button type="button" onClick={onClose} style={cancelBtnStyle}>
              Hủy
            </button>
            <button type="submit" disabled={isSubmitting || !name.trim()} style={submitBtnStyle}>
              {isSubmitting ? 'Đang tạo...' : 'Tạo dự án'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0,0,0,0.4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const modalStyle: React.CSSProperties = {
  background: 'var(--surface-raised)',
  borderRadius: '8px',
  padding: '24px',
  width: '440px',
  maxWidth: '90vw',
  boxShadow: '0 8px 32px rgba(0,0,0,0.16)',
};

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '6px',
  marginBottom: '12px',
  fontSize: '0.875rem',
  color: 'var(--ink-primary)',
  fontWeight: 500,
};

const inputStyle: React.CSSProperties = {
  padding: '8px 10px',
  border: '1px solid var(--border-hairline)',
  borderRadius: '6px',
  fontSize: '0.875rem',
  background: 'var(--surface-base)',
  color: 'var(--ink-primary)',
  outline: 'none',
  width: '100%',
  boxSizing: 'border-box',
};

const cancelBtnStyle: React.CSSProperties = {
  padding: '8px 16px',
  border: '1px solid var(--border-hairline)',
  borderRadius: '6px',
  background: 'transparent',
  color: 'var(--ink-secondary)',
  cursor: 'pointer',
  fontSize: '0.875rem',
};

const submitBtnStyle: React.CSSProperties = {
  padding: '8px 16px',
  border: 'none',
  borderRadius: '6px',
  background: 'var(--accent-blue)',
  color: '#fff',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
};
