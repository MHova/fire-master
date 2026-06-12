/**
 * Streaming chat client for the AI advisor.
 * Uses fetch + ReadableStream (not EventSource) for POST + auth header support.
 */

import type { SSEEvent } from "../types/advisor";

const BASE = "/api/advisor";

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("token");
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/**
 * Stream chat responses from the advisor API.
 * Yields parsed SSE events as they arrive.
 */
export async function* streamChat(
  message: string,
  conversationId?: string | null,
  pageContext?: string | null,
  model?: string | null,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId ?? undefined,
      page_context: pageContext ?? undefined,
      model: model ?? undefined,
    }),
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* ignore */ }
    throw new Error(detail);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // Keep incomplete last line

    let currentEvent = "";
    for (const line of lines) {
      if (line.startsWith("event: ")) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith("data: ")) {
        const data = line.slice(6);
        try {
          const parsed = JSON.parse(data);
          yield { type: currentEvent, ...parsed } as SSEEvent;
        } catch { /* skip malformed */ }
      }
      // Empty line resets event (SSE spec), but we handle inline
    }
  }
}
