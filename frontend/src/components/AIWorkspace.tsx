import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  ArrowLeftIcon,
  CheckIcon,
  DocumentTextIcon,
} from "@heroicons/react/24/outline";
import type { CategoryOption, SimilarTicket, Ticket } from "../api/types";
import {
  approveTicket,
  classifyTicket,
  correctTicket,
  fetchSimilar,
} from "../api/client";
import { CATEGORIES } from "../api/catalog";
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
    <div className="min-w-0">
      <div className="text-xs text-gray-400 mb-0.5">{label}</div>
      <div className="text-sm font-medium text-gray-900 truncate" title={value || undefined}>
        {value || "—"}
      </div>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="bg-white border border-line rounded-md p-4 sm:p-5">
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
  const [correcting, setCorrecting] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
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

  /** Оператор выбрал категорию — вручную или из предложенных вариантов. */
  const applyCategory = async (option: CategoryOption | string) => {
    if (correcting) return;
    const category = typeof option === "string" ? option : option.category;
    setCorrecting(true);
    setDropdownOpen(false);
    try {
      const updated = await correctTicket(current.id, category, current.category);
      const merged: Ticket = { ...current, ...updated };
      // подкатегорию и службу берём из выбранного варианта, если он их принёс
      if (typeof option !== "string") {
        merged.subcategory = option.subcategory;
        merged.responsible_service = option.responsible_service;
      }
      merged.needs_review = false;
      merged.alternatives = [];
      setCurrent(merged);
      onResolved(merged);
      toast("Коррекция сохранена. Будет использована для дообучения модели.");
    } catch {
      toast("Не удалось сохранить коррекцию");
    } finally {
      setCorrecting(false);
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
    /* Колонка: прокручивается только содержимое, кнопка подтверждения
       остаётся прижатой к низу панели и видна без прокрутки. */
    <div className="h-full flex flex-col">
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-4">
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

          {/* Заголовок — над карточками, на фоне страницы */}
          <div className="flex items-center justify-between gap-3 pt-0.5 pb-1">
            <div className="flex items-center gap-2 min-w-0">
              <DocumentTextIcon className="h-5 w-5 shrink-0 text-gray-400" />
              <h2 className="text-lg font-semibold text-gray-900 truncate">
                Обращение #{current.id}
              </h2>
            </div>
            {current.needs_review ? (
              <span className="shrink-0 text-xs font-medium px-2 py-0.5 rounded bg-amber-50 text-amber-700">
                Требует проверки
              </span>
            ) : (
              <span
                className={`shrink-0 text-xs font-medium px-2 py-0.5 rounded ${
                  statusBadge[current.status]
                }`}
              >
                {statusLabel[current.status]}
              </span>
            )}
          </div>

          {/* Исходный текст */}
          <div className="bg-white border border-line rounded-md p-4 sm:p-5">
            <p className="text-sm text-gray-700 leading-relaxed">
              {current.text}
            </p>
          </div>

          {/* Классификация */}
          <Section title="Автоматическая классификация">
            {classifying ? (
              <div className="flex items-center gap-2 py-3">
                <Spinner />
                <span className="text-sm text-gray-400">Анализ обращения…</span>
              </div>
            ) : (
              <>
                {current.needs_review &&
                (current.alternatives?.length ?? 0) > 0 ? (
                  /* Уверенности мало — категорию выбирает оператор */
                  <div>
                    <div className="text-xs text-gray-400 mb-1.5">
                      Категория определена неуверенно. Выберите подходящую:
                    </div>
                    <div className="space-y-1.5">
                      {current.alternatives?.map((option) => (
                        <button
                          key={`${option.category}-${option.subcategory}`}
                          onClick={() => applyCategory(option)}
                          disabled={correcting}
                          className="w-full flex items-center justify-between gap-3 px-3 py-1.5 text-left bg-white border border-line rounded-md hover:bg-accent-light hover:border-accent disabled:opacity-50 transition-colors duration-150"
                        >
                          <span className="min-w-0">
                            <span className="block text-sm font-medium text-gray-900 truncate">
                              {option.category} — {option.subcategory}
                            </span>
                            <span className="block text-xs text-gray-400 truncate">
                              {option.responsible_service}
                            </span>
                          </span>
                          <span className="shrink-0 text-xs text-gray-400 tabular-nums">
                            {option.confidence}%
                          </span>
                        </button>
                      ))}
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4 mt-4">
                      <Field label="Адрес" value={current.address} />
                      <Field
                        label="Приоритет"
                        value={priorityLabel[current.priority]}
                      />
                      <Field label="Источник" value={current.source} />
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs text-gray-400">Категория</span>
                        <div className="relative">
                          <button
                            onClick={() => setDropdownOpen((v) => !v)}
                            disabled={correcting}
                            className="text-xs text-gray-400 hover:text-gray-600 underline underline-offset-2 disabled:opacity-50 transition-colors duration-150"
                          >
                            Исправить
                          </button>
                          {dropdownOpen && (
                            <div className="absolute left-0 top-full mt-1 z-20 w-44 bg-white border border-line rounded-md shadow-sm py-1">
                              {CATEGORIES.map((name) => (
                                <button
                                  key={name}
                                  onClick={() => applyCategory(name)}
                                  className="w-full text-left px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors duration-150"
                                >
                                  {name}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {current.category || "—"}
                      </div>
                    </div>
                    <Field label="Подкатегория" value={current.subcategory} />
                    <Field label="Адрес" value={current.address} />
                    <Field
                      label="Ответственная служба"
                      value={current.responsible_service}
                    />
                    <Field
                      label="Приоритет"
                      value={priorityLabel[current.priority]}
                    />
                    <Field label="Источник" value={current.source} />
                  </div>
                )}

                {/* Уверенность модели и её обоснование — одной строкой,
                    на узких экранах обоснование переносится вниз. */}
                <div className="mt-4 pt-4 border-t border-line-soft flex flex-wrap items-center gap-x-4 gap-y-2">
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-gray-400">Уверенность:</span>
                    <span className="text-xs font-semibold text-gray-700 tabular-nums">
                      {conf}%
                    </span>
                    <div
                      className="h-1.5 w-20 rounded-full bg-gray-200 overflow-hidden"
                      role="progressbar"
                      aria-label="Уверенность модели"
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
                    <p
                      className="flex-1 basis-48 min-w-0 text-xs italic text-gray-500 line-clamp-2"
                      title={current.reasoning}
                    >
                      {current.reasoning}
                    </p>
                  )}
                </div>
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
              rows={3}
              className="w-full border border-line rounded-md p-3 text-sm text-gray-900 bg-white resize-y focus:outline-none focus:ring-1 focus:ring-accent focus:border-accent transition-colors duration-150"
            />
          </Section>
        </div>
      </div>

      {/* Подтверждение — прижато к низу панели */}
      <div className="shrink-0 border-t border-line bg-white px-4 sm:px-6 py-3.5">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
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
