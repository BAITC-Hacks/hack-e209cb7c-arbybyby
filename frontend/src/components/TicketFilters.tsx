import { MagnifyingGlassIcon } from "@heroicons/react/24/outline";
import type { TicketFilters as Filters } from "../api/types";
import { CATEGORIES, PRIORITIES, REGIONS, STATUSES } from "../api/catalog";
import FilterSelect from "./FilterSelect";

export const EMPTY_FILTERS: Filters = {
  region: "",
  category: "",
  priority: "",
  status: "",
  q: "",
};

interface Props {
  value: Filters;
  onChange: (next: Filters) => void;
}

const asOptions = (items: readonly string[]) =>
  items.map((name) => ({ value: name, label: name }));

/** Строка фильтров над списком обращений: поиск + четыре измерения. */
export default function TicketFilters({ value, onChange }: Props) {
  const set = (patch: Partial<Filters>) => onChange({ ...value, ...patch });
  const dirty = Object.values(value).some((v) => v !== "");

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <div className="relative flex-1 min-w-0">
          <MagnifyingGlassIcon className="pointer-events-none absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
          <input
            value={value.q}
            onChange={(e) => set({ q: e.target.value })}
            placeholder="Поиск…"
            aria-label="Поиск по тексту обращения"
            className="h-8 w-full rounded-md border border-line bg-white pl-7 pr-2 text-xs text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-colors duration-150"
          />
        </div>
        {dirty && (
          <button
            onClick={() => onChange(EMPTY_FILTERS)}
            className="shrink-0 text-xs text-gray-400 hover:text-accent transition-colors duration-150"
          >
            Сбросить
          </button>
        )}
      </div>

      <div className="grid grid-cols-4 gap-1.5">
        <FilterSelect
          label="Регион"
          value={value.region}
          options={asOptions(REGIONS)}
          onChange={(region) => set({ region })}
        />
        <FilterSelect
          label="Категория"
          value={value.category}
          options={asOptions(CATEGORIES)}
          onChange={(category) => set({ category })}
        />
        <FilterSelect
          label="Приоритет"
          value={value.priority}
          options={PRIORITIES}
          onChange={(priority) => set({ priority })}
        />
        <FilterSelect
          label="Статус"
          value={value.status}
          options={STATUSES}
          onChange={(status) => set({ status })}
        />
      </div>
    </div>
  );
}
