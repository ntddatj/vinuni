import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { createProject, listProjects } from '@/api/projects';
import { getErrorMessage } from '@/api/errors';
import styles from './OnboardingPage.module.css';

const CHECKLIST = [
  {
    icon: '✅',
    label: 'Tạo dự án nghiên cứu đầu tiên',
    desc: 'Đặt tên cho không gian nghiên cứu của bạn',
  },
  {
    icon: '📚',
    label: 'Nạp tài liệu khoa học',
    desc: 'Tìm kiếm arXiv/Semantic Scholar hoặc upload PDF',
  },
  {
    icon: '🤖',
    label: 'Chat với AI Agent',
    desc: 'Phân tích khoảng trống nghiên cứu bằng RAG',
  },
];

export function OnboardingPage() {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    listProjects()
      .then((projects) => {
        if (projects.length > 0) {
          navigate('/dashboard', { replace: true });
        }
      })
      .catch(() => {
        // /api/projects not yet available (Story 1.4) — stay on onboarding
      });
  }, [navigate]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      await createProject(name, description || undefined);
      navigate('/dashboard');
    } catch (err: unknown) {
      toast.error(getErrorMessage(err, 'Tạo dự án thất bại'));
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.layout}>
        <div className={styles.formSection}>
          <h1 className={styles.formTitle}>Tạo dự án đầu tiên của bạn</h1>
          <form onSubmit={handleSubmit}>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="project-name">
                Tên dự án
              </label>
              <input
                id="project-name"
                className={styles.input}
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="VD: Nghiên cứu học máy trong y tế"
              />
            </div>
            <div className={styles.field}>
              <label className={styles.label} htmlFor="project-desc">
                Mô tả ngắn (tùy chọn)
              </label>
              <textarea
                id="project-desc"
                className={styles.textarea}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Mô tả mục tiêu nghiên cứu của bạn..."
              />
            </div>
            <button className={styles.button} type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Đang tạo...' : 'Tạo dự án'}
            </button>
          </form>
        </div>

        <div className={styles.checklistSection}>
          <h2 className={styles.checklistTitle}>Hướng dẫn bắt đầu nhanh</h2>
          {CHECKLIST.map((item) => (
            <div key={item.label} className={styles.checklistItem}>
              <span className={styles.checklistIcon}>{item.icon}</span>
              <div className={styles.checklistText}>
                <span className={styles.checklistLabel}>{item.label}</span>
                <span className={styles.checklistDesc}>{item.desc}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
