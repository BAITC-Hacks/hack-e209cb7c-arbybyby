/**
 * Справочники значений, по которым фильтруется интерфейс.
 *
 * Держим в одном месте: список категорий нужен и фильтрам оператора, и
 * фильтру ситуационного центра, и ручной правке категории в AIWorkspace —
 * расходиться им нельзя.
 */
import type { Priority, Status } from "./types";

export const REGIONS = [
  "Астана",
  "Алматы",
  "Шымкент",
  "Караганда",
  "Павлодар",
  "Актобе",
] as const;

// «Другое» — реальная категория в данных, поэтому она есть и в фильтрах:
// иначе такие обращения находились бы только через «Все».
export const CATEGORIES = [
  "ЖКХ",
  "Дороги",
  "Освещение",
  "Транспорт",
  "Благоустройство",
  "Другое",
] as const;

export const PRIORITIES: { value: Priority; label: string }[] = [
  { value: "high", label: "Высокий" },
  { value: "medium", label: "Средний" },
  { value: "low", label: "Низкий" },
];

export const STATUSES: { value: Status; label: string }[] = [
  { value: "new", label: "Новое" },
  { value: "processing", label: "В работе" },
  { value: "resolved", label: "Решено" },
];

/** Окна аналитики. Значения совпадают с теми, что принимает бэкенд. */
export const PERIODS = [
  { value: 7, label: "7 дней" },
  { value: 30, label: "30 дней" },
  { value: 90, label: "90 дней" },
];
