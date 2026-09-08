import { DataTable, humanize } from "./UI";

export default function JsonData({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span>—</span>;
  if (Array.isArray(value)) {
    if (!value.length) return <span>None</span>;
    if (typeof value[0] === "object" && value[0] !== null) {
      return <DataTable rows={value as Array<Record<string, unknown>>} />;
    }
    return <div className="tag-list">{value.map((item, index) => <span key={index}>{String(item)}</span>)}</div>;
  }
  if (typeof value === "object") {
    return (
      <div className="key-grid">
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div className="key-row" key={key}>
            <span>{humanize(key)}</span>
            <div><JsonData value={item} /></div>
          </div>
        ))}
      </div>
    );
  }
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  return <span>{String(value)}</span>;
}
