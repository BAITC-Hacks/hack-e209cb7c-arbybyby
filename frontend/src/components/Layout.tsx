import type { ReactNode } from "react";
import Navbar from "./Navbar";
import { ToastProvider } from "./Toast";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <ToastProvider>
      <div className="h-screen flex flex-col bg-page text-gray-900">
        <Navbar />
        {/* контент скроллится под фиксированным навбаром */}
        <main className="flex-1 min-h-0 pt-14">{children}</main>
      </div>
    </ToastProvider>
  );
}
