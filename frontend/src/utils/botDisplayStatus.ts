import type { BotItem } from "../types/bots";

export type BotDisplayStatus = "paused" | "waiting" | "running" | "error" | "unknown";

/** Maps enabled + runtime.status to the label shown on the bot tile. */
export function getBotDisplayStatus(bot: BotItem): BotDisplayStatus {
  if (!bot.enabled) {
    return "paused";
  }

  const status = bot.runtime.status;
  if (status === "running" || status === "waiting" || status === "error") {
    return status;
  }

  if (status === "paused") {
    return "waiting";
  }

  return "unknown";
}

/** Picks the timestamp shown as "last activity" on the bot tile. */
export function getBotLastActivityUtc(bot: BotItem, displayStatus: BotDisplayStatus) {
  if (displayStatus === "paused") {
    return bot.runtime.lastStoppedUtc ?? bot.runtime.lastHeartbeatUtc;
  }

  return bot.runtime.lastHeartbeatUtc;
}
