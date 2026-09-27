interface Props {
  label: string;
  value: string;
  /** Значение до внедрения системы — показывает эффект. */
  baseline?: string;
}

export default function MetricCard({ label, value, baseline }: Props) {
  return (
    <div className="bg-white border border-line rounded-md p-3 sm:p-4">
      <div className="text-2xl font-semibold text-gray-900 tabular-nums">
        {value}
      </div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
      {baseline && (
        <div className="text-xs text-gray-400 mt-0.5">до AURA: {baseline}</div>
      )}
    </div>
  );
}
