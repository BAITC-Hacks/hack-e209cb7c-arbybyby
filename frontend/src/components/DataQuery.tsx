import { useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AskResponse } from "../api/types";
import { askData } from "../api/client";
import Spinner from "./Spinner";

const EXAMPLES = [
  "Сколько обращений по ЖКХ в Астане?",
  "Какой район лидирует по жалобам?",
  "Тренд по дорогам за месяц",
];

const AXIS_TICK = { fill: "#9CA3AF", fontSize: 11 };

function shortLabel(label: string): string {
  // даты приходят как YYYY-MM-DD, названия регионов — как есть
  if (/^\d{4}-\d{2}-\d{2}$/.test(label)) {
    return new Date(label).toLocaleDateString("ru-RU", {
      day: "2-digit",
      month: "2-digit",
    });
  }
  return label;
}

export default function DataQuery() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);

  const run = async (text: string) => {
    const query = text.trim();
    if (!query || loading) return;
    setLoading(true);
    setError(false);
    try {
      setResult(await askData(query));
    } catch {
      setError(true);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const runExample = (text: string) => {
    setQuestion(text);
    run(text);
  };

  const filters = result?.filters_applied;
  const activeFilters = filters
    ? [
        filters.category && `категория: ${filters.category}`,
        filters.region && `регион: ${filters.region}`,
        filters.period && `период: ${filters.period}`,
      ].filter(Boolean)
    : [];

  return (
    <section className="bg-white border border-line rounded-md p-4">
      <h2 className="section-label mb-3">Запрос к данным</h2>

      <div className="flex items-center gap-2">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run(question)}
          placeholder="Задайте вопрос данным…"
          className="flex-1 min-w-0 text-sm border border-line rounded-md px-3 py-1.5 bg-white text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-colors duration-150"
        />
        {/* Вторичная кнопка: запрос к данным — не основное действие экрана,
            заливка акцентом перетягивала на себя внимание. */}
        <button
          onClick={() => run(question)}
          disabled={loading || !question.trim()}
          className="shrink-0 px-3 py-1.5 bg-white border border-line text-accent text-sm font-medium rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
        >
          Спросить
        </button>
      </div>

      <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
        {EXAMPLES.map((example, i) => (
          <span key={example} className="flex items-center gap-2">
            {i > 0 && <span className="text-gray-300">·</span>}
            <button
              onClick={() => runExample(example)}
              className="text-xs text-gray-400 hover:text-accent transition-colors duration-150"
            >
              {example}
            </button>
          </span>
        ))}
      </div>

      {loading && (
        <div className="flex items-center gap-2 mt-4">
          <Spinner />
          <span className="text-sm text-gray-400">Считаю…</span>
        </div>
      )}

      {error && !loading && (
        <p className="text-sm text-gray-400 mt-4">Не удалось получить ответ</p>
      )}

      {result && !loading && !error && (
        <div className="mt-4">
          <div className="text-2xl font-semibold text-gray-900">
            {result.answer}
          </div>
          {result.detail && (
            <div className="text-sm text-gray-500 mt-0.5">{result.detail}</div>
          )}

          {activeFilters.length > 0 && (
            <div className="text-xs text-gray-400 mt-1">
              {activeFilters.join(" · ")}
            </div>
          )}

          {result.clarification && (
            <div className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1 mt-2 inline-block">
              {result.clarification}
            </div>
          )}

          {result.data.length > 1 && (
            <div className="h-[140px] mt-3">
              <ResponsiveContainer width="100%" height="100%">
                {result.chart === "bar" ? (
                  <BarChart
                    data={result.data}
                    margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="label"
                      tickFormatter={shortLabel}
                      tick={AXIS_TICK}
                      tickLine={false}
                      axisLine={{ stroke: "#E5E7EB" }}
                    />
                    <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} width={40} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#FFFFFF",
                        border: "1px solid #E5E7EB",
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      cursor={{ fill: "#F9FAFB" }}
                    />
                    <Bar dataKey="value" name="Обращений" fill="#2563EB" radius={[2, 2, 0, 0]} />
                  </BarChart>
                ) : (
                  <LineChart
                    data={result.data}
                    margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid stroke="#F3F4F6" strokeDasharray="3 3" />
                    <XAxis
                      dataKey="label"
                      tickFormatter={shortLabel}
                      tick={AXIS_TICK}
                      tickLine={false}
                      axisLine={{ stroke: "#E5E7EB" }}
                      minTickGap={24}
                    />
                    <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} width={40} />
                    <Tooltip
                      labelFormatter={(v) => shortLabel(String(v))}
                      contentStyle={{
                        backgroundColor: "#FFFFFF",
                        border: "1px solid #E5E7EB",
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      cursor={{ stroke: "#E5E7EB", strokeWidth: 1 }}
                    />
                    <Line
                      type="monotone"
                      dataKey="value"
                      name="Обращений"
                      stroke="#2563EB"
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </LineChart>
                )}
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
