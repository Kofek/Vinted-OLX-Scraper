import { API_BASE_URL, BOTS_PAGE_SIZE } from "../config/api";
import type { BotsResponse, CreateBotPayload } from "../types/bots";
import { apiErrorDetail } from "./http";

export async function fetchBotsPage(page: number, pageSize = BOTS_PAGE_SIZE): Promise<BotsResponse> {
  const response = await fetch(`${API_BASE_URL}/api/bots?page=${page}&pageSize=${pageSize}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json() as Promise<BotsResponse>;
}

export async function createBot(payload: CreateBotPayload): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/bots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await apiErrorDetail(response);
    throw new Error(detail || "Request failed");
  }
}
