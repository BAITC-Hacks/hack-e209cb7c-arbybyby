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

export default function DashboardPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [regions, setRegions] = useState<RegionStats[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [spikes, setSpikes] = useState<Spike[]>([]);
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
      );
  }, []);

  return (
    <div className="h-full overflow-y-auto p-6 space-y-6">
      {error && <p className="text-sm text-danger">{error}</p>}

      {/* metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Всего обращений"
          value={summary ? summary.total_tickets.toLocaleString("ru-RU") : "—"}
        />
        <MetricCard
          label="Среднее время"
          value={summary ? `${summary.avg_processing_time} мин` : "—"}
          accent="#6366F1"
        />
        <MetricCard
          label="Решено"
          value={summary ? `${summary.resolved_percent}%` : "—"}
          accent="#10B981"
        />
        <MetricCard
          label="Критических"
          value={summary ? String(summary.critical_count) : "—"}
          accent="#F43F5E"
        />
      </div>

      {/* middle: region table + chart */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <RegionTable rows={regions} />
        </div>
        <div className="lg:col-span-2">
          <LoadChart data={timeline} />
        </div>
      </div>

      {/* bottom: spikes */}
      <SpikeAlert spikes={spikes} />
    </div>
  );
}
