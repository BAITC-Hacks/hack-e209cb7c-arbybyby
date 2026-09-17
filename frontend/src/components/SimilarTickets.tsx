import type { SimilarTicket } from "../api/types";

export default function SimilarTickets({ items }: { items: SimilarTicket[] }) {
  if (!items.length) {
    return <p className="text-sm text-muted">Похожих обращений не найдено.</p>;
  }

  return (
    <div className="grid gap-2 sm:grid-cols-3">
      {items.map((s) => (
        <div
          key={s.id}
          className="rounded-lg border border-line bg-base/50 p-3 flex flex-col gap-2"
        >
          <p className="text-xs text-muted line-clamp-3 leading-snug">{s.text}</p>
          <div className="flex items-center justify-between mt-auto">
            <span className="text-[11px] text-muted">{s.category}</span>
            <span className="text-[11px] font-medium px-1.5 py-0.5 rounded bg-ai/20 text-ai">
              {s.similarity_score}% схожесть
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
