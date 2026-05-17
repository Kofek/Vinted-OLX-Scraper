export function parseIsoTimestamp(timestamp: string | null): Date | null {
  if (!timestamp) return null;
  const date = new Date(timestamp);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatLastActivityLabel(
  isoUtc: string | null,
  language: string,
  justNowLabel: string,
): string {
  const dateUtc = parseIsoTimestamp(isoUtc);
  if (!dateUtc) return "—";

  const diffSec = Math.round((Date.now() - dateUtc.getTime()) / 1000);
  if (diffSec < 60) {
    return justNowLabel;
  }

  const formatter = new Intl.RelativeTimeFormat(language, { numeric: "auto" });

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
}
