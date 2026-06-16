import { useState } from 'react';
import { toast } from 'sonner';
import { deleteProject } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import { useProjectStore } from '@/store/projectStore';

interface DeleteProjectModalProps {
  projectId: string;
  projectName: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export function DeleteProjectModal({ projectId, projectName, onClose, onSuccess }: DeleteProjectModalProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const removeProject = useProjectStore((s) => s.removeProject);

  async function handleConfirm() {
    setIsDeleting(true);
    try {
      await deleteProject(projectId);
      removeProject(projectId);
      toast.success('Đã xóa dự án');
      onSuccess?.();
      onClose();
    } catch (err) {
      toast.error(getErrorMessage(err, 'Không thể xóa dự án'));
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div style={overlayStyle} onClick={onClose}>
      <div style={modalStyle} onClick={(e) => e.stopPropagation()}>
        <h2 style={{ margin: '0 0 12px', fontSize: '1.125rem', color: 'var(--ink-primary)' }}>
          Xóa dự án
        </h2>
        <p style={{ margin: '0 0 20px', fontSize: '0.875rem', color: 'var(--ink-secondary)' }}>
          Bạn có chắc muốn xóa dự án <strong>"{projectName}"</strong>? Hành động này không thể hoàn tác.
        </p>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button type="button" onClick={onClose} style={cancelBtnStyle}>
            Hủy
          </button>
          <button type="button" onClick={handleConfirm} disabled={isDeleting} style={deleteBtnStyle}>
            {isDeleting ? 'Đang xóa...' : 'Xóa dự án'}
          </button>
        </div>
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
  width: '400px',
  maxWidth: '90vw',
  boxShadow: '0 8px 32px rgba(0,0,0,0.16)',
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

const deleteBtnStyle: React.CSSProperties = {
  padding: '8px 16px',
  border: 'none',
  borderRadius: '6px',
  background: 'var(--state-danger)',
  color: '#fff',
  cursor: 'pointer',
  fontSize: '0.875rem',
  fontWeight: 500,
};
