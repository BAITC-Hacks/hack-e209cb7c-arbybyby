interface Props {
  label: string;
  value: string;
}

export default function MetricCard({ label, value }: Props) {
  return (
    <div className="bg-white border border-line rounded-md p-3 sm:p-4">
      <div className="text-2xl font-semibold text-gray-900 tabular-nums">
        {value}
      </div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}
