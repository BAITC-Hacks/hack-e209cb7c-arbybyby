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

export default function LoadChart({ data }: { data: TimelinePoint[] }) {
  return (
    <div className="rounded-lg bg-card border border-line p-5 h-full">
      <h3 className="text-sm font-semibold text-white mb-4">
        Нагрузка за 7 дней
      </h3>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis dataKey="day" stroke="#CBD5E1" fontSize={12} />
          <YAxis stroke="#CBD5E1" fontSize={12} />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1E293B",
              border: "1px solid #334155",
              borderRadius: 8,
              color: "#fff",
            }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line
            type="monotone"
            dataKey="ЖКХ"
            stroke="#6366F1"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="Дороги"
            stroke="#F59E0B"
            strokeWidth={2}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="Освещение"
            stroke="#10B981"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
