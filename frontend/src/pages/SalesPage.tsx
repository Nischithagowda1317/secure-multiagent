import { useEffect, useState } from "react";
import { get } from "../api";
import { BarList, DataTable, ErrorBox, Loading, Panel } from "../components/UI";

interface SalesData { region: Array<Record<string, unknown>>; category: Array<Record<string, unknown>> }
export default function SalesPage() {
  const [data, setData] = useState<SalesData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => { get<SalesData>("/dashboard/sales").then(setData).catch((err: Error) => setError(err.message)); }, []);
  if (error) return <ErrorBox message={error} />;
  if (!data) return <Loading label="Loading sales analytics" />;
  return <div className="page-stack"><div className="page-title"><div><span className="eyebrow">Sales Analytics Agent</span><h1>Sales performance</h1><p>Revenue, profit, order volume, regions, categories, channels, and discount controls.</p></div></div><div className="two-column"><Panel title="Sales by region"><BarList items={data.region} valueKey="sales_usd" labelKey="region" /></Panel><Panel title="Profit by category"><BarList items={data.category} valueKey="profit_usd" labelKey="product_category" /></Panel></div><Panel title="Regional detail"><DataTable rows={data.region} /></Panel><Panel title="Category detail"><DataTable rows={data.category} /></Panel></div>;
}
