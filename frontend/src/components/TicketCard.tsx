import type { Ticket } from "../api/types";
import { formatTime, priorityColor, priorityLabel } from "../api/format";

interface Props {
  ticket: Ticket;
  active: boolean;
  onClick: () => void;
}

export default function TicketCard({ ticket, active, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      aria-current={active ? "true" : undefined}
      className={`w-full text-left pr-4 py-2.5 border-b border-gray-100 transition-colors duration-150 ${
        active
          ? "bg-accent-light border-l-2 border-l-accent pl-[14px]"
          : "bg-white hover:bg-gray-50 pl-4"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <span
          className="mt-[5px] w-2 h-2 rounded-full shrink-0"
          style={{ backgroundColor: priorityColor[ticket.priority] }}
          title={`Приоритет: ${priorityLabel[ticket.priority]}`}
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-gray-900 line-clamp-2 leading-snug">
            {ticket.text}
          </p>

          <div className="mt-1.5 flex items-center gap-1.5 text-xs text-gray-400">
            {ticket.category && (
              <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-gray-500">
                {ticket.category}
              </span>
            )}
            <span className="shrink-0">{formatTime(ticket.created_at)}</span>
            <span aria-hidden="true">·</span>
            <span className="shrink-0">{ticket.source}</span>
            <span aria-hidden="true">·</span>
            <span className="truncate">{ticket.region}</span>
          </div>

          {ticket.needs_review && (
            <div className="mt-1.5">
              <span className="inline-block rounded bg-amber-50 px-1.5 py-0.5 text-xs font-medium text-amber-700">
                ⚠ Проверка
              </span>
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
