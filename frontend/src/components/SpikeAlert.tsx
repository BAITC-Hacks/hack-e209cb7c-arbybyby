import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import type { Spike } from "../api/types";

export default function SpikeAlert({ spikes }: { spikes: Spike[] }) {
  return (
    <section className="space-y-3">
      <h2 className="section-label">Детектор всплесков</h2>

      {spikes.length === 0 ? (
        <div className="bg-white border border-line rounded-md p-4">
          <p className="text-sm text-gray-400 text-center">
            Аномалий не обнаружено
          </p>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {spikes.map((s, i) => (
            <div
              key={`${s.region}-${s.category}-${i}`}
              className="bg-white border border-line border-l-4 border-l-red-500 rounded-md p-4"
            >
              <div className="flex items-start gap-2.5">
                <ExclamationTriangleIcon className="h-5 w-5 shrink-0 text-red-500" />
                <div className="min-w-0">
                  <p className="text-sm text-gray-900 leading-snug">
                    {s.description}
                  </p>
                  <p className="text-xs text-gray-400 mt-1.5">
                    {s.time_window} · {s.region} · {s.category} · рост{" "}
                    {s.percent_increase}%
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
