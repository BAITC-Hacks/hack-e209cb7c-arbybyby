import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { CheckCircleIcon } from "@heroicons/react/24/outline";

interface ToastItem {
  id: number;
  message: string;
}

const ToastContext = createContext<(message: string) => void>(() => {});

/** Показать короткое уведомление. Замена alert(). */
export function useToast() {
  return useContext(ToastContext);
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const timers = useRef<number[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const push = useCallback(
    (message: string) => {
      const id = nextId.current++;
      setItems((prev) => [...prev, { id, message }]);
      const timer = window.setTimeout(() => dismiss(id), 3500);
      timers.current.push(timer);
    },
    [dismiss]
  );

  useEffect(() => {
    const pending = timers.current;
    return () => pending.forEach(window.clearTimeout);
  }, []);

  const value = useMemo(() => push, [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 left-4 sm:left-auto z-50 flex flex-col items-stretch sm:items-end gap-2"
        role="status"
        aria-live="polite"
      >
        {items.map((t) => (
          <div
            key={t.id}
            className="pointer-events-auto flex items-center gap-2 rounded-md border border-line bg-white px-3 py-2 shadow-sm"
          >
            <CheckCircleIcon className="h-4 w-4 shrink-0 text-green-600" />
            <span className="text-sm text-gray-900">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="ml-2 text-xs text-gray-400 hover:text-gray-600 transition-colors duration-150"
              aria-label="Закрыть уведомление"
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
