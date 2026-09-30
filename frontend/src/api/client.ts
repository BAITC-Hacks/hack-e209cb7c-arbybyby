import axios from "axios";
import type {
  AnalyticsSummary,
  AskResponse,
  ForecastResponse,
  ClassifyResponse,
  RegionStats,
  SimilarTicket,
  Spike,
  Ticket,
  TimelinePoint,
} from "./types";

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

// -------- Tickets --------
export async function fetchTickets(params?: {
  region?: string;
  status?: string;
  category?: string;
  priority?: string;
  q?: string;
}): Promise<Ticket[]> {
  // Пустые значения не отправляем — «Все» в дропдауне означает отсутствие фильтра.
  const query = Object.fromEntries(
    Object.entries(params ?? {}).filter(([, v]) => v)
  );
  const { data } = await api.get<Ticket[]>("/api/tickets", { params: query });
  return data;
}

export async function fetchTicket(id: number): Promise<Ticket> {
  const { data } = await api.get<Ticket>(`/api/tickets/${id}`);
  return data;
}

export async function classifyTicket(id: number): Promise<ClassifyResponse> {
  const { data } = await api.post<ClassifyResponse>(`/api/tickets/${id}/classify`);
  return data;
}

export async function approveTicket(id: number): Promise<Ticket> {
  const { data } = await api.post<Ticket>(`/api/tickets/${id}/approve`);
  return data;
}

export async function correctTicket(
  id: number,
  correctedCategory: string,
  originalCategory?: string | null
): Promise<Ticket> {
  const { data } = await api.post<Ticket>(`/api/tickets/${id}/correct`, {
    original_category: originalCategory ?? null,
    corrected_category: correctedCategory,
  });
  return data;
}

/** Ссылки на выгрузку отчётов — браузер качает файл сам. */
export const exportUrls = {
  pdf: `${BASE_URL}/api/analytics/export/pdf`,
  excel: `${BASE_URL}/api/analytics/export/excel`,
};

export async function fetchSimilar(id: number): Promise<SimilarTicket[]> {
  const { data } = await api.get<SimilarTicket[]>(`/api/tickets/${id}/similar`);
  return data;
}

// -------- Analytics --------
export async function fetchSummary(): Promise<AnalyticsSummary> {
  const { data } = await api.get<AnalyticsSummary>("/api/analytics/summary");
  return data;
}

export async function fetchRegions(
  period: number,
  category?: string
): Promise<RegionStats[]> {
  const { data } = await api.get<RegionStats[]>("/api/analytics/regions", {
    params: { period, ...(category ? { category } : {}) },
  });
  return data;
}

export async function fetchSpikes(): Promise<Spike[]> {
  const { data } = await api.get<Spike[]>("/api/analytics/spikes");
  return data;
}

export async function fetchTimeline(
  period: number,
  category?: string
): Promise<TimelinePoint[]> {
  const { data } = await api.get<TimelinePoint[]>("/api/analytics/timeline", {
    params: { period, ...(category ? { category } : {}) },
  });
  return data;
}

export async function fetchForecast(months: number): Promise<ForecastResponse> {
  const { data } = await api.get<ForecastResponse>("/api/analytics/forecast", {
    params: { months },
  });
  return data;
}

export async function askData(question: string): Promise<AskResponse> {
  const { data } = await api.post<AskResponse>("/api/analytics/ask", { question });
  return data;
}
