import axios from "axios";
import type {
  AnalyticsSummary,
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
}): Promise<Ticket[]> {
  const { data } = await api.get<Ticket[]>("/api/tickets", { params });
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

export async function fetchSimilar(id: number): Promise<SimilarTicket[]> {
  const { data } = await api.get<SimilarTicket[]>(`/api/tickets/${id}/similar`);
  return data;
}

// -------- Analytics --------
export async function fetchSummary(): Promise<AnalyticsSummary> {
  const { data } = await api.get<AnalyticsSummary>("/api/analytics/summary");
  return data;
}

export async function fetchRegions(): Promise<RegionStats[]> {
  const { data } = await api.get<RegionStats[]>("/api/analytics/regions");
  return data;
}

export async function fetchSpikes(): Promise<Spike[]> {
  const { data } = await api.get<Spike[]>("/api/analytics/spikes");
  return data;
}

export async function fetchTimeline(): Promise<TimelinePoint[]> {
  const { data } = await api.get<TimelinePoint[]>("/api/analytics/timeline");
  return data;
}
