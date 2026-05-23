import { useState, useEffect, useCallback } from "react";
import { fetchBotsPage } from "../api/bots";
import type { BotItem } from "../types/bots";

export type FetchState = "loading" | "ok" | "error";

export function useBotsList() {
  const [bots, setBots] = useState<BotItem[]>([]);
  const [activeBots, setActiveBots] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [fetchState, setFetchState] = useState<FetchState>("loading");

  const fetchBots = useCallback(
    async (options?: { page?: number; silent?: boolean }) => {
      const page = options?.page ?? currentPage;
      if (!options?.silent) {
        setFetchState("loading");
      }
      try {
        const data = await fetchBotsPage(page);
        setBots(data.items ?? []);
        setActiveBots(data.summary?.activeBotsCount ?? 0);
        setTotalItems(data.summary?.totalItemsFound ?? 0);
        setCurrentPage(data.pagination?.page ?? page);
        setTotalPages(data.pagination?.totalPages ?? 1);
        setFetchState("ok");
      } catch {
        if (!options?.silent) {
          setFetchState("error");
        }
      }
    },
    [currentPage],
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => void fetchBots(), 0);
    const intervalId = window.setInterval(() => void fetchBots({ silent: true }), 10_000);
    return () => {
      window.clearTimeout(timeoutId);
      window.clearInterval(intervalId);
    };
  }, [fetchBots]);

  return {
    bots,
    activeBots,
    totalItems,
    currentPage,
    setCurrentPage,
    totalPages,
    fetchState,
    fetchBots,
  };
}
