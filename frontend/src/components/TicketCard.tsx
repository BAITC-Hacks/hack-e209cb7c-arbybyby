import type { Ticket } from "../api/types";
import { formatTime, priorityColor } from "../api/format";

interface Props {
  ticket: Ticket;
  active: boolean;
  onClick: () => void;
}

export default function TicketCard({ ticket, active, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3 rounded-lg border transition-colors ${
        active
          ? "border-accent bg-accent/10"
          : "border-line bg-card hover:border-line/80 hover:bg-line/20"
      }`}
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-1.5 w-2.5 h-2.5 rounded-full shrink-0"
          style={{ backgroundColor: priorityColor[ticket.priority] }}
          title={ticket.priority}
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-white line-clamp-2 leading-snug">
            {ticket.text}
          </p>
          <div className="mt-2 flex items-center gap-2 text-xs text-muted">
            <span>{formatTime(ticket.created_at)}</span>
            <span className="text-line">·</span>
            <span className="px-1.5 py-0.5 rounded bg-line/40 text-muted">
              {ticket.source}
            </span>
            <span className="text-line">·</span>
            <span>{ticket.region}</span>
          </div>
        </div>
      </div>
    </button>
  );
}
