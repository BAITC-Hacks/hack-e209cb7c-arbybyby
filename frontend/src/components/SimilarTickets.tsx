import type { SimilarTicket } from "../api/types";

export default function SimilarTickets({ items }: { items: SimilarTicket[] }) {
  if (!items.length) {
    return (
      <p className="text-sm text-gray-400 py-2">Похожих обращений не найдено</p>
    );
  }

  return (
    <ul>
      {items.map((s) => (
        <li
          key={s.id}
          className="flex items-center gap-3 py-2 border-b border-line-soft last:border-b-0"
        >
          <span className="text-sm text-gray-600 truncate flex-1 min-w-0">
            {s.text}
          </span>
          <span className="text-xs text-gray-400 shrink-0 tabular-nums">
            {s.similarity_score}%
          </span>
        </li>
      ))}
    </ul>
  );
}
