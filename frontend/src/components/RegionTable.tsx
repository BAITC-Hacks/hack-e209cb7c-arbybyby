import type { RegionStats } from "../api/types";

export default function RegionTable({ rows }: { rows: RegionStats[] }) {
  return (
    <div className="rounded-lg bg-card border border-line overflow-hidden">
      <div className="px-5 py-3 border-b border-line">
        <h3 className="text-sm font-semibold text-white">
          Статистика по регионам
        </h3>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-muted text-xs">
            <th className="px-5 py-2 font-medium">Регион</th>
            <th className="px-5 py-2 font-medium">Обращений</th>
            <th className="px-5 py-2 font-medium">Топ-категория</th>
            <th className="px-5 py-2 font-medium text-right">Тренд</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const up = r.trend_percent >= 0;
            return (
              <tr
                key={r.region}
                className="border-t border-line/60 hover:bg-line/10"
              >
                <td className="px-5 py-3 text-white font-medium">
                  {r.region}
                </td>
                <td className="px-5 py-3 text-muted">{r.total}</td>
                <td className="px-5 py-3 text-muted">{r.top_category}</td>
                <td
                  className="px-5 py-3 text-right font-medium"
                  style={{ color: up ? "#F43F5E" : "#10B981" }}
                >
                  {up ? "▲" : "▼"} {Math.abs(r.trend_percent).toFixed(1)}%
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
