import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import StatCard from "../components/StatCard/StatCard";
import "./MyBotsPage.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

type BotRuntime = {
  status: string;
  lastHeartbeatUtc: string | null;
  lastStartedUtc: string | null;
  lastStoppedUtc: string | null;
  itemsFound: number;
  successRate: number | null;
  lastError: string | null;
};

type BotItem = {
  id: string;
  name: string;
  source: string;
  urlsOlx: string[];
  urlsVinted: string[];
  webhookUrl: string | null;
  enabled: boolean;
  promptText: string;
  createdAtUtc: string | null;
  updatedAtUtc: string | null;
  runtime: BotRuntime;
};

type BotsResponse = {
  items: BotItem[];
  pagination: {
    page: number;
    pageSize: number;
    totalBots: number;
    totalPages: number;
    hasPrev: boolean;
    hasNext: boolean;
  };
  summary: {
    activeBotsCount: number;
    totalItemsFound: number;
  };
  serverTimeUtc: string;
};

export default function MyBotsPage() {
  const { t } = useTranslation();

  const [bots, setBots] = useState<BotItem[]>([]);
  const [activeBots, setActiveBots] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [statusText, setStatusText] = useState("Loading bots...");

  useEffect(() => {
    const fetchBots = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/bots?page=${currentPage}&pageSize=6`);
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data: BotsResponse = await response.json();
        setBots(data.items ?? []);
        setActiveBots(data.summary?.activeBotsCount ?? 0);
        setTotalItems(data.summary?.totalItemsFound ?? 0);
        setCurrentPage(data.pagination?.page ?? 1);
        setTotalPages(data.pagination?.totalPages ?? 1);
        setStatusText(`Connected. Showing ${data.items.length} bots.`);
      } 
      catch {
        setStatusText("Backend unavailable. Start FastAPI on port 8000 and check /api/bots.");
      }
    };

    fetchBots();
    const intervalId = window.setInterval(fetchBots, 10_000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [currentPage]);

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

      <div className="bots-grid">
        {bots.map((bot) => (
          <article key={bot.id} className="bot-card">
            <div className="bot-card-top">
              <p className="bot-source">{bot.source.toUpperCase()}</p>
              <span className={`bot-status ${bot.runtime.status === "running" ? "running" : "paused"}`}>
                {bot.runtime.status}
              </span>
            </div>
            <h3 className="bot-name">{bot.name}</h3>
            <p className="bot-meta">Items found: {bot.runtime.itemsFound}</p>
            <p className="bot-meta">
              Success rate: {bot.runtime.successRate == null ? "-" : `${bot.runtime.successRate}%`}
            </p>
            <p className="bot-meta">OLX links: {bot.urlsOlx.length}</p>
            <p className="bot-meta">Vinted links: {bot.urlsVinted.length}</p>
            <p className="bot-meta">Webhook: {bot.webhookUrl ? "yes" : "no"}</p>
          </article>
        ))}
      </div>

      {bots.length === 0 ? <p className="empty-state">No bots to display.</p> : null}

      {totalPages > 1 ? (
        <div className="pagination">
          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage <= 1}
          >
            Prev
          </button>
          <span>
            Page {currentPage} / {totalPages}
          </span>
          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage >= totalPages}
          >
            Next
          </button>
        </div>
      ) : null}
    </section>
  );
}