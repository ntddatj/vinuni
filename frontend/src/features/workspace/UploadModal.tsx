import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { getErrorMessage } from '@/api/errors';
import { confirmMetadata, uploadDocument } from '@/api/ingestion';
import { useTranslation } from '@/i18n/useTranslation';
import type { UploadResponse } from '@/types/document';
import styles from './UploadModal.module.css';

type Phase = 'idle' | 'extracting' | 'form' | 'confirming';

interface UploadModalProps {
  projectId: string;
  onClose: () => void;
  onSuccess: (documentId: string) => void;
}

export function UploadModal({ projectId, onClose, onSuccess }: UploadModalProps) {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [title, setTitle] = useState('');
  const [authors, setAuthors] = useState('');
  const [year, setYear] = useState('');
  const [abstract, setAbstract] = useState('');

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    // Reset ngay để chọn lại cùng một file vẫn trigger onChange ở lần sau.
    e.target.value = '';
    if (!file) return;

    if (file.size > 20 * 1024 * 1024) {
      toast.error(t('upload.fileTooLarge'));
      return;
    }

    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['pdf', 'docx'].includes(ext ?? '')) {
      toast.error(t('upload.unsupportedType'));
      return;
    }

    setPhase('extracting');
    try {
      const result = await uploadDocument(file, projectId);
      setUploadResponse(result);
      setTitle(result.title);
      setAuthors(result.authors.join(', '));
      setYear(result.year?.toString() ?? '');
      setAbstract(result.abstract);
      setPhase('form');
    } catch (err) {
      toast.error(getErrorMessage(err, t('upload.errorToast')));
      setPhase('idle');
    }
  }

  async function handleConfirm() {
    if (!uploadResponse) return;
    setPhase('confirming');
    try {
      const result = await confirmMetadata({
        fileId: uploadResponse.fileId,
        title: title.trim(),
        authors: authors.split(',').map((a) => a.trim()).filter(Boolean),
        abstract: abstract.trim(),
        year: year ? parseInt(year, 10) : null,
        projectId,
      });
      toast.success(t('upload.successToast'));
      onSuccess(result.documentId);
      onClose();
    } catch (err) {
      toast.error(getErrorMessage(err, t('upload.errorToast')));
      setPhase('form');
    }
  }

  const isProcessing = phase === 'extracting' || phase === 'confirming';

  // Không cho đóng modal (click overlay) khi đang upload/confirm để tránh setState sau unmount.
  const handleOverlayClose = () => {
    if (!isProcessing) onClose();
  };

  return (
    <div className={styles.overlay} onClick={handleOverlayClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>{t('upload.modalTitle')}</h2>
        </div>

        {(phase === 'idle' || phase === 'extracting') && (
          <div className={styles.uploadArea}>
            {phase === 'idle' ? (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  style={{ display: 'none' }}
                  onChange={handleFileChange}
                  aria-label={t('upload.button')}
                />
                <button
                  type="button"
                  className={styles.selectFileButton}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {t('upload.button')}
                </button>
              </>
            ) : (
              <div className={styles.extractingState}>
                <div className={styles.spinner} aria-hidden="true" />
                <span>{t('upload.extracting')}</span>
              </div>
            )}
          </div>
        )}

        {(phase === 'form' || phase === 'confirming') && (
          <form className={styles.form} onSubmit={(e) => e.preventDefault()}>
            <div className={styles.fieldGroup}>
              <label className={styles.label}>
                {t('upload.fieldTitle')}
                <span className={styles.aiBadge}>{t('upload.aiBadge')}</span>
              </label>
              <input
                className={styles.input}
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                disabled={isProcessing}
              />
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>
                {t('upload.fieldAuthors')}
                <span className={styles.aiBadge}>{t('upload.aiBadge')}</span>
              </label>
              <input
                className={styles.input}
                type="text"
                value={authors}
                onChange={(e) => setAuthors(e.target.value)}
                disabled={isProcessing}
              />
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>
                {t('upload.fieldYear')}
                <span className={styles.aiBadge}>{t('upload.aiBadge')}</span>
              </label>
              <input
                className={styles.input}
                type="number"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                disabled={isProcessing}
                min={1900}
                max={2100}
              />
            </div>

            <div className={styles.fieldGroup}>
              <label className={styles.label}>
                {t('upload.fieldAbstract')}
                <span className={styles.aiBadge}>{t('upload.aiBadge')}</span>
              </label>
              <textarea
                className={`${styles.input} ${styles.textarea}`}
                value={abstract}
                onChange={(e) => setAbstract(e.target.value)}
                disabled={isProcessing}
              />
            </div>

            <div className={styles.footer}>
              <button
                type="button"
                className={styles.cancelButton}
                onClick={onClose}
                disabled={isProcessing}
              >
                {t('upload.cancel')}
              </button>
              <button
                type="button"
                className={styles.confirmButton}
                onClick={handleConfirm}
                disabled={isProcessing}
              >
                {phase === 'confirming' ? (
                  <span className={styles.spinnerInline} aria-hidden="true" />
                ) : null}
                {t('upload.confirm')}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
