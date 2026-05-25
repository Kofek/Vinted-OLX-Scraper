import { useState, useEffect, useCallback, useRef } from "react";
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

  const currentPageRef = useRef(currentPage);
  currentPageRef.current = currentPage;

  const requestIdRef = useRef(0);

  const fetchBots = useCallback(async (options?: { page?: number; silent?: boolean }) => {
    const page = options?.page ?? currentPageRef.current;
    const requestId = ++requestIdRef.current;

    if (!options?.silent) {
      setFetchState("loading");
    }

    try {
      const data = await fetchBotsPage(page);
      if (requestId !== requestIdRef.current) {
        return;
      }

      const apiPage = data.pagination?.page ?? page;
      setBots(data.items ?? []);
      setActiveBots(data.summary?.activeBotsCount ?? 0);
      setTotalItems(data.summary?.totalItemsFound ?? 0);
      setTotalPages(data.pagination?.totalPages ?? 1);
      setCurrentPage(apiPage);
      setFetchState("ok");
    } catch {
      if (requestId !== requestIdRef.current) {
        return;
      }
      if (!options?.silent) {
        setFetchState("error");
      }
    }
  }, []);

  const goToPage = useCallback(
    (page: number) => {
      const safePage = Math.max(1, page);
      currentPageRef.current = safePage;
      setCurrentPage(safePage);
      void fetchBots({ page: safePage });
    },
    [fetchBots],
  );

  useEffect(() => {
    void fetchBots({ page: 1 });
  }, [fetchBots]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      void fetchBots({ page: currentPageRef.current, silent: true });
    }, 10_000);

    return () => window.clearInterval(intervalId);
  }, [fetchBots]);

  return {
    bots,
    activeBots,
    totalItems,
    currentPage,
    totalPages,
    fetchState,
    fetchBots,
    goToPage,
  };
}
