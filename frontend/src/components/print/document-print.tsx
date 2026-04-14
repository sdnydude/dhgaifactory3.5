import { PrintShell } from "./print-shell";

export interface DocumentPrintProps {
  title: string;
  graphLabel: string;
  reviewRound: number;
  documentText: string;
  generatedAt: string;
}

export function DocumentPrint({
  title,
  graphLabel,
  reviewRound,
  documentText,
  generatedAt,
}: DocumentPrintProps) {
  return (
    <PrintShell
      title={title}
      subtitle={`${graphLabel} · Round ${reviewRound + 1}`}
      generatedAt={generatedAt}
    >
      <div className="prose prose-sm max-w-none text-[#32374A]">
        {documentText.split(/\n{2,}/).map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
    </PrintShell>
  );
}
