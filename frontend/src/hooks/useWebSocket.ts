// @TASK T-WS-3 - WebSocket hook for real-time alert notifications
// @SPEC TRD: "alert delivery within 5 seconds" via WebSocket push
/**
 * Custom React hook for WebSocket connection with auto-reconnect.
 *
 * Connects to the backend WebSocket endpoint and provides:
 * - `lastMessage`: the most recent parsed JSON message from the server
 * - `isConnected`: whether the WebSocket is currently open
 *
 * Features:
 * - Derives WS URL from VITE_API_BASE_URL (http->ws, https->wss)
 * - Exponential backoff reconnection (1s -> 2s -> 4s -> ... -> 30s max)
 * - Sends periodic ping to keep connection alive
 * - Cleans up on unmount
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

interface UseWebSocketReturn {
  lastMessage: WebSocketMessage | null;
  isConnected: boolean;
}

/** Maximum reconnect delay in milliseconds. */
const MAX_RECONNECT_DELAY_MS = 30_000;

/** Base reconnect delay in milliseconds. */
const BASE_RECONNECT_DELAY_MS = 1_000;

/** Ping interval in milliseconds (25 seconds). */
const PING_INTERVAL_MS = 25_000;

/**
 * Derive the WebSocket URL from the API base URL.
 *
 * Examples:
 *   "http://localhost:8000"  -> "ws://localhost:8000/api/v1/ws"
 *   "https://api.example.com" -> "wss://api.example.com/api/v1/ws"
 *   "" (empty/unset) -> uses current page host with ws:// protocol
 */
function buildWsUrl(): string {
  const apiBase = import.meta.env.VITE_API_BASE_URL as string | undefined;

  if (apiBase) {
    const wsBase = apiBase
      .replace(/^https:/, 'wss:')
      .replace(/^http:/, 'ws:');
    return `${wsBase}/api/v1/ws`;
  }

  // Fallback: derive from current page location
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/api/v1/ws`;
}

export function useWebSocket(): UseWebSocketReturn {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const [isConnected, setIsConnected] = useState(false);

  // Refs to persist across renders without triggering re-renders.
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const unmountedRef = useRef(false);

  const clearTimers = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (pingTimerRef.current !== null) {
      clearInterval(pingTimerRef.current);
      pingTimerRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (unmountedRef.current) return;

    const url = buildWsUrl();

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (unmountedRef.current) return;
        setIsConnected(true);
        reconnectAttemptRef.current = 0;

        // Start periodic ping to keep connection alive.
        pingTimerRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, PING_INTERVAL_MS);
      };

      ws.onmessage = (event: MessageEvent) => {
        if (unmountedRef.current) return;
        try {
          const data = JSON.parse(event.data) as WebSocketMessage;
          setLastMessage(data);
        } catch {
          // Non-JSON message -- ignore silently.
        }
      };

      ws.onclose = () => {
        if (unmountedRef.current) return;
        setIsConnected(false);
        clearTimers();

        // Schedule reconnect with exponential backoff.
        const attempt = reconnectAttemptRef.current;
        const delay = Math.min(
          BASE_RECONNECT_DELAY_MS * Math.pow(2, attempt),
          MAX_RECONNECT_DELAY_MS,
        );
        reconnectAttemptRef.current = attempt + 1;

        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      };

      ws.onerror = () => {
        // onerror is always followed by onclose, so reconnect logic
        // is handled there. Just close the socket cleanly.
        ws.close();
      };
    } catch {
      // WebSocket constructor can throw on invalid URLs.
      // Schedule a reconnect attempt.
      const attempt = reconnectAttemptRef.current;
      const delay = Math.min(
        BASE_RECONNECT_DELAY_MS * Math.pow(2, attempt),
        MAX_RECONNECT_DELAY_MS,
      );
      reconnectAttemptRef.current = attempt + 1;
      reconnectTimerRef.current = setTimeout(() => {
        connect();
      }, delay);
    }
  }, [clearTimers]);

  useEffect(() => {
    unmountedRef.current = false;
    connect();

    return () => {
      unmountedRef.current = true;
      clearTimers();
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect, clearTimers]);

  return { lastMessage, isConnected };
}
