import type { RegionStats } from "../api/types";
import { formatTrend } from "../api/format";

/**
 * Рост числа обращений — негативный сигнал (красный),
 * снижение — позитивный (зелёный).
 */
function trendClass(percent: number): string {
  return percent >= 0 ? "text-red-600" : "text-green-600";
}

export default function RegionTable({ rows }: { rows: RegionStats[] }) {
  return (
    <div className="bg-white border border-line rounded-md">
      <div className="px-4 py-3 border-b border-line">
        <h2 className="section-label">Статистика по регионам</h2>
      </div>

      {rows.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-8">Нет данных</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px]">
            <thead>
              <tr className="bg-gray-50 border-b border-line">
                <th className="section-label text-left px-4 py-2">Регион</th>
                <th className="section-label text-left px-4 py-2">Обращений</th>
                <th className="section-label text-left px-4 py-2">
                  Топ-категория
                </th>
                <th className="section-label text-right px-4 py-2">Тренд</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.region}
                  className="border-b border-line-soft last:border-b-0 hover:bg-gray-50 transition-colors duration-150"
                >
                  <td className="px-4 py-2.5 text-sm text-gray-900">
                    {r.region}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-900 tabular-nums">
                    {r.total}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-gray-500">
                    {r.top_category}
                  </td>
                  <td
                    className={`px-4 py-2.5 text-xs font-medium text-right tabular-nums ${trendClass(
                      r.trend_percent
                    )}`}
                  >
                    {formatTrend(r.trend_percent)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
