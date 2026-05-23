import { useState } from "react";
import { useTranslation } from "react-i18next";
import { pauseBot, resumeBot } from "../api/bots";
import StatCard from "../components/StatCard/StatCard";
import BotTile from "../components/BotTile/BotTile";
import CreateBotModal from "../components/CreateBotModal/CreateBotModal";
import EditBotModal from "../components/EditBotModal/EditBotModal";
import { useBotsList } from "../hooks/useBotsList";
import type { BotItem } from "../types/bots";
import "./MyBotsPage.css";

export default function MyBotsPage() {
  const { t } = useTranslation();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingBot, setEditingBot] = useState<BotItem | null>(null);
  const [togglingBotId, setTogglingBotId] = useState<string | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);

  const {
    bots,
    activeBots,
    totalItems,
    currentPage,
    setCurrentPage,
    totalPages,
    fetchState,
    fetchBots,
  } = useBotsList();

  const handleBotCreated = () => {
    setCurrentPage(1);
    void fetchBots({ page: 1 });
  };

  const handleBotSaved = () => {
    void fetchBots({ page: currentPage });
  };

  const handleBotDeleted = () => {
    void fetchBots({ page: currentPage });
  };

  const handleToggleRuntime = async (bot: BotItem) => {
    setToggleError(null);
    setTogglingBotId(bot.id);
    try {
      if (bot.runtime.status === "running") {
        await pauseBot(bot.id);
      } else {
        await resumeBot(bot.id);
      }
      await fetchBots({ page: currentPage, silent: true });
    } catch (err) {
      setToggleError(err instanceof Error ? err.message : t("myBots.actions.toggleError"));
    } finally {
      setTogglingBotId(null);
    }
  };

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
                : t("myBots.fetch.ok", { count: bots.length })}
          </p>
        </div>
        <div className="header-stats-panel">
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
          <button type="button" className="create-bot-trigger" onClick={() => setCreateModalOpen(true)}>
            {t("myBots.create.openButton")}
          </button>
        </div>
      </div>

      {toggleError ? <p className="bots-toggle-error">{toggleError}</p> : null}

      <div className="bots-grid">
        {bots.map((bot) => (
          <BotTile
            key={bot.id}
            bot={bot}
            onEdit={setEditingBot}
            onToggleRuntime={handleToggleRuntime}
            toggleBusy={togglingBotId === bot.id}
          />
        ))}
      </div>

      {fetchState === "ok" && bots.length === 0 ? (
        <p className="empty-state">{t("myBots.empty")}</p>
      ) : null}

      {totalPages > 1 ? (
        <div className="bots-pagination-wrap">
          <nav className="bots-pagination" aria-label={t("myBots.pagination.navAria")}>
            <button
              type="button"
              className="bots-pagination__btn"
              onClick={() => setCurrentPage((prev) => Math.max(prev - 1, 1))}
              disabled={currentPage <= 1}
              aria-label={t("myBots.pagination.prev")}
            >
              <svg className="bots-pagination__icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                <path fill="currentColor" d="M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z" />
              </svg>
              <span className="bots-pagination__label">{t("myBots.pagination.prev")}</span>
            </button>

            <div
              className="bots-pagination__indicator"
              aria-label={t("myBots.pagination.page", { current: currentPage, total: totalPages })}
            >
              <span className="bots-pagination__current" aria-hidden>
                {currentPage}
              </span>
              <span className="bots-pagination__sep" aria-hidden>
                /
              </span>
              <span className="bots-pagination__total" aria-hidden>
                {totalPages}
              </span>
            </div>

            <button
              type="button"
              className="bots-pagination__btn"
              onClick={() => setCurrentPage((prev) => Math.min(prev + 1, totalPages))}
              disabled={currentPage >= totalPages}
              aria-label={t("myBots.pagination.next")}
            >
              <span className="bots-pagination__label">{t("myBots.pagination.next")}</span>
              <svg className="bots-pagination__icon" viewBox="0 0 24 24" width="18" height="18" aria-hidden>
                <path fill="currentColor" d="M8.59 16.59 13.17 12 8.59 7.41 10 6l6 6-6 6z" />
              </svg>
            </button>
          </nav>
        </div>
      ) : null}

      {createModalOpen ? (
        <CreateBotModal onClose={() => setCreateModalOpen(false)} onCreated={handleBotCreated} />
      ) : null}

      {editingBot ? (
        <EditBotModal
          bot={editingBot}
          onClose={() => setEditingBot(null)}
          onSaved={handleBotSaved}
          onDeleted={handleBotDeleted}
        />
      ) : null}
    </section>
  );
}
