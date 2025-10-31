import type { components } from './types';

export type MessageRead = components['schemas']['MessageRead'];
export type ConversationRead = components['schemas']['ConversationRead'];
export type MessageRole = components['schemas']['MessageRoleEnum'];

export enum ConnectionStatus {
    CONNECTING = 'connecting',
    CONNECTED = 'connected',
    DISCONNECTED = 'disconnected',
    ERROR = 'error',
}

export type WebSocketMessage = { type: 'conversation_created'; conversation_id: number }
    | { type: 'message'; id: number; content: string; role: MessageRole; conversation_id: number; created_at: string}
    | { type: 'error'; error: string };

export interface SendMessagePayload {
    content: string;
    conversation_id?: number;
}

export interface Message {
    id: number | string;
    content: string;
    role: MessageRole;
    created_at: string;
    isOptimistic?: boolean;
}
