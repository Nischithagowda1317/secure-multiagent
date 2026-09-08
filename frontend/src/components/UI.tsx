import type { ReactNode } from "react";

export function Panel({ title, subtitle, actions, children, className = "" }: {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`panel ${className}`}>
      {(title || actions) && (
        <header className="panel-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p>{subtitle}</p>}
          </div>
          {actions && <div className="panel-actions">{actions}</div>}
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function StatCard({ label, value, helper, tone = "default" }: {
  label: string;
  value: ReactNode;
  helper?: string;
  tone?: "default" | "good" | "warn" | "danger";
}) {
  return (
    <div className={`stat-card ${tone}`}>
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      {helper && <span className="stat-helper">{helper}</span>}
    </div>
  );
}

export function Badge({ children, tone = "neutral" }: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn" | "danger" | "info";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return <div className="loading"><span className="spinner" />{label}</div>;
}

export function ErrorBox({ message }: { message: string }) {
  return <div className="error-box">{message}</div>;
}

export function Empty({ message }: { message: string }) {
  return <div className="empty-state">{message}</div>;
}

export function Progress({ value, label }: { value: number; label?: string }) {
  const bounded = Math.max(0, Math.min(100, value));
  return (
    <div className="progress-wrap">
      <div className="progress-label"><span>{label}</span><strong>{bounded.toFixed(0)}%</strong></div>
      <div className="progress-track"><span style={{ width: `${bounded}%` }} /></div>
    </div>
  );
}

export function DataTable({ rows, maxRows = 20 }: { rows: Array<Record<string, unknown>>; maxRows?: number }) {
  if (!rows.length) return <Empty message="No records found." />;
  const columns = Object.keys(rows[0]).slice(0, 10);
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column}>{humanize(column)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, maxRows).map((row, index) => (
            <tr key={index}>
              {columns.map((column) => <td key={column}>{formatCell(row[column])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BarList({ items, valueKey, labelKey }: {
  items: Array<Record<string, unknown>>;
  valueKey: string;
  labelKey: string;
}) {
  const values = items.map((item) => Number(item[valueKey] ?? 0));
  const max = Math.max(...values, 1);
  return (
    <div className="bar-list">
      {items.map((item, index) => {
        const value = Number(item[valueKey] ?? 0);
        return (
          <div className="bar-item" key={index}>
            <div className="bar-row"><span>{String(item[labelKey] ?? "Unknown")}</span><strong>{formatNumber(value)}</strong></div>
            <div className="bar-track"><span style={{ width: `${(value / max) * 100}%` }} /></div>
          </div>
        );
      })}
    </div>
  );
}

export function humanize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value);
}

export function formatMoney(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function formatCell(value: unknown): ReactNode {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return formatNumber(value);
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
