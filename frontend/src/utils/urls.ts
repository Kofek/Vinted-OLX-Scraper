export function collectNonEmptyUrls(urls: string[]): string[] {
  return urls.map((url) => url.trim()).filter(Boolean);
}
