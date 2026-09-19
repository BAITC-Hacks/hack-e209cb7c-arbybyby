import type { Priority, Status } from "./types";

/** Цвет точки приоритета в списке обращений. */
export const priorityColor: Record<Priority, string> = {
  high: "#DC2626",
  medium: "#D97706",
  low: "#16A34A",
};

export const priorityLabel: Record<Priority, string> = {
  high: "Высокий",
  medium: "Средний",
  low: "Низкий",
};

/** Бейдж приоритета — светлая заливка, без обводки и тени. */
export const priorityBadge: Record<Priority, string> = {
  high: "bg-red-50 text-red-700",
  medium: "bg-amber-50 text-amber-700",
  low: "bg-green-50 text-green-700",
};

export const statusLabel: Record<Status, string> = {
  new: "Новое",
  processing: "В работе",
  resolved: "Решено",
};

export const statusBadge: Record<Status, string> = {
  new: "bg-amber-50 text-amber-700",
  processing: "bg-blue-50 text-blue-700",
  resolved: "bg-green-50 text-green-700",
};

export function formatTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
}

/** Тренд по региону: «↑ 12%» / «↓ 3%». */
export function formatTrend(percent: number): string {
  const arrow = percent >= 0 ? "↑" : "↓";
  return `${arrow} ${Math.abs(percent).toFixed(0)}%`;
}
