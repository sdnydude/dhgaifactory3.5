import type { ReactNode } from "react";

export interface PrintShellProps {
  title: string;
  subtitle?: string;
  generatedAt: string;
  children: ReactNode;
}

export function PrintShell({ title, subtitle, generatedAt, children }: PrintShellProps) {
  return (
    <article data-print-ready="true">
      <header className="mb-8 border-b border-[#E4E4E7] pb-4">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[#71717A]">
          Digital Harmony Group · CME
        </p>
        <h1 className="mt-2 font-[Inter] text-2xl font-semibold text-[#32374A]">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-[#52525B]">{subtitle}</p>}
        <p className="mt-4 text-[10px] text-[#A1A1AA]">Generated {generatedAt}</p>
      </header>
      {children}
      <footer className="mt-12 border-t border-[#E4E4E7] pt-3 text-[10px] text-[#A1A1AA]">
        AI-assisted output · verify against source material · not legal or medical advice
      </footer>
    </article>
  );
}
