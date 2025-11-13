import type { components } from './types';

// Export types from OpenAPI schema
export type MessageRead = components['schemas']['MessageRead'];
export type ConversationRead = components['schemas']['ConversationRead'];
export type MessageRole = components['schemas']['MessageRoleEnum'];

// Export WebSocket message types from OpenAPI schema
export type MessagePartBase = components['schemas']['MessagePartBase'];
export type PartKind = components['schemas']['PartKind'];
export type ToolStatus = components['schemas']['ToolStatus'];
export type NodeData = components['schemas']['NodeData'];
export type ConversationCreatedMessage = components['schemas']['ConversationCreatedMessage'];
export type MessageMessage = components['schemas']['MessageMessage'];
export type MessagePartMessage = components['schemas']['MessagePartMessage'];
export type NodeAddedMessage = components['schemas']['NodeAddedMessage'];
export type TextChunkMessage = components['schemas']['TextChunkMessage'];
export type MessageCompleteMessage = components['schemas']['MessageCompleteMessage'];
export type ToolStartMessage = components['schemas']['ToolStartMessage'];
export type ToolCompleteMessage = components['schemas']['ToolCompleteMessage'];
export type ErrorMessage = components['schemas']['ErrorMessage'];

// Union type of all WebSocket messages
export type WebSocketMessage =
    | ConversationCreatedMessage
    | MessageMessage
    | MessagePartMessage
    | NodeAddedMessage
    | TextChunkMessage
    | MessageCompleteMessage
    | ToolStartMessage
    | ToolCompleteMessage
    | ErrorMessage;

// For backward compatibility, create alias for MessagePart
export type MessagePart = MessagePartBase;

export enum ConnectionStatus {
    CONNECTING = 'connecting',
    CONNECTED = 'connected',
    DISCONNECTED = 'disconnected',
    ERROR = 'error',
}

export interface SendMessagePayload {
    content: string;
    conversation_id?: number;
}

export interface Message {
    id: number | string;
    parts: MessagePart[];
    role: MessageRole;
    created_at: string;
    model_name?: string;
    timestamp?: string;
}
