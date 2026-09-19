import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TimelinePoint } from "../api/types";

/** Серо-синяя палитра: один акцент + нейтральные тона. */
const SERIES = [
  { key: "ЖКХ", color: "#2563EB" },
  { key: "Дороги", color: "#6B7280" },
  { key: "Освещение", color: "#9CA3AF" },
] as const;

const AXIS_TICK = { fill: "#9CA3AF", fontSize: 12 };

export default function LoadChart({ data }: { data: TimelinePoint[] }) {
  return (
    <div className="bg-white border border-line rounded-md p-4 h-full flex flex-col">
      <h2 className="section-label mb-4">Нагрузка за 7 дней</h2>

      {data.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-12">Нет данных</p>
      ) : (
        <div className="flex-1 min-h-[260px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
              margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
              <XAxis
                dataKey="day"
                tick={AXIS_TICK}
                tickLine={false}
                axisLine={{ stroke: "#E5E7EB" }}
              />
              <YAxis
                tick={AXIS_TICK}
                tickLine={false}
                axisLine={false}
                width={44}
              />
              <Tooltip
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
              {SERIES.map((s) => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  stroke={s.color}
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3, strokeWidth: 0 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
