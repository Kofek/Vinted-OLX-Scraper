import { useTranslation } from "react-i18next";
import type { BotItem } from "../../types/bots";
import { getBotDisplayStatus } from "../../utils/botDisplayStatus";
import { formatLastActivityLabel } from "../../utils/time";
import "./BotTile.css";

type BotTileProps = {
  bot: BotItem;
  onEdit: (bot: BotItem) => void;
  onToggleRuntime: (bot: BotItem) => void;
  toggleBusy: boolean;
};

export default function BotTile({ bot, onEdit, onToggleRuntime, toggleBusy }: BotTileProps) {
  const { t, i18n } = useTranslation();
  const displayStatus = getBotDisplayStatus(bot);
  const isEnabled = bot.enabled;
  const statusLabelKey = `myBots.status.${displayStatus}` as const;

  const lastActivity =
    displayStatus === "running"
      ? formatLastActivityLabel(bot.runtime.lastHeartbeatUtc, i18n.language, t("time.justNow"))
      : formatLastActivityLabel(
          bot.runtime.lastStoppedUtc ?? bot.runtime.lastHeartbeatUtc,
          i18n.language,
          t("time.justNow"),
        );
  const success =
    bot.runtime.successRate == null ? "—" : `${Number(bot.runtime.successRate).toFixed(1)}%`;

  return (
    <article className={`bot-tile bot-tile--${displayStatus}`}>
      <div className="bot-tile-accent" />
      <div className="bot-tile-inner">
        <header className="bot-tile-header">
          <h3 className="bot-tile-name">{bot.name}</h3>
          <span
            className={`bot-tile-pill bot-tile-pill--${displayStatus}`}
            aria-label={t(statusLabelKey)}
          >
            <span className="bot-tile-dot" aria-hidden />
            {t(statusLabelKey)}
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
          <button
            type="button"
            className={`bot-tile-main-btn bot-tile-main-btn--${isEnabled ? "pause" : "resume"}`}
            onClick={() => onToggleRuntime(bot)}
            disabled={toggleBusy}
          >
            {toggleBusy
              ? t("myBots.actions.toggling")
              : isEnabled
                ? t("myBots.actions.pause")
                : t("myBots.actions.resume")}
          </button>
          <button
            type="button"
            className="bot-tile-icon-btn"
            aria-label={t("myBots.actions.editAria")}
            onClick={() => onEdit(bot)}
          >
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
}
