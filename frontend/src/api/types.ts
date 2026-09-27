export type Status = "new" | "processing" | "resolved";
export type Priority = "high" | "medium" | "low";

export interface CategoryOption {
  category: string;
  subcategory: string;
  responsible_service: string;
  confidence: number;
}

export interface Ticket {
  id: number;
  /** Гражданин обозначается только номером — ФИО в системе нет. */
  citizen_label?: string | null;
  text: string;
  source: string;
  region: string;
  created_at: string;
  status: Status;
  priority: Priority;
  category: string | null;
  subcategory: string | null;
  address: string | null;
  responsible_service: string | null;
  confidence_score: number | null;
  reasoning: string | null;
  needs_review?: boolean;
  alternatives?: CategoryOption[];
}

export interface ClassifyResponse {
  category: string;
  subcategory: string;
  address: string | null;
  priority: Priority;
  responsible_service: string;
  confidence_score: number;
  reasoning: string;
  needs_review: boolean;
  alternatives: CategoryOption[];
}

export interface SimilarTicket {
  id: number;
  text: string;
  category: string;
  similarity_score: number;
}

export interface AnalyticsSummary {
  total_tickets: number;
  avg_processing_time: number;
  resolved_percent: number;
  critical_count: number;
}

export interface RegionStats {
  region: string;
  total: number;
  top_category: string;
  trend_percent: number;
}

export interface Spike {
  region: string;
  description: string;
  percent_increase: number;
  category: string;
  time_window: string;
}

export interface TimelinePoint {
  day: string;
  ЖКХ: number;
  Дороги: number;
  Освещение: number;
}

export interface ForecastPoint {
  date: string;
  predicted: number;
  lower: number;
  upper: number;
}

export interface ForecastResponse {
  method: string;
  months: number;
  horizon_days: number;
  history: { date: string; actual: number }[];
  forecast: ForecastPoint[];
  summary: {
    total_predicted: number;
    avg_per_day_recent: number;
    avg_per_day_forecast: number;
    change_percent: number;
  };
}

export interface AskResponse {
  answer: string;
  detail?: string;
  filters_applied: {
    category: string | null;
    region: string | null;
    period: string;
  };
  data: { label: string; value: number }[];
  chart?: "line" | "bar";
  clarification?: string;
}
