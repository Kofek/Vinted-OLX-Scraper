import { useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { deleteBot, updateBot } from "../../api/bots";
import type { BotItem, CreateBotSource, CreateBotFormState, UrlListField } from "../../types/bots";
import { formFromBot } from "../../utils/botForm";
import { collectNonEmptyUrls } from "../../utils/urls";
import CreateBotUrlList from "../CreateBotUrlList/CreateBotUrlList";
import "../CreateBotModal/CreateBotModal.css";

type EditBotModalProps = {
  bot: BotItem;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
};

export default function EditBotModal({ bot, onClose, onSaved, onDeleted }: EditBotModalProps) {
  const { t } = useTranslation();
  const [form, setForm] = useState<CreateBotFormState>(() => formFromBot(bot));
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const busy = submitting || deleting;

  const handleClose = () => {
    if (busy) return;
    onClose();
    setError(null);
  };

  const buildPayload = () => ({
    name: form.name.trim(),
    source: form.source,
    urlsOlx: collectNonEmptyUrls(form.urlsOlx),
    urlsVinted: collectNonEmptyUrls(form.urlsVinted),
    webhookUrl: form.webhookUrl.trim(),
    promptText: form.promptText.trim(),
    enabled: form.enabled,
  });

  const submitUpdate = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await updateBot(bot.id, buildPayload());
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("myBots.edit.errorGeneric"));
    } finally {
      setSubmitting(false);
    }
  };

  const submitDelete = async () => {
    if (!window.confirm(t("myBots.edit.deleteConfirm", { name: bot.name }))) return;
    setError(null);
    setDeleting(true);
    try {
      await deleteBot(bot.id);
      onDeleted();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("myBots.edit.deleteError"));
    } finally {
      setDeleting(false);
    }
  };

  const setUrlAt = (field: UrlListField, index: number, value: string) => {
    setForm((f) => {
      const next = [...f[field]];
      next[index] = value;
      return { ...f, [field]: next };
    });
  };

  const addUrlRow = (field: UrlListField) => {
    setForm((f) => ({ ...f, [field]: [...f[field], ""] }));
  };

  const removeUrlRow = (field: UrlListField, index: number) => {
    setForm((f) => {
      if (f[field].length <= 1) return f;
      return { ...f, [field]: f[field].filter((_, i) => i !== index) };
    });
  };

  const urlListSharedProps = {
    disabled: busy,
    addLabel: t("myBots.create.addUrl"),
    removeAria: t("myBots.create.removeUrlAria"),
    placeholder: t("myBots.create.urlPlaceholder"),
  };

  useEffect(() => {
    const scrollbarWidth = window.innerWidth - document.documentElement.clientWidth;
    const prevOverflow = document.body.style.overflow;
    const prevPaddingRight = document.body.style.paddingRight;

    document.body.style.overflow = "hidden";
    if (scrollbarWidth > 0) {
      document.body.style.paddingRight = `${scrollbarWidth}px`;
    }

    return () => {
      document.body.style.overflow = prevOverflow;
      document.body.style.paddingRight = prevPaddingRight;
    };
  }, []);

  return createPortal(
    <div
      className="create-bot-modal-backdrop"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) handleClose();
      }}
    >
      <div
        className="create-bot-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-bot-modal-title"
      >
        <header className="create-bot-modal-header">
          <h2 id="edit-bot-modal-title" className="create-bot-modal-title">
            {t("myBots.edit.title")}
          </h2>
          <button
            type="button"
            className="create-bot-modal-close"
            onClick={handleClose}
            disabled={busy}
            aria-label={t("myBots.edit.closeAria")}
          >
            ×
          </button>
        </header>

        <form className="create-bot-form" onSubmit={submitUpdate}>
          <p className="edit-bot-id-hint">
            {t("myBots.edit.botId")}: <code>{bot.id}</code>
          </p>

          <label className="create-bot-field">
            <span>{t("myBots.create.name")}</span>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              autoComplete="off"
              disabled={busy}
              required
            />
          </label>

          <label className="create-bot-field">
            <span>{t("myBots.create.source")}</span>
            <select
              value={form.source}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  source: e.target.value as CreateBotSource,
                }))
              }
              disabled={busy}
            >
              <option value="mixed">{t("myBots.create.sourceMixed")}</option>
              <option value="olx">{t("myBots.create.sourceOlx")}</option>
              <option value="vinted">{t("myBots.create.sourceVinted")}</option>
            </select>
          </label>

          <CreateBotUrlList
            label={t("myBots.create.urlsOlx")}
            urls={form.urlsOlx}
            {...urlListSharedProps}
            onChange={(index, value) => setUrlAt("urlsOlx", index, value)}
            onAdd={() => addUrlRow("urlsOlx")}
            onRemove={(index) => removeUrlRow("urlsOlx", index)}
          />

          <CreateBotUrlList
            label={t("myBots.create.urlsVinted")}
            urls={form.urlsVinted}
            {...urlListSharedProps}
            onChange={(index, value) => setUrlAt("urlsVinted", index, value)}
            onAdd={() => addUrlRow("urlsVinted")}
            onRemove={(index) => removeUrlRow("urlsVinted", index)}
          />

          <label className="create-bot-field">
            <span>{t("myBots.create.webhookUrl")}</span>
            <input
              type="text"
              value={form.webhookUrl}
              onChange={(e) => setForm((f) => ({ ...f, webhookUrl: e.target.value }))}
              placeholder="https://"
              disabled={busy}
              required
            />
          </label>

          <label className="create-bot-field">
            <span>{t("myBots.create.promptText")}</span>
            <textarea
              value={form.promptText}
              onChange={(e) => setForm((f) => ({ ...f, promptText: e.target.value }))}
              rows={5}
              disabled={busy}
              required
            />
          </label>

          <label className="create-bot-checkbox">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm((f) => ({ ...f, enabled: e.target.checked }))}
              disabled={busy}
            />
            <span>{t("myBots.create.enabled")}</span>
          </label>

          {error ? <p className="create-bot-error">{error}</p> : null}

          <div className="edit-bot-actions">
            <button
              type="button"
              className="edit-bot-delete"
              onClick={() => void submitDelete()}
              disabled={busy}
            >
              {deleting ? t("myBots.edit.deleting") : t("myBots.edit.delete")}
            </button>
            <div className="create-bot-actions">
              <button type="button" className="create-bot-cancel" onClick={handleClose} disabled={busy}>
                {t("myBots.create.cancel")}
              </button>
              <button type="submit" className="create-bot-submit" disabled={busy}>
                {submitting ? t("myBots.edit.submitting") : t("myBots.edit.submit")}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
