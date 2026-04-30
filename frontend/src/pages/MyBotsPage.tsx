import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import StatCard from "../components/StatCard/StatCard";
import "./MyBotsPage.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type ApiStatus = {
  botRunning: boolean;
  categoriesCount: number;
  historyEntriesCount: number;
};

export default function MyBotsPage() {
  const { t } = useTranslation();

  const [activeBots, setActiveBots] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [statusText, setStatusText] = useState("Loading backend status...");

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/status`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data: ApiStatus = await response.json();
        setActiveBots(data.botRunning ? 1 : 0);
        setTotalItems(data.historyEntriesCount);
        setStatusText(`Connected. Categories: ${data.categoriesCount}`);
      } catch {
        setStatusText("Backend unavailable. Start FastAPI on port 8000.");
      }
    };

    fetchStatus();
    const intervalId = window.setInterval(fetchStatus, 10_000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <section className="my-bots-page">
      <div className="page-header-row">
        <div className="title-section">
          <p className="eyebrow">{t("page.eyebrow")}</p>
          <h1 className="my-bots-title">{t("page.myBotsTitle")}</h1>
          <p className="my-bots-desc">{t("page.myBotsDesc")}</p>
          <p className="api-status">{statusText}</p>
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