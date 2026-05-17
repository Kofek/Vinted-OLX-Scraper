export type CreateBotUrlListProps = {
  label: string;
  urls: string[];
  disabled: boolean;
  addLabel: string;
  removeAria: string;
  placeholder: string;
  onChange: (index: number, value: string) => void;
  onAdd: () => void;
  onRemove: (index: number) => void;
};

export default function CreateBotUrlList({
  label,
  urls,
  disabled,
  addLabel,
  removeAria,
  placeholder,
  onChange,
  onAdd,
  onRemove,
}: CreateBotUrlListProps) {
  return (
    <div className="create-bot-field create-bot-url-list">
      <span>{label}</span>
      <ul className="create-bot-url-rows">
        {urls.map((url, index) => (
          <li key={index} className="create-bot-url-row">
            <input
              type="text"
              value={url}
              onChange={(e) => onChange(index, e.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              autoComplete="off"
            />
            {urls.length > 1 ? (
              <button
                type="button"
                className="create-bot-url-remove"
                onClick={() => onRemove(index)}
                disabled={disabled}
                aria-label={removeAria}
              >
                ×
              </button>
            ) : null}
          </li>
        ))}
      </ul>
      <button type="button" className="create-bot-url-add" onClick={onAdd} disabled={disabled}>
        + {addLabel}
      </button>
    </div>
  );
}
