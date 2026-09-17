import type { Priority, Status } from "./types";

export const priorityColor: Record<Priority, string> = {
  high: "#F43F5E",
  medium: "#F59E0B",
  low: "#10B981",
};

export const priorityLabel: Record<Priority, string> = {
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
};

export const statusLabel: Record<Status, string> = {
  new: "Новое",
  processing: "В работе",
  resolved: "Решено",
};

export const statusColor: Record<Status, string> = {
  new: "#6366F1",
  processing: "#F59E0B",
  resolved: "#10B981",
};

export function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}
