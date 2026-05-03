import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import StatCard from "../components/StatCard/StatCard";
import "./MyBotsPage.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

function parseIsoTimestamp(timestamp: string | null): Date | null {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? null : date;
}

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
  const { t, i18n } = useTranslation();

  const [bots, setBots] = useState<BotItem[]>([]);
  const [activeBots, setActiveBots] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [fetchState, setFetchState] = useState<"loading" | "ok" | "error">("loading");
  const [fetchedBotsOnPageCount, setFetchedBotsOnPageCount] = useState(0);

  const formatLastActivityLabel = (isoUtc: string | null): string => {
    const dateUtc = parseIsoTimestamp(isoUtc);
    if (!dateUtc) return "—";

    const diffSec = Math.round((Date.now() - dateUtc.getTime()) / 1000);
    if (diffSec < 0) {
      return t("time.justNow");
    }
    if (diffSec < 60) {
      return t("time.justNow");
    }

    const formatter = new Intl.RelativeTimeFormat(i18n.language, { numeric: "auto" });

    if (diffSec < 3600) {
      return formatter.format(-Math.floor(diffSec / 60), "minute");
    }
    if (diffSec < 86400) {
      return formatter.format(-Math.floor(diffSec / 3600), "hour");
    }
    if (diffSec < 604800) {
      return formatter.format(-Math.floor(diffSec / 86400), "day");
    }
    if (diffSec < 2629800) {
      return formatter.format(-Math.floor(diffSec / 604800), "week");
    }
    if (diffSec < 31557600) {
      return formatter.format(-Math.floor(diffSec / 2629800), "month");
    }
    return formatter.format(-Math.floor(diffSec / 31557600), "year");
  };

  useEffect(() => {
    const fetchBots = async () => {
      setFetchState("loading");
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
        setFetchedBotsOnPageCount(data.items.length);
        setFetchState("ok");
      } 
      catch {
        setFetchedBotsOnPageCount(0);
        setFetchState("error");
      }
    };

    fetchBots();
    const intervalId = window.setInterval(fetchBots, 10_000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, [currentPage, i18n.language]);

  return (
    <section className="my-bots-page">
      <div className="page-header-row">
        <div className="title-section">
          <p className="eyebrow">{t("page.eyebrow")}</p>
          <h1 className="my-bots-title">{t("page.myBotsTitle")}</h1>
          <p className="my-bots-desc">{t("page.myBotsDesc")}</p>
          <p className="api-status">
            {fetchState === "loading"
              ? t("myBots.fetch.loading")
              : fetchState === "error"
                ? t("myBots.fetch.error")
                : t("myBots.fetch.ok", { count: fetchedBotsOnPageCount })}
          </p>
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
        {bots.map((bot) => {
          const isRunning = bot.runtime.status === "running";

          const lastActivity = isRunning
            ? formatLastActivityLabel(bot.runtime.lastHeartbeatUtc)
            : formatLastActivityLabel(bot.runtime.lastStoppedUtc ?? bot.runtime.lastHeartbeatUtc);
          const success =
            bot.runtime.successRate == null ? "—" : `${Number(bot.runtime.successRate).toFixed(1)}%`;

          return (
            <article
              key={bot.id}
              className={`bot-tile bot-tile--${isRunning ? "running" : "paused"}`}
            >
              <div className="bot-tile-accent" />
              <div className="bot-tile-inner">
                <header className="bot-tile-header">
                  <h3 className="bot-tile-name">{bot.name}</h3>
                  <span
                    className={`bot-tile-pill bot-tile-pill--${isRunning ? "running" : "paused"}`}
                    aria-label={isRunning ? t("myBots.status.running") : t("myBots.status.paused")}
                  >
                    <span className="bot-tile-dot" aria-hidden />
                    {isRunning ? t("myBots.status.running") : t("myBots.status.paused")}
                  </span>
                </header>

                <dl className="bot-tile-rows">
                  <div className="bot-tile-row">
                    <dt>{t("myBots.labels.lastActivity")}</dt>
                    <dd>{lastActivity}</dd>
                  </div>
                  <div className="bot-tile-row">
                    <dt>{t("myBots.labels.itemsFound")}</dt>
                    <dd>{bot.runtime.itemsFound.toLocaleString(i18n.language)}</dd>
                  </div>
                  <div className="bot-tile-row bot-tile-row--last">
                    <dt>{t("myBots.labels.successRate")}</dt>
                    <dd>{success}</dd>
                  </div>
                </dl>

                <footer className="bot-tile-actions">
                  <button type="button" className={`bot-tile-main-btn bot-tile-main-btn--${isRunning ? "pause" : "resume"}`}>
                    {isRunning ? t("myBots.actions.pause") : t("myBots.actions.resume")}
                  </button>
                  <button type="button" className="bot-tile-icon-btn" aria-label={t("myBots.actions.editAria")}>
                    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                      <path
                        fill="currentColor"
                        d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 2.83-2.83z"
                      />
                    </svg>
                  </button>
                </footer>
              </div>
            </article>
          );
        })}
      </div>

      {bots.length === 0 ? <p className="empty-state">{t("myBots.empty")}</p> : null}

      {totalPages > 1 ? (
        <div className="pagination">
          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
            disabled={currentPage <= 1}
          >
            {t("myBots.pagination.prev")}
          </button>
          <span>
            {t("myBots.pagination.page", { current: currentPage, total: totalPages })}
          </span>
          <button
            type="button"
            onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
            disabled={currentPage >= totalPages}
          >
            {t("myBots.pagination.next")}
          </button>
        </div>
      ) : null}
    </section>
  );
}