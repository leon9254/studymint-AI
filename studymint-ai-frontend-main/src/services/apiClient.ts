const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api/v1";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("studymint_token");
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers
      }
    });
  } catch (err) {
    const message = err instanceof Error && err.message ? err.message : "Network request failed";
    throw new ApiError(0, `Backend request failed: ${message}. Check that FastAPI is running and CORS is configured.`);
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: response.statusText }));
    const detail = payload.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => item.msg ?? item.message ?? JSON.stringify(item)).join("; ")
      : typeof detail === "string"
        ? detail
        : detail
          ? JSON.stringify(detail)
          : "Request failed";
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
