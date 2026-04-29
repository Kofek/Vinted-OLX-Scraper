import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react"; 
import StatCard from "../components/StatCard/StatCard";
import "./MyBotsPage.css";

export default function MyBotsPage() {
  const { t } = useTranslation();

  const [activeBots, setActiveBots] = useState(0); 
  const [totalItems, setTotalItems] = useState(0);

  return (
    <section className="my-bots-page">
      <div className="page-header-row">
        <div className="title-section">
          <p className="eyebrow">{t("page.eyebrow")}</p>
          <h1 className="my-bots-title">{t("page.myBotsTitle")}</h1>
          <p className="my-bots-desc">{t("page.myBotsDesc")}</p>
        </div>
        <div className="stats-grid">
          <StatCard 
            labelKey="stats.activeCount" 
            value={activeBots < 10 ? `0${activeBots}` : activeBots}
            variant="light" 
          />
          <StatCard 
            labelKey="stats.totalItems" 
            value={totalItems}
            variant="dark" 
          />
        </div>
      </div>
    </section>
  );
}