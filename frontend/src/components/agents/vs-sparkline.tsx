interface VsSparklineProps {
  scores: number[];
  maxScore?: number;
}

export function VsSparkline({ scores, maxScore = 1 }: VsSparklineProps) {
  if (scores.length === 0) return null;

  return (
    <div className="flex items-end gap-0.5 h-4">
      {scores
        .sort((a, b) => b - a)
        .map((score, i) => (
          <div
            key={i}
            className="w-2 rounded-sm"
            style={{
              height: `${(score / maxScore) * 100}%`,
              backgroundColor:
                i === 0
                  ? "var(--dhg-border-focus, #663399)"
                  : "var(--dhg-text-placeholder, #A1A1AA)",
              opacity: i === 0 ? 1 : 0.5,
            }}
          />
        ))}
    </div>
  );
}
