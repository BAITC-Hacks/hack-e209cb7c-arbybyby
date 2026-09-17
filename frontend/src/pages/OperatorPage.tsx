import { useEffect, useState } from "react";
import type { Ticket } from "../api/types";
import { fetchTickets } from "../api/client";
import TicketCard from "../components/TicketCard";
import AIWorkspace from "../components/AIWorkspace";

export default function OperatorPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchTickets()
      .then((data) => {
        setTickets(data);
        if (data.length) setSelectedId(data[0].id);
      })
      .catch(() => setError("Не удалось загрузить обращения. Запущен ли backend на :8000?"))
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

  return (
    <div className="h-full flex">
      {/* left: ticket list */}
      <aside className="w-1/3 border-r border-line flex flex-col">
        <div className="p-4 border-b border-line">
          <div className="text-sm text-muted">
            Входящие:{" "}
            <span className="text-white font-semibold">{incoming}</span>
            <span className="mx-2 text-line">|</span>
            В работе:{" "}
            <span className="text-warn font-semibold">{inProgress}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-3 space-y-2">
          {loading && (
            <p className="text-sm text-muted p-2">Загрузка обращений…</p>
          )}
          {error && <p className="text-sm text-danger p-2">{error}</p>}
          {tickets.map((t) => (
            <TicketCard
              key={t.id}
              ticket={t}
              active={t.id === selectedId}
              onClick={() => setSelectedId(t.id)}
            />
          ))}
        </div>
      </aside>

      {/* right: AI workspace */}
      <section className="w-2/3">
        {selected ? (
          <AIWorkspace
            key={selected.id}
            ticket={selected}
            onResolved={handleResolved}
          />
        ) : (
          <div className="h-full flex items-center justify-center text-muted">
            {loading ? "Загрузка…" : "Выберите обращение слева"}
          </div>
        )}
      </section>
    </div>
  );
}
