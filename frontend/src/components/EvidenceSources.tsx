import type { SourceReference } from "../types";

export default function EvidenceSources({ sources }: { sources: SourceReference[] }) {
  return (
    <div className="source-list">
      {sources.map((source, index) => (
        <div key={`${source.source_id}-${index}`}>
          <strong>{source.title}</strong>
          <span>{source.source_type}{source.section ? ` · ${source.section}` : ""}</span>
          {typeof source.score === "number" && Number.isFinite(source.score) && (
            <small>Similarity {source.score.toFixed(3)}</small>
          )}
        </div>
      ))}
    </div>
  );
}
