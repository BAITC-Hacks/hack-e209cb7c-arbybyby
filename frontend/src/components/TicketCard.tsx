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
      className={`w-full text-left pr-4 py-3 border-b border-line-soft transition-colors duration-150 ${
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
            <span>{formatTime(ticket.created_at)}</span>
            <span aria-hidden="true">·</span>
            <span>{ticket.source}</span>
            <span aria-hidden="true">·</span>
            <span className="truncate">{ticket.region}</span>
          </div>
        </div>
      </div>
    </button>
  );
}
