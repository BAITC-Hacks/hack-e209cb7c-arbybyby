interface Props {
  label: string;
  value: string;
  accent?: string;
  hint?: string;
}

export default function MetricCard({ label, value, accent, hint }: Props) {
  return (
    <div className="rounded-lg bg-card border border-line p-5">
      <div className="text-sm text-muted">{label}</div>
      <div
        className="text-3xl font-bold mt-1"
        style={{ color: accent || "#FFFFFF" }}
      >
        {value}
      </div>
      {hint && <div className="text-xs text-muted mt-1">{hint}</div>}
    </div>
  );
}
