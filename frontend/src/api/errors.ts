// Extracts a human-readable message from an Axios/FastAPI error.
// FastAPI returns `detail` as a string for business errors (400/401) but as an
// ARRAY of objects for 422 validation errors — never pass that array to a toast.
export function getErrorMessage(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
  return typeof detail === 'string' && detail.length > 0 ? detail : fallback;
}
