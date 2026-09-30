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
const PALETTE = ["#2563EB", "#6B7280", "#9CA3AF"];

const AXIS_TICK = { fill: "#9CA3AF", fontSize: 12 };

interface Props {
  data: TimelinePoint[];
  /** Окно в днях — только для заголовка. */
  period: number;
}

export default function LoadChart({ data, period }: Props) {
  // Набор категорий задаёт бэкенд (все массовые или одна выбранная),
  // поэтому серии выводим из самих данных, а не из константы.
  const series = Object.keys(data[0] ?? {}).filter((key) => key !== "day");

  return (
    <div className="bg-white border border-line rounded-md p-4 h-full flex flex-col">
      <h2 className="section-label mb-4">Нагрузка за {period} дней</h2>

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
                minTickGap={16}
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
              {series.map((name, i) => (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  stroke={PALETTE[i % PALETTE.length]}
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
