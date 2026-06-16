import axios from 'axios';

const apiClient = axios.create({
  baseURL: '',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

// Endpoints where a 401 is an expected business response (wrong credentials,
// no session yet) and must NOT trigger a global redirect — the calling page
// shows its own error toast instead.
const AUTH_ENDPOINTS = ['/api/auth/login', '/api/auth/register'];

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const url: string = error.config?.url ?? '';
    const isAuthEndpoint = AUTH_ENDPOINTS.some((path) => url.includes(path));
    if (error.response?.status === 401 && !isAuthEndpoint) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default apiClient;
