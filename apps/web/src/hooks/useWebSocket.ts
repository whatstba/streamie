import { useEffect, useState, useRef, useCallback } from 'react';

// WebSocket message types from server
export interface ServerMessage {
  type: 'connected' | 'playback_status' | 'error' | 'command_result' | 'pong';
  sessionId?: string;
  message?: string;
  data?: any;
  command?: string;
  success?: boolean;
  error?: string;
  timestamp?: string;
}

// WebSocket message types to server
export interface ClientMessage {
  type: 'play' | 'pause' | 'stop' | 'ping';
  setId?: string;
}

// WebSocket connection state
export enum WebSocketState {
  CONNECTING = 0,
  OPEN = 1,
  CLOSING = 2,
  CLOSED = 3,
}

interface UseWebSocketOptions {
  url: string;
  enabled?: boolean;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  onMessage?: (message: ServerMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

export const useWebSocket = ({
  url,
  enabled = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
  onMessage,
  onOpen,
  onClose,
  onError,
}: UseWebSocketOptions) => {
  const [connectionState, setConnectionState] = useState<WebSocketState>(WebSocketState.CLOSED);
  const [lastMessage, setLastMessage] = useState<ServerMessage | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Send message to server
  const sendMessage = useCallback((message: ClientMessage) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      console.log('📤 Sending WebSocket message:', message);
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected, unable to send message:', message);
    }
  }, []);

  // Close WebSocket connection
  const disconnect = useCallback(() => {
    console.log('🔌 Disconnecting WebSocket...');
    
    // Clear timers
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
    
    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionState(WebSocketState.CLOSED);
  }, []);

  // Store callbacks in refs to avoid circular dependencies
  const callbacksRef = useRef({
    onOpen,
    onMessage,
    onError,
    onClose
  });
  
  // Update callbacks ref when they change
  useEffect(() => {
    callbacksRef.current = {
      onOpen,
      onMessage,
      onError,
      onClose
    };
  }, [onOpen, onMessage, onError, onClose]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!enabled || wsRef.current) {
      return;
    }

    console.log('🔌 Connecting to WebSocket:', url);
    setConnectionState(WebSocketState.CONNECTING);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ WebSocket connected successfully');
        setConnectionState(WebSocketState.OPEN);
        setReconnectAttempts(0);
        
        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          // Use the ws instance directly instead of sendMessage
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000); // Ping every 30 seconds
        
        callbacksRef.current.onOpen?.();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerMessage;
          console.log('📥 WebSocket message received:', message);
          setLastMessage(message);
          callbacksRef.current.onMessage?.(message);
        } catch (error) {
          console.error('❌ Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
        callbacksRef.current.onError?.(error);
      };

      ws.onclose = () => {
        console.log('🔌 WebSocket closed');
        setConnectionState(WebSocketState.CLOSED);
        wsRef.current = null;
        
        // Clear ping interval
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }
        
        callbacksRef.current.onClose?.();

        // Attempt to reconnect if enabled and not at max attempts
        if (enabled && reconnectAttempts < maxReconnectAttempts) {
          const timeout = reconnectInterval * Math.pow(1.5, reconnectAttempts); // Exponential backoff
          console.log(`🔄 Attempting to reconnect in ${timeout}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts(prev => prev + 1);
            connect();
          }, timeout);
        }
      };
    } catch (error) {
      console.error('❌ Failed to create WebSocket:', error);
      setConnectionState(WebSocketState.CLOSED);
    }
  }, [url, enabled, reconnectAttempts, maxReconnectAttempts, reconnectInterval]);

  // Store connect function in a ref to avoid circular dependencies
  const connectRef = useRef(connect);
  connectRef.current = connect;
  
  const disconnectRef = useRef(disconnect);
  disconnectRef.current = disconnect;

  // Effect to manage connection lifecycle
  useEffect(() => {
    if (enabled) {
      connectRef.current();
    } else {
      disconnectRef.current();
    }

    return () => {
      disconnectRef.current();
    };
  }, [enabled]);

  return {
    connectionState,
    isConnected: connectionState === WebSocketState.OPEN,
    lastMessage,
    sendMessage,
    disconnect,
    reconnect: connect,
  };
};