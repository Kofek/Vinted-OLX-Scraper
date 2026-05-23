import type { BotItem, CreateBotFormState, CreateBotSource } from "../types/bots";

function urlsToFormRows(urls: string[]) {
  if (!urls.length) return [""];
  return urls;
}

export function formFromBot(bot: BotItem): CreateBotFormState {
  const source = (bot.source || "mixed") as CreateBotSource;
  return {
    name: bot.name,
    source,
    urlsOlx: urlsToFormRows(bot.urlsOlx ?? []),
    urlsVinted: urlsToFormRows(bot.urlsVinted ?? []),
    webhookUrl: bot.webhookUrl ?? "",
    promptText: bot.promptText ?? "",
    enabled: bot.enabled,
  };
}
