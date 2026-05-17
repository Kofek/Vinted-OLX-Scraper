import { useState } from "react";
import { useTranslation } from "react-i18next";
import StatCard from "../components/StatCard/StatCard";
import BotTile from "../components/BotTile/BotTile";
import CreateBotModal from "../components/CreateBotModal/CreateBotModal";
import { useBotsList } from "../hooks/useBotsList";
import "./MyBotsPage.css";

export default function MyBotsPage() {
  const { t } = useTranslation();
  const [createModalOpen, setCreateModalOpen] = useState(false);

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

      <div className="bots-grid">
        {bots.map((bot) => (
          <BotTile key={bot.id} bot={bot} />
        ))}
      </div>

      {fetchState === "ok" && bots.length === 0 ? (
        <p className="empty-state">{t("myBots.empty")}</p>
      ) : null}

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

      {createModalOpen ? (
        <CreateBotModal onClose={() => setCreateModalOpen(false)} onCreated={handleBotCreated} />
      ) : null}
    </section>
  );
}
