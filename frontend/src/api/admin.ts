import apiClient from '@/api/client';

export interface SystemSetting {
  key: string;
  value: string;
  description: string | null;
  updatedAt: string;
}

export async function getAdminSettings(): Promise<SystemSetting[]> {
  const res = await apiClient.get<SystemSetting[]>('/api/admin/settings');
  return res.data;
}

export async function updateAdminSetting(key: string, value: string): Promise<SystemSetting> {
  const res = await apiClient.put<SystemSetting>(`/api/admin/settings/${key}`, { value });
  return res.data;
}

export interface PublicSettings {
  maxPapersPerProject: number;
}

// Cấu hình công khai (không cần quyền admin) — dùng cho banner/disable ở trang Library.
export async function getPublicSettings(): Promise<PublicSettings> {
  const res = await apiClient.get<PublicSettings>('/api/admin/settings/public');
  return res.data;
}
