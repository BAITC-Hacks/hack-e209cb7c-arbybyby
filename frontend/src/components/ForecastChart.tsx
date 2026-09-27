import { useEffect, useMemo, useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ForecastResponse } from "../api/types";
import { fetchForecast } from "../api/client";
import Spinner from "./Spinner";

const MONTH_OPTIONS = [1, 2, 3];

/** Сколько дней истории показываем слева от прогноза. */
const HISTORY_TAIL = 45;

const AXIS_TICK = { fill: "#9CA3AF", fontSize: 12 };

interface Row {
  date: string;
  actual?: number;
  predicted?: number;
  /** [низ, верх] — Recharts рисует область по паре значений. */
  band?: [number, number];
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("ru-RU", { day: "2-digit", month: "short" });
}

export default function ForecastChart() {
  const [months, setMonths] = useState(3);
  const [data, setData] = useState<ForecastResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    fetchForecast(months)
      .then((res) => !cancelled && setData(res))
      .catch(() => !cancelled && setError(true))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [months]);

  const rows = useMemo<Row[]>(() => {
    if (!data) return [];
    const history: Row[] = data.history.slice(-HISTORY_TAIL).map((h) => ({
      date: h.date,
      actual: h.actual,
    }));
    const forecast: Row[] = data.forecast.map((f) => ({
      date: f.date,
      predicted: f.predicted,
      band: [f.lower, f.upper],
    }));
    // стыкуем ряды: последняя фактическая точка становится началом прогноза,
    // иначе между линиями остаётся разрыв
    const last = history[history.length - 1];
    if (last) {
      forecast.unshift({
        date: last.date,
        predicted: last.actual,
        band: [last.actual ?? 0, last.actual ?? 0],
      });
    }
    return [...history, ...forecast];
  }, [data]);

  const tabClass = (active: boolean) =>
    `px-2 py-1 text-xs font-medium rounded transition-colors duration-150 ${
      active
        ? "bg-accent-light text-accent"
        : "text-gray-500 hover:text-gray-700"
    }`;

  return (
    <section className="bg-white border border-line rounded-md p-4">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h2 className="section-label">Прогноз нагрузки</h2>
        <div className="flex items-center gap-1 shrink-0">
          {MONTH_OPTIONS.map((m) => (
            <button
              key={m}
              onClick={() => setMonths(m)}
              className={tabClass(m === months)}
            >
              {m} мес
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="flex items-center justify-center gap-2 py-16">
          <Spinner />
          <span className="text-sm text-gray-400">Считаю прогноз…</span>
        </div>
      )}

      {error && !loading && (
        <p className="text-sm text-gray-400 text-center py-16">
          Не удалось построить прогноз
        </p>
      )}

      {!loading && !error && data && (
        <>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart
                data={rows}
                margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
              >
                <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  tick={AXIS_TICK}
                  tickLine={false}
                  axisLine={{ stroke: "#E5E7EB" }}
                  minTickGap={28}
                />
                <YAxis
                  tick={AXIS_TICK}
                  tickLine={false}
                  axisLine={false}
                  width={44}
                />
                <Tooltip
                  labelFormatter={(v) => formatDate(String(v))}
                  formatter={(value, name) => {
                    if (name === "Доверительный интервал") {
                      const pair = value as unknown as [number, number];
                      return [`${pair[0]} – ${pair[1]}`, name];
                    }
                    return [value, name];
                  }}
                  contentStyle={{
                    backgroundColor: "#FFFFFF",
                    border: "1px solid #E5E7EB",
                    borderRadius: 6,
                    boxShadow: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
                    fontSize: 12,
                    padding: "8px 10px",
                  }}
                  labelStyle={{ color: "#111827", fontWeight: 500, marginBottom: 4 }}
                  itemStyle={{ color: "#6B7280", padding: 0 }}
                  cursor={{ stroke: "#E5E7EB", strokeWidth: 1 }}
                />
                <Legend
                  iconType="plainline"
                  wrapperStyle={{ fontSize: 12, color: "#6B7280" }}
                />
                <Area
                  dataKey="band"
                  name="Доверительный интервал"
                  stroke="none"
                  fill="#2563EB"
                  fillOpacity={0.1}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="actual"
                  name="Факт"
                  stroke="#2563EB"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  name="Прогноз"
                  stroke="#2563EB"
                  strokeWidth={1.5}
                  strokeDasharray="4 3"
                  dot={false}
                  isAnimationActive={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-400">
            <span>
              Ожидается{" "}
              <span className="text-gray-700 font-medium tabular-nums">
                {data.summary.total_predicted.toLocaleString("ru-RU")}
              </span>{" "}
              обращений за {data.months} мес
            </span>
            <span>
              В среднем{" "}
              <span className="text-gray-700 font-medium tabular-nums">
                {data.summary.avg_per_day_forecast}
              </span>{" "}
              в день
              {data.summary.change_percent !== 0 && (
                <span
                  className={
                    data.summary.change_percent > 0
                      ? "text-red-600 ml-1"
                      : "text-green-600 ml-1"
                  }
                >
                  {data.summary.change_percent > 0 ? "↑" : "↓"}{" "}
                  {Math.abs(data.summary.change_percent)}%
                </span>
              )}
            </span>
            <span className="text-gray-300">{data.method}</span>
          </div>
        </>
      )}
    </section>
  );
}
