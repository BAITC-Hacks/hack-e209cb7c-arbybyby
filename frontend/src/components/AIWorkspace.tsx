import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowLeftIcon,
  CheckIcon,
  DocumentTextIcon,
} from "@heroicons/react/24/outline";
import type { SimilarTicket, Ticket } from "../api/types";
import { approveTicket, classifyTicket, fetchSimilar } from "../api/client";
import { priorityLabel, statusBadge, statusLabel } from "../api/format";
import SimilarTickets from "./SimilarTickets";
import Spinner from "./Spinner";
import { useToast } from "./Toast";

interface Props {
  ticket: Ticket;
  onResolved: (t: Ticket) => void;
  /** Возврат к списку на узких экранах. */
  onBack?: () => void;
}

function Field({ label, value }: { label: string; value: string | null }) {
  return (
    <div>
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      <div className="text-sm font-medium text-gray-900">{value || "—"}</div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section>
      <h3 className="section-label mb-3">{title}</h3>
      {children}
    </section>
  );
}

export default function AIWorkspace({ ticket, onResolved, onBack }: Props) {
  const [current, setCurrent] = useState<Ticket>(ticket);
  const [similar, setSimilar] = useState<SimilarTicket[]>([]);
  const [classifying, setClassifying] = useState(false);
  const [approving, setApproving] = useState(false);
  const toast = useToast();

  // синхронизация при смене выбранного обращения
  useEffect(() => {
    let cancelled = false;
    setCurrent(ticket);
    setSimilar([]);

    const run = async () => {
      // если обращение ещё не классифицировано — классифицируем
      if (!ticket.category) {
        setClassifying(true);
        try {
          const res = await classifyTicket(ticket.id);
          if (cancelled) return;
          setCurrent({
            ...ticket,
            ...res,
            status: ticket.status === "new" ? "processing" : ticket.status,
          });
        } finally {
          if (!cancelled) setClassifying(false);
        }
      }
      const sim = await fetchSimilar(ticket.id);
      if (!cancelled) setSimilar(sim);
    };

    run().catch(() => {
      if (!cancelled) setClassifying(false);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticket.id]);

  const template = useMemo(
    () =>
      `Уважаемый гражданин, Ваше обращение принято и направлено в ${
        current.responsible_service || "профильную службу"
      }. Ориентировочный срок обработки — 3 рабочих дня. Спасибо за обращение в Pulse 109.`,
    [current.responsible_service]
  );

  const done = current.status === "resolved";
  const disabled = approving || done;

  const handleApprove = async () => {
    if (disabled) return;
    setApproving(true);
    try {
      const updated = await approveTicket(current.id);
      const merged = { ...current, ...updated };
      setCurrent(merged);
      onResolved(merged);
      toast("Обращение перенаправлено");
    } catch {
      toast("Не удалось перенаправить обращение");
    } finally {
      setApproving(false);
    }
  };

  // ⌘/Ctrl + Enter — подтвердить и перенаправить
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        handleApprove();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [disabled, current.id]);

  const conf = current.confidence_score ?? 0;

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-4 sm:p-6 max-w-3xl space-y-6">
        {/* Возврат к списку — только на узких экранах */}
        {onBack && (
          <button
            onClick={onBack}
            className="lg:hidden inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors duration-150"
          >
            <ArrowLeftIcon className="h-4 w-4" />
            Назад к списку
          </button>
        )}

        {/* Заголовок */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <DocumentTextIcon className="h-5 w-5 shrink-0 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900 truncate">
              Обращение #{current.id}
            </h2>
          </div>
          <span
            className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded ${
              statusBadge[current.status]
            }`}
          >
            {statusLabel[current.status]}
          </span>
        </div>

        {/* Исходный текст */}
        <div className="bg-gray-50 border border-line rounded-md p-4">
          <p className="text-sm text-gray-700 leading-relaxed">{current.text}</p>
        </div>

        {/* Классификация */}
        <Section title="Автоматическая классификация">
          {classifying ? (
            <div className="flex items-center gap-2 py-4">
              <Spinner />
              <span className="text-sm text-gray-400">Анализ обращения…</span>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Категория" value={current.category} />
                <Field label="Подкатегория" value={current.subcategory} />
                <Field label="Адрес" value={current.address} />
                <Field
                  label="Ответственная служба"
                  value={current.responsible_service}
                />
                <Field label="Приоритет" value={priorityLabel[current.priority]} />
                <Field label="Источник" value={current.source} />
              </div>

              <p className="text-xs text-gray-400 mt-4">
                Определено автоматически. Проверьте и скорректируйте при
                необходимости.
              </p>

              {/* Уверенность модели */}
              <div className="mt-4">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-gray-400">Уверенность модели</span>
                  <span className="text-sm font-semibold text-gray-700 tabular-nums">
                    {conf}%
                  </span>
                </div>
                <div
                  className="h-1.5 rounded-full bg-gray-200 overflow-hidden"
                  role="progressbar"
                  aria-valuenow={conf}
                  aria-valuemin={0}
                  aria-valuemax={100}
                >
                  <div
                    className="h-full rounded-full bg-accent transition-all duration-150"
                    style={{ width: `${conf}%` }}
                  />
                </div>
              </div>

              {current.reasoning && (
                <p className="text-xs text-gray-500 italic mt-3">
                  {current.reasoning}
                </p>
              )}
            </>
          )}
        </Section>

        {/* Похожие обращения */}
        <Section title="Похожие обращения">
          <SimilarTickets items={similar} />
        </Section>

        {/* Шаблон ответа */}
        <Section title="Шаблон ответа">
          <textarea
            key={template}
            defaultValue={template}
            rows={4}
            className="w-full border border-line rounded-md p-3 text-sm text-gray-900 bg-white resize-y focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-colors duration-150"
          />
        </Section>

        {/* Подтверждение */}
        <div className="flex items-center gap-3 pt-1">
          <button
            onClick={handleApprove}
            disabled={disabled}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-accent text-white text-sm font-medium rounded-md hover:bg-accent-hover disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-150"
          >
            {approving ? (
              <Spinner className="h-4 w-4 text-white" />
            ) : (
              <CheckIcon className="h-4 w-4" />
            )}
            {done ? "Обращение обработано" : "Подтвердить и перенаправить"}
          </button>
          {!done && (
            <span className="hidden sm:inline text-xs text-gray-400">
              ⌘ Enter
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
