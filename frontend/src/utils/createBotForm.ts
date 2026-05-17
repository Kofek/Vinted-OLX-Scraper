import type { CreateBotFormState } from "../types/bots";

export function emptyCreateForm(): CreateBotFormState {
  return {
    name: "",
    source: "mixed",
    urlsOlx: [""],
    urlsVinted: [""],
    webhookUrl: "",
    promptText: "",
    enabled: true,
  };
}
