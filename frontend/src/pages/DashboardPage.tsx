import { useEffect, useState } from "react";
import type {
  AnalyticsSummary,
  RegionStats,
  Spike,
  TimelinePoint,
} from "../api/types";
import {
  fetchRegions,
  fetchSpikes,
  fetchSummary,
  fetchTimeline,
} from "../api/client";
import MetricCard from "../components/MetricCard";
import RegionTable from "../components/RegionTable";
import LoadChart from "../components/LoadChart";
import SpikeAlert from "../components/SpikeAlert";
import Spinner from "../components/Spinner";

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [regions, setRegions] = useState<RegionStats[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [spikes, setSpikes] = useState<Spike[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchSummary(),
      fetchRegions(),
      fetchTimeline(),
      fetchSpikes(),
    ])
      .then(([s, r, t, sp]) => {
        setSummary(s);
        setRegions(r);
        setTimeline(t);
        setSpikes(sp);
      })
      .catch(() =>
        setError("Не удалось загрузить аналитику. Запущен ли backend на :8000?")
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center gap-2">
        <Spinner />
        <span className="text-sm text-gray-400">Загрузка…</span>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 sm:p-6 space-y-6">
        <h1 className="text-lg font-semibold text-gray-900">
          Ситуационный центр
        </h1>

        {error && (
          <div className="bg-white border border-line border-l-4 border-l-red-500 rounded-md p-4 text-sm text-gray-900">
            {error}
          </div>
        )}

        {/* Метрики */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <MetricCard
            label="Всего обращений"
            value={summary ? summary.total_tickets.toLocaleString("ru-RU") : "—"}
          />
          <MetricCard
            label="Среднее время обработки"
            value={summary ? `${summary.avg_processing_time} мин` : "—"}
          />
          <MetricCard
            label="Решено"
            value={summary ? `${summary.resolved_percent}%` : "—"}
          />
          <MetricCard
            label="Критических"
            value={summary ? String(summary.critical_count) : "—"}
          />
        </div>

        {/* Таблица регионов + график */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6">
          <div className="lg:col-span-3">
            <RegionTable rows={regions} />
          </div>
          <div className="lg:col-span-2">
            <LoadChart data={timeline} />
          </div>
        </div>

        {/* Всплески */}
        <SpikeAlert spikes={spikes} />
      </div>
    </div>
  );
}
