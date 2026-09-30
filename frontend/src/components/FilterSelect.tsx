interface Option {
  value: string;
  label: string;
}

interface Props {
  /** Название измерения: показывается, пока фильтр не выбран. */
  label: string;
  value: string;
  options: Option[];
  onChange: (value: string) => void;
  /** Подпись варианта «без фильтра». */
  allLabel?: string;
  /** false — значение обязательно (например период), вариант «без фильтра» не нужен. */
  clearable?: boolean;
  className?: string;
}

/**
 * Компактный фильтр-дропдаун.
 *
 * Пустое значение = фильтр не применён; в свёрнутом виде селект показывает
 * название измерения («Регион»), поэтому подпись рядом не нужна — в строке
 * фильтров над списком обращений каждый пиксель ширины на счету.
 */
export default function FilterSelect({
  label,
  value,
  options,
  onChange,
  allLabel = "Все",
  clearable = true,
  className = "",
}: Props) {
  const active = value !== "";

  return (
    <select
      aria-label={label}
      title={label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={`h-8 min-w-0 rounded-md border bg-white px-2 text-xs transition-colors duration-150 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent ${
        !clearable
          ? "border-line text-gray-900"
          : active
          ? "border-accent/40 text-gray-900 font-medium"
          : "border-line text-gray-500"
      } ${className}`}
    >
      {clearable && (
        <option value="">{active ? `${label}: ${allLabel}` : label}</option>
      )}
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
