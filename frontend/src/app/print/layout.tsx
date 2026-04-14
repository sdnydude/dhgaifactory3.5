import type { ReactNode } from "react";
import "@/app/globals.css";
import "./print.css";

export const dynamic = "force-dynamic";

export default function PrintLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-white text-[#32374A] antialiased">
        <main className="mx-auto max-w-[7.5in] px-[0.75in] py-[0.5in]">{children}</main>
      </body>
    </html>
  );
}
