import { useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";
import { createBot } from "../../api/bots";
import type { CreateBotSource, CreateBotFormState, UrlListField } from "../../types/bots";
import { collectNonEmptyUrls } from "../../utils/urls";
import { emptyCreateForm } from "../../utils/createBotForm";
import CreateBotUrlList from "../CreateBotUrlList/CreateBotUrlList";
import "./CreateBotModal.css";

type CreateBotModalProps = {
  onClose: () => void;
  onCreated: () => void;
};

export default function CreateBotModal({ onClose, onCreated }: CreateBotModalProps) {
  const { t } = useTranslation();
  const [createForm, setCreateForm] = useState<CreateBotFormState>(() => emptyCreateForm());
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleClose = () => {
    if (createSubmitting) return;
    onClose();
    setCreateForm(emptyCreateForm());
    setCreateError(null);
  };

  const submitCreateBot = async (event: FormEvent) => {
    event.preventDefault();
    setCreateError(null);
    setCreateSubmitting(true);
    try {
      await createBot({
        name: createForm.name.trim(),
        source: createForm.source,
        urlsOlx: collectNonEmptyUrls(createForm.urlsOlx),
        urlsVinted: collectNonEmptyUrls(createForm.urlsVinted),
        webhookUrl: createForm.webhookUrl.trim(),
        promptText: createForm.promptText.trim(),
        enabled: createForm.enabled,
      });
      setCreateForm(emptyCreateForm());
      onCreated();
      onClose();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : t("myBots.create.errorGeneric"));
    } finally {
      setCreateSubmitting(false);
    }
  };

  const setUrlAt = (field: UrlListField, index: number, value: string) => {
    setCreateForm((f) => {
      const next = [...f[field]];
      next[index] = value;
      return { ...f, [field]: next };
    });
  };

  const addUrlRow = (field: UrlListField) => {
    setCreateForm((f) => ({ ...f, [field]: [...f[field], ""] }));
  };

  const removeUrlRow = (field: UrlListField, index: number) => {
    setCreateForm((f) => {
      if (f[field].length <= 1) return f;
      return { ...f, [field]: f[field].filter((_, i) => i !== index) };
    });
  };

  const urlListSharedProps = {
    disabled: createSubmitting,
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
        aria-labelledby="create-bot-modal-title"
      >
        <header className="create-bot-modal-header">
          <h2 id="create-bot-modal-title" className="create-bot-modal-title">
            {t("myBots.create.title")}
          </h2>
          <button
            type="button"
            className="create-bot-modal-close"
            onClick={handleClose}
            disabled={createSubmitting}
            aria-label={t("myBots.create.closeAria")}
          >
            ×
          </button>
        </header>

        <form className="create-bot-form" onSubmit={submitCreateBot}>
          <label className="create-bot-field">
            <span>{t("myBots.create.name")}</span>
            <input
              type="text"
              value={createForm.name}
              onChange={(e) => setCreateForm((f) => ({ ...f, name: e.target.value }))}
              autoComplete="off"
              disabled={createSubmitting}
              required
            />
          </label>

          <label className="create-bot-field">
            <span>{t("myBots.create.source")}</span>
            <select
              value={createForm.source}
              onChange={(e) =>
                setCreateForm((f) => ({
                  ...f,
                  source: e.target.value as CreateBotSource,
                }))
              }
              disabled={createSubmitting}
            >
              <option value="mixed">{t("myBots.create.sourceMixed")}</option>
              <option value="olx">{t("myBots.create.sourceOlx")}</option>
              <option value="vinted">{t("myBots.create.sourceVinted")}</option>
            </select>
          </label>

          <CreateBotUrlList
            label={t("myBots.create.urlsOlx")}
            urls={createForm.urlsOlx}
            {...urlListSharedProps}
            onChange={(index, value) => setUrlAt("urlsOlx", index, value)}
            onAdd={() => addUrlRow("urlsOlx")}
            onRemove={(index) => removeUrlRow("urlsOlx", index)}
          />

          <CreateBotUrlList
            label={t("myBots.create.urlsVinted")}
            urls={createForm.urlsVinted}
            {...urlListSharedProps}
            onChange={(index, value) => setUrlAt("urlsVinted", index, value)}
            onAdd={() => addUrlRow("urlsVinted")}
            onRemove={(index) => removeUrlRow("urlsVinted", index)}
          />

          <label className="create-bot-field">
            <span>{t("myBots.create.webhookUrl")}</span>
            <input
              type="text"
              value={createForm.webhookUrl}
              onChange={(e) => setCreateForm((f) => ({ ...f, webhookUrl: e.target.value }))}
              placeholder="https://"
              disabled={createSubmitting}
              required
            />
          </label>

          <label className="create-bot-field">
            <span>{t("myBots.create.promptText")}</span>
            <textarea
              value={createForm.promptText}
              onChange={(e) => setCreateForm((f) => ({ ...f, promptText: e.target.value }))}
              rows={5}
              disabled={createSubmitting}
              required
            />
          </label>

          <label className="create-bot-checkbox">
            <input
              type="checkbox"
              checked={createForm.enabled}
              onChange={(e) => setCreateForm((f) => ({ ...f, enabled: e.target.checked }))}
              disabled={createSubmitting}
            />
            <span>{t("myBots.create.enabled")}</span>
          </label>

          {createError ? <p className="create-bot-error">{createError}</p> : null}

          <div className="create-bot-actions">
            <button type="button" className="create-bot-cancel" onClick={handleClose} disabled={createSubmitting}>
              {t("myBots.create.cancel")}
            </button>
            <button type="submit" className="create-bot-submit" disabled={createSubmitting}>
              {createSubmitting ? t("myBots.create.submitting") : t("myBots.create.submit")}
            </button>
          </div>
        </form>
      </div>
    </div>,
    document.body,
  );
}
