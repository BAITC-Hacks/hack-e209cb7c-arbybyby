import { NavLink } from "react-router-dom";

export default function Navbar() {
  const tabClass = ({ isActive }: { isActive: boolean }) =>
    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? "bg-accent text-white"
        : "text-muted hover:text-white hover:bg-line/50"
    }`;

  return (
    <nav className="h-16 shrink-0 border-b border-line bg-card/60 backdrop-blur flex items-center justify-between px-6">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-accent to-ai flex items-center justify-center font-bold text-white">
            A
          </div>
          <span className="text-xl font-bold tracking-tight text-accent">
            AURA
          </span>
        </div>

        <div className="flex items-center gap-2">
          <NavLink to="/" end className={tabClass}>
            Оператор
          </NavLink>
          <NavLink to="/dashboard" className={tabClass}>
            Ситуационный центр
          </NavLink>
        </div>
      </div>

      <div className="text-sm text-muted">
        <span className="text-white font-medium">Pulse 109</span>
        <span className="mx-2 text-line">|</span>
        <span>arbybyby</span>
      </div>
    </nav>
  );
}
