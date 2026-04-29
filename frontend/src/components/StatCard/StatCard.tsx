import { useTranslation } from "react-i18next";
import "./StatCard.css";

interface StatCardProps {
  labelKey: string; // przekazujemy klucz do tłumaczenia, np. "stats.active"
  value: string | number;
  variant?: "light" | "dark";
}

export default function StatCard({ labelKey, value, variant = "light" }: StatCardProps) {
  const { t } = useTranslation();

  return (
    <div className={`stat-card ${variant}`}>
      <span className="stat-label">{t(labelKey)}</span>
      <h2 className="stat-value">{typeof value === "number" ? value.toLocaleString() : value}</h2>
    </div>
  );
}