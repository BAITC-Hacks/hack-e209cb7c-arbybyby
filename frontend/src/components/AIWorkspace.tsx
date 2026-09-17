import { useEffect, useMemo, useState } from "react";
import type { SimilarTicket, Ticket } from "../api/types";
import {
  approveTicket,
  classifyTicket,
  fetchSimilar,
} from "../api/client";
import {
  priorityColor,
  priorityLabel,
  statusColor,
  statusLabel,
} from "../api/format";
import SimilarTickets from "./SimilarTickets";

interface Props {
  ticket: Ticket;
  onResolved: (t: Ticket) => void;
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="rounded-lg bg-base/60 border border-line p-3">
      <div className="text-[11px] uppercase tracking-wide text-ai mb-1">
        Заполнено AI
      </div>
      <div className="text-xs text-muted">{label}</div>
      <div className="text-sm text-white font-medium mt-0.5">
        {value || "—"}
      </div>
    </div>
  );
}

export default function AIWorkspace({ ticket, onResolved }: Props) {
  const [current, setCurrent] = useState<Ticket>(ticket);
  const [similar, setSimilar] = useState<SimilarTicket[]>([]);
  const [classifying, setClassifying] = useState(false);
  const [approving, setApproving] = useState(false);

  // синхронизируем при смене выбранного тикета
  useEffect(() => {
    setCurrent(ticket);
    setSimilar([]);

    // если ещё не классифицировано — классифицируем автоматически
    const run = async () => {
      let t = ticket;
      if (!ticket.category) {
        setClassifying(true);
        try {
          const res = await classifyTicket(ticket.id);
          t = {
            ...ticket,
            ...res,
            status: ticket.status === "new" ? "processing" : ticket.status,
          };
          setCurrent(t);
        } finally {
          setClassifying(false);
        }
      }
      const sim = await fetchSimilar(ticket.id);
      setSimilar(sim);
    };
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket.id]);

  const template = useMemo(
    () =>
      `Уважаемый гражданин, Ваше обращение принято и направлено в ${
        current.responsible_service || "профильную службу"
      }. Ориентировочный срок обработки — 3 рабочих дня. Спасибо за обращение в Pulse 109.`,
    [current.responsible_service]
  );

  const handleApprove = async () => {
    setApproving(true);
    try {
      const updated = await approveTicket(current.id);
      const merged = { ...current, ...updated };
      setCurrent(merged);
      onResolved(merged);
    } finally {
      setApproving(false);
    }
  };

  const conf = current.confidence_score ?? 0;

  return (
    <div className="h-full overflow-y-auto p-6 space-y-5">
      {/* header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white">
          Обращение #{current.id}
        </h2>
        <span
          className="text-xs font-medium px-2.5 py-1 rounded-full"
          style={{
            color: statusColor[current.status],
            backgroundColor: `${statusColor[current.status]}22`,
          }}
        >
          {statusLabel[current.status]}
        </span>
      </div>

      {/* original text */}
      <div className="rounded-lg bg-base/60 border border-line p-4">
        <div className="text-xs text-muted mb-1">
          Текст обращения · {current.source} · {current.region}
        </div>
        <p className="text-sm text-white leading-relaxed">{current.text}</p>
      </div>

      {/* AI classification block */}
      <div className="rounded-lg bg-card border border-line border-l-4 border-l-ai p-4 space-y-4">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">
            AI-классификация
          </span>
          <span className="text-[11px] px-1.5 py-0.5 rounded bg-ai/20 text-ai">
            {classifying ? "анализ…" : "готово"}
          </span>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          <Field label="Категория" value={current.category} />
          <Field label="Подкатегория" value={current.subcategory} />
          <Field label="Адрес" value={current.address} />
          <Field
            label="Приоритет"
            value={priorityLabel[current.priority]}
          />
          <Field
            label="Ответственная служба"
            value={current.responsible_service}
          />
          <Field label="Источник" value={current.source} />
        </div>

        {/* confidence */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-muted">AI Confidence</span>
            <span className="text-2xl font-bold text-white">{conf}%</span>
          </div>
          <div className="h-2.5 rounded-full bg-base overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent to-ai transition-all"
              style={{ width: `${conf}%` }}
            />
          </div>
        </div>

        {/* reasoning */}
        {current.reasoning && (
          <div className="rounded-lg bg-base/60 border border-line p-3">
            <div className="text-xs text-muted mb-1">Обоснование AI</div>
            <p className="text-sm text-muted">{current.reasoning}</p>
          </div>
        )}
      </div>

      {/* priority marker line */}
      <div className="flex items-center gap-2 text-xs text-muted">
        <span
          className="w-2.5 h-2.5 rounded-full"
          style={{ backgroundColor: priorityColor[current.priority] }}
        />
        Приоритет: {priorityLabel[current.priority]}
      </div>

      {/* similar */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-2">
          Похожие обращения
        </h3>
        <SimilarTickets items={similar} />
      </div>

      {/* response template */}
      <div>
        <h3 className="text-sm font-semibold text-white mb-2">
          Шаблон ответа
        </h3>
        <textarea
          defaultValue={template}
          key={template}
          rows={4}
          className="w-full rounded-lg bg-base border border-line p-3 text-sm text-muted focus:outline-none focus:border-accent resize-none"
        />
      </div>

      {/* approve */}
      <button
        onClick={handleApprove}
        disabled={approving || current.status === "resolved"}
        className="w-full py-3 rounded-lg bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold transition-colors"
      >
        {current.status === "resolved"
          ? "✓ Обращение обработано"
          : approving
          ? "Отправка…"
          : "Подтвердить и перенаправить"}
      </button>
    </div>
  );
}
