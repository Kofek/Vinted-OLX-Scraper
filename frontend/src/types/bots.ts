export type BotRuntime = {
  status: string;
  lastHeartbeatUtc: string | null;
  lastStartedUtc: string | null;
  lastStoppedUtc: string | null;
  itemsFound: number;
  successRate: number | null;
  lastError: string | null;
};

export type BotItem = {
  id: string;
  name: string;
  source: string;
  urlsOlx: string[];
  urlsVinted: string[];
  webhookUrl: string | null;
  enabled: boolean;
  promptText: string;
  createdAtUtc: string | null;
  updatedAtUtc: string | null;
  runtime: BotRuntime;
};

export type BotsResponse = {
  items: BotItem[];
  pagination: {
    page: number;
    pageSize: number;
    totalBots: number;
    totalPages: number;
  };
  summary: {
    activeBotsCount: number;
    totalItemsFound: number;
  };
};

export type CreateBotSource = "mixed" | "olx" | "vinted";

export type CreateBotFormState = {
  name: string;
  source: CreateBotSource;
  urlsOlx: string[];
  urlsVinted: string[];
  webhookUrl: string;
  promptText: string;
  enabled: boolean;
};

export type UrlListField = "urlsOlx" | "urlsVinted";

export type CreateBotPayload = {
  name: string;
  source: CreateBotSource;
  urlsOlx: string[];
  urlsVinted: string[];
  webhookUrl: string;
  promptText: string;
  enabled: boolean;
};
