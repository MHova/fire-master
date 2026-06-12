export interface ChatMessage {
  role: "user" | "assistant";
  content: string | ContentBlock[];
}

export interface ContentBlock {
  type: "text" | "tool_use" | "tool_result";
  text?: string;
  id?: string;
  name?: string;
  input?: Record<string, unknown>;
  tool_use_id?: string;
  content?: string;
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  model: string;
  message_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string | null;
  model: string;
  messages: ChatMessage[];
  context_snapshot: Record<string, unknown>;
  total_input_tokens: number;
  total_output_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

// SSE event types from the backend
export interface SSETextEvent {
  type: "text";
  text: string;
}

export interface SSEToolUseEvent {
  type: "tool_use";
  tool: string;
  id: string;
}

export interface SSEDoneEvent {
  type: "done";
  conversation_id: string;
}

export interface SSEErrorEvent {
  type: "error";
  error: string;
}

export type SSEEvent = SSETextEvent | SSEToolUseEvent | SSEDoneEvent | SSEErrorEvent;
