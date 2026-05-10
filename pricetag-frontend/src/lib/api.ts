import type {
  FeedbackPayload,
  HistoryDetailItem,
  HistoryResponse,
  HistoryStatus,
  RecognizeResponse,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";
  const isJson = contentType.includes("application/json");
  const payload = isJson ? await response.json() : null;

  if (!response.ok) {
    const message =
      payload?.detail ?? payload?.error ?? "Сервер вернул ошибку.";
    throw new ApiError(message, response.status);
  }

  return payload as T;
}

export async function recognizePrice(file: File): Promise<RecognizeResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE_URL}/recognize`, {
    method: "POST",
    body: formData,
  });

  return parseResponse<RecognizeResponse>(response);
}

export async function fetchHistory(params: {
  limit: number;
  offset: number;
  status: HistoryStatus;
}): Promise<HistoryResponse> {
  const searchParams = new URLSearchParams({
    limit: String(params.limit),
    offset: String(params.offset),
    status: params.status,
  });

  const response = await fetch(`${API_BASE_URL}/history?${searchParams}`);
  return parseResponse<HistoryResponse>(response);
}

export async function fetchRecognitionDetail(
  id: string,
): Promise<HistoryDetailItem> {
  const response = await fetch(`${API_BASE_URL}/history/${id}`);
  return parseResponse<HistoryDetailItem>(response);
}

export async function sendFeedback(
  id: string,
  payload: FeedbackPayload,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/feedback/${id}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  await parseResponse(response);
}

export { API_BASE_URL, ApiError };
