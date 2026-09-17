import type { Spike } from "../api/types";

export default function SpikeAlert({ spikes }: { spikes: Spike[] }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white">
        Детектор всплесков
      </h3>
      <div className="grid gap-3 md:grid-cols-3">
        {spikes.map((s, i) => (
          <div
            key={i}
            className="rounded-lg border border-danger/50 bg-danger/10 p-4"
          >
            <div className="flex items-start gap-2">
              <span className="text-lg leading-none">⚠</span>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-white font-semibold text-sm">
                    {s.region}
                  </span>
                  <span className="text-danger font-bold text-sm">
                    +{s.percent_increase}%
                  </span>
                </div>
                <p className="text-xs text-muted mt-1">{s.description}</p>
                <div className="mt-2 flex items-center gap-2 text-[11px] text-muted">
                  <span className="px-1.5 py-0.5 rounded bg-line/40">
                    {s.category}
                  </span>
                  <span>{s.time_window}</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
