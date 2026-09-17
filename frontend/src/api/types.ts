export type Status = "new" | "processing" | "resolved";
export type Priority = "high" | "medium" | "low";

export interface Ticket {
  id: number;
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
}

export interface ClassifyResponse {
  category: string;
  subcategory: string;
  address: string | null;
  priority: Priority;
  responsible_service: string;
  confidence_score: number;
  reasoning: string;
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
