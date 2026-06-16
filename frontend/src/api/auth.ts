import type { UserResponse } from '@/types/auth';
import apiClient from './client';

export async function loginUser(email: string, password: string): Promise<UserResponse> {
  const res = await apiClient.post<UserResponse>('/api/auth/login', { email, password });
  return res.data;
}

export async function registerUser(email: string, password: string): Promise<UserResponse> {
  const res = await apiClient.post<UserResponse>('/api/auth/register', { email, password });
  return res.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const res = await apiClient.get<UserResponse>('/api/auth/me');
  return res.data;
}

export async function logoutUser(): Promise<void> {
  await apiClient.post('/api/auth/logout');
}
