import type { ReactNode } from "react";
import Navbar from "./Navbar";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="h-screen flex flex-col bg-base text-white overflow-hidden">
      <Navbar />
      <main className="flex-1 overflow-hidden">{children}</main>
    </div>
  );
}
