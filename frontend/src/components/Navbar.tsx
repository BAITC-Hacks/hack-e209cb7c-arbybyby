import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline";

const TABS = [
  { to: "/", label: "Оператор", end: true },
  { to: "/dashboard", label: "Ситуационный центр", end: false },
];

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();

  // закрываем меню при переходе между разделами
  useEffect(() => setMenuOpen(false), [pathname]);

  const desktopTab = ({ isActive }: { isActive: boolean }) =>
    `relative h-14 inline-flex items-center px-1 text-sm font-medium transition-colors duration-150 ${
      isActive
        ? "text-accent after:absolute after:inset-x-0 after:bottom-0 after:h-0.5 after:bg-accent"
        : "text-gray-500 hover:text-gray-700"
    }`;

  const mobileTab = ({ isActive }: { isActive: boolean }) =>
    `block px-4 py-2.5 text-sm font-medium transition-colors duration-150 ${
      isActive
        ? "bg-accent-light text-accent border-l-2 border-accent"
        : "text-gray-500 hover:bg-gray-50 hover:text-gray-700 border-l-2 border-transparent"
    }`;

  return (
    <header className="fixed inset-x-0 top-0 z-40 h-14 border-b border-line bg-white">
      <nav className="h-full flex items-center justify-between px-4 sm:px-6">
        {/* Слева: словесный знак */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-sm font-bold text-gray-900">AURA</span>
          <span className="text-gray-300" aria-hidden="true">
            |
          </span>
          <span className="text-sm text-gray-500">Pulse 109</span>
        </div>

        {/* Центр: табы (десктоп) */}
        <div className="hidden sm:flex items-center gap-6 absolute left-1/2 -translate-x-1/2">
          {TABS.map((t) => (
            <NavLink key={t.to} to={t.to} end={t.end} className={desktopTab}>
              {t.label}
            </NavLink>
          ))}
        </div>

        {/* Справа: пользователь + гамбургер на мобильных */}
        <div className="flex items-center gap-3">
          <span className="hidden sm:inline text-xs text-gray-400">
            arbybyby
          </span>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            className="sm:hidden -mr-1 p-1.5 rounded-md text-gray-500 hover:bg-gray-50 hover:text-gray-700 transition-colors duration-150"
            aria-label={menuOpen ? "Закрыть меню" : "Открыть меню"}
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <XMarkIcon className="h-5 w-5" />
            ) : (
              <Bars3Icon className="h-5 w-5" />
            )}
          </button>
        </div>
      </nav>

      {/* Мобильное меню */}
      {menuOpen && (
        <div className="sm:hidden border-b border-line bg-white shadow-sm">
          {TABS.map((t) => (
            <NavLink key={t.to} to={t.to} end={t.end} className={mobileTab}>
              {t.label}
            </NavLink>
          ))}
          <div className="px-4 py-2.5 text-xs text-gray-400 border-t border-line-soft">
            arbybyby
          </div>
        </div>
      )}
    </header>
  );
}
