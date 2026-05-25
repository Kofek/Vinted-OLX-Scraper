import { useState, useEffect, useCallback, useRef } from "react";
import { fetchBotsPage } from "../api/bots";
import type { BotItem, BotsResponse } from "../types/bots";

export type FetchState = "loading" | "ok" | "error";

export function useBotsList() {
  const [bots, setBots] = useState<BotItem[]>([]);
  const [activeBots, setActiveBots] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [fetchState, setFetchState] = useState<FetchState>("loading");

  const currentPageRef = useRef(1);
  const requestIdRef = useRef(0);

  useEffect(() => {
    currentPageRef.current = currentPage;
  }, [currentPage]);

  const applyListResponse = useCallback((data: BotsResponse, page: number) => {
    const apiPage = data.pagination?.page ?? page;
    setBots(data.items ?? []);
    setActiveBots(data.summary?.activeBotsCount ?? 0);
    setTotalItems(data.summary?.totalItemsFound ?? 0);
    setTotalPages(data.pagination?.totalPages ?? 1);
    setCurrentPage(apiPage);
  }, []);

  const loadPage = useCallback(
    async (page: number, options?: { silent?: boolean }) => {
      const requestId = ++requestIdRef.current;

      if (!options?.silent) {
        setFetchState("loading");
      }

      try {
        const data = await fetchBotsPage(page);
        if (requestId !== requestIdRef.current) {
          return;
        }

        applyListResponse(data, page);
        setFetchState("ok");
      } catch {
        if (requestId !== requestIdRef.current) {
          return;
        }
        if (!options?.silent) {
          setFetchState("error");
        }
      }
    },
    [applyListResponse],
  );

  const fetchBots = useCallback(
    (options?: { page?: number; silent?: boolean }) => {
      const page = options?.page ?? currentPageRef.current;
      void loadPage(page, options);
    },
    [loadPage],
  );

  const goToPage = useCallback(
    (page: number) => {
      const safePage = Math.max(1, page);
      setCurrentPage(safePage);
      void loadPage(safePage);
    },
    [loadPage],
  );

  useEffect(() => {
    let cancelled = false;
    const requestId = ++requestIdRef.current;

    fetchBotsPage(1)
      .then((data) => {
        if (cancelled || requestId !== requestIdRef.current) {
          return;
        }
        applyListResponse(data, 1);
        setFetchState("ok");
      })
      .catch(() => {
        if (cancelled || requestId !== requestIdRef.current) {
          return;
        }
        setFetchState("error");
      });

    const intervalId = window.setInterval(() => {
      void loadPage(currentPageRef.current, { silent: true });
    }, 10_000);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [applyListResponse, loadPage]);

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
