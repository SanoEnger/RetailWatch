export type HistoryStatus = "all" | "ok" | "error" | "pending";

export interface RecognizeResponse {
  request_id: string;
  price: number | null;
  raw_text: string | null;
  confidence: number | null;
  timestamp: string;
  detected: boolean;
  engine: string | null;
  message: string | null;
  
  product_name: string | null;
  barcode: string | null;
  weight: string | null;
  store: string | null;
}

export interface HistoryItem {
  id: string;
  extracted_price: number | null;
  raw_text: string | null;
  confidence: number | null;
  is_valid: boolean | null;
  created_at: string;
  
  product_name: string | null;
  barcode: string | null;
  weight: string | null;
  store: string | null;
}

export interface HistoryResponse {
  items: HistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HistoryDetailItem extends HistoryItem {
  image_base64: string | null;
}

export interface FeedbackPayload {
  is_valid: boolean;
  correct_price: number | null;
}
