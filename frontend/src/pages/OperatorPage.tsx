import { useEffect, useState } from "react";
import type { Ticket } from "../api/types";
import { fetchTickets } from "../api/client";
import TicketCard from "../components/TicketCard";
import AIWorkspace from "../components/AIWorkspace";
import Spinner from "../components/Spinner";

export default function OperatorPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  /** На узких экранах панели переключаются: список ↔ карточка обращения. */
  const [mobileDetail, setMobileDetail] = useState(false);

  useEffect(() => {
    fetchTickets()
      .then((data) => {
        setTickets(data);
        if (data.length) setSelectedId(data[0].id);
      })
      .catch(() =>
        setError("Не удалось загрузить обращения. Запущен ли backend на :8000?")
      )
      .finally(() => setLoading(false));
  }, []);

  const selected = tickets.find((t) => t.id === selectedId) || null;
  const incoming = tickets.filter((t) => t.status === "new").length;
  const inProgress = tickets.filter((t) => t.status === "processing").length;

  const handleResolved = (updated: Ticket) => {
    setTickets((prev) =>
      prev.map((t) => (t.id === updated.id ? { ...t, ...updated } : t))
    );
  };

  const handleSelect = (id: number) => {
    setSelectedId(id);
    setMobileDetail(true);
  };

  return (
    <div className="h-full flex">
      {/* Слева: список обращений */}
      <aside
        className={`w-full lg:w-[380px] xl:w-[420px] shrink-0 border-r border-line bg-white flex-col ${
          mobileDetail ? "hidden lg:flex" : "flex"
        }`}
      >
        <div className="px-4 py-3 border-b border-line shrink-0">
          <div className="text-xs text-gray-500">
            Входящие:{" "}
            <span className="text-gray-900 font-medium tabular-nums">
              {incoming}
            </span>
            <span className="mx-2 text-gray-300">·</span>
            В работе:{" "}
            <span className="text-gray-900 font-medium tabular-nums">
              {inProgress}
            </span>
          </div>
        </div>

        <div className="flex-1 min-h-0 overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center gap-2 py-10">
              <Spinner />
              <span className="text-sm text-gray-400">Загрузка…</span>
            </div>
          )}

          {error && (
            <div className="m-4 bg-white border border-line border-l-4 border-l-red-500 rounded-md p-4 text-sm text-gray-900">
              {error}
            </div>
          )}

          {!loading && !error && tickets.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-10">
              Нет обращений
            </p>
          )}

          {tickets.map((t) => (
            <TicketCard
              key={t.id}
              ticket={t}
              active={t.id === selectedId}
              onClick={() => handleSelect(t.id)}
            />
          ))}
        </div>
      </aside>

      {/* Справа: рабочая область */}
      <section
        className={`flex-1 min-w-0 ${mobileDetail ? "block" : "hidden lg:block"}`}
      >
        {selected ? (
          <AIWorkspace
            key={selected.id}
            ticket={selected}
            onResolved={handleResolved}
            onBack={() => setMobileDetail(false)}
          />
        ) : (
          <div className="h-full flex items-center justify-center">
            <p className="text-sm text-gray-400">
              {loading ? "Загрузка…" : "Выберите обращение слева"}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
