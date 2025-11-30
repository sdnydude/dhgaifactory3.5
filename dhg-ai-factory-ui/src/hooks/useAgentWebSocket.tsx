// DHG AI Factory - WebSocket Hook
// Real-time communication with LangGraph agent orchestrator

import { useEffect, useRef, useCallback, useState, createContext, useContext, ReactNode } from 'react';
import { 
  WebSocketEvent, 
  AgentStatusPayload, 
  AgentProgressPayload,
  AgentLogPayload,
  ContentChunkPayload,
  ContentCompletePayload,
  ValidationCompletePayload,
  ChatResponsePayload,
  ErrorPayload,
  CMERequest,
  AgentId
} from '../types';

// ============================================================================
// CONFIGURATION
// ============================================================================

const WS_URL = import.meta.env.VITE_WS_URL || 'wss://api.dhg.ai/ws';
const HEARTBEAT_INTERVAL = 30000;
const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_RECONNECT_DELAY = 1000;

// ============================================================================
// EVENT TYPES
// ============================================================================

type EventHandler<T> = (payload: T, event: WebSocketEvent<T>) => void;

interface EventHandlers {
  // Connection
  onConnected?: () => void;
  onDisconnected?: (reason: string) => void;
  onReconnecting?: (attempt: number) => void;
  
  // Agent events
  onAgentStatus?: EventHandler<AgentStatusPayload>;
  onAgentProgress?: EventHandler<AgentProgressPayload>;
  onAgentLog?: EventHandler<AgentLogPayload>;
  
  // Content events
  onContentChunk?: EventHandler<ContentChunkPayload>;
  onContentComplete?: EventHandler<ContentCompletePayload>;
  
  // Validation events
  onValidationStarted?: EventHandler<{ content_id: string; checks: string[] }>;
  onValidationCheckComplete?: EventHandler<{ check: string; status: string; details: unknown }>;
  onValidationComplete?: EventHandler<ValidationCompletePayload>;
  
  // Chat events
  onChatResponse?: EventHandler<ChatResponsePayload>;
  onChatTyping?: EventHandler<{ agent_id: AgentId; is_typing: boolean }>;
  
  // Error events
  onError?: EventHandler<ErrorPayload>;
  
  // Request events
  onRequestAccepted?: EventHandler<{ request_id: string; estimated_duration: number }>;
  onRequestComplete?: EventHandler<{ request_id: string }>;
  onRequestFailed?: EventHandler<{ request_id: string; error: string }>;
}

// ============================================================================
// WEBSOCKET STATE
// ============================================================================

type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting';

interface UseWebSocketReturn {
  // State
  connectionState: ConnectionState;
  sessionId: string | null;
  lastError: ErrorPayload | null;
  
  // Actions
  connect: () => void;
  disconnect: () => void;
  
  // Request methods
  submitRequest: (request: CMERequest) => Promise<string>;
  cancelRequest: (requestId: string) => void;
  
  // Chat methods
  sendChatMessage: (content: string, requestId?: string) => void;
  
  // Utility
  isConnected: boolean;
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useAgentWebSocket(
  authToken: string,
  handlers: EventHandlers = {}
): UseWebSocketReturn {
  // Refs
  const ws = useRef<WebSocket | null>(null);
  const heartbeatInterval = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const eventSequence = useRef(0);
  const pendingPromises = useRef<Map<string, { resolve: (value: string) => void; reject: (error: Error) => void }>>(new Map());
  
  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [lastError, setLastError] = useState<ErrorPayload | null>(null);
  
  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================
  
  const generateEventId = useCallback(() => {
    return `evt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }, []);
  
  const generateClientId = useCallback(() => {
    // Try to get existing client ID from localStorage
    let clientId = localStorage.getItem('dhg_client_id');
    if (!clientId) {
      clientId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('dhg_client_id', clientId);
    }
    return clientId;
  }, []);
  
  const sendEvent = useCallback(<T,>(type: string, payload: T, correlationId?: string) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Cannot send event: not connected');
      return null;
    }
    
    const eventId = generateEventId();
    const event: WebSocketEvent<T> = {
      type,
      id: eventId,
      timestamp: new Date().toISOString(),
      session_id: sessionId || '',
      payload,
      ...(correlationId && { correlation_id: correlationId }),
      meta: {
        sequence: eventSequence.current++
      }
    };
    
    ws.current.send(JSON.stringify(event));
    return eventId;
  }, [sessionId, generateEventId]);
  
  // ============================================================================
  // EVENT HANDLERS
  // ============================================================================
  
  const handleEvent = useCallback((event: WebSocketEvent<unknown>) => {
    const { type, payload, correlation_id } = event;
    
    switch (type) {
      // Connection events
      case 'connection.ack': {
        const ackPayload = payload as { session_id: string; heartbeat_interval: number };
        setSessionId(ackPayload.session_id);
        setConnectionState('connected');
        handlers.onConnected?.();
        break;
      }
      
      case 'pong':
        // Heartbeat acknowledged
        break;
      
      // Request events
      case 'request.accepted': {
        const acceptedPayload = payload as { request_id: string; estimated_duration: number };
        handlers.onRequestAccepted?.(acceptedPayload, event as WebSocketEvent<typeof acceptedPayload>);
        
        // Resolve pending promise
        if (correlation_id && pendingPromises.current.has(correlation_id)) {
          const { resolve } = pendingPromises.current.get(correlation_id)!;
          resolve(acceptedPayload.request_id);
          pendingPromises.current.delete(correlation_id);
        }
        break;
      }
      
      case 'request.complete': {
        const completePayload = payload as { request_id: string };
        handlers.onRequestComplete?.(completePayload, event as WebSocketEvent<typeof completePayload>);
        break;
      }
      
      case 'request.failed': {
        const failedPayload = payload as { request_id: string; error: string };
        handlers.onRequestFailed?.(failedPayload, event as WebSocketEvent<typeof failedPayload>);
        break;
      }
      
      // Agent events
      case 'agent.status': {
        const statusPayload = payload as AgentStatusPayload;
        handlers.onAgentStatus?.(statusPayload, event as WebSocketEvent<AgentStatusPayload>);
        break;
      }
      
      case 'agent.progress': {
        const progressPayload = payload as AgentProgressPayload;
        handlers.onAgentProgress?.(progressPayload, event as WebSocketEvent<AgentProgressPayload>);
        break;
      }
      
      case 'agent.log': {
        const logPayload = payload as AgentLogPayload;
        handlers.onAgentLog?.(logPayload, event as WebSocketEvent<AgentLogPayload>);
        break;
      }
      
      // Content events
      case 'content.chunk': {
        const chunkPayload = payload as ContentChunkPayload;
        handlers.onContentChunk?.(chunkPayload, event as WebSocketEvent<ContentChunkPayload>);
        break;
      }
      
      case 'content.complete': {
        const contentPayload = payload as ContentCompletePayload;
        handlers.onContentComplete?.(contentPayload, event as WebSocketEvent<ContentCompletePayload>);
        break;
      }
      
      // Validation events
      case 'validation.started': {
        const validationStartPayload = payload as { content_id: string; checks: string[] };
        handlers.onValidationStarted?.(validationStartPayload, event as WebSocketEvent<typeof validationStartPayload>);
        break;
      }
      
      case 'validation.check.complete': {
        const checkPayload = payload as { check: string; status: string; details: unknown };
        handlers.onValidationCheckComplete?.(checkPayload, event as WebSocketEvent<typeof checkPayload>);
        break;
      }
      
      case 'validation.complete': {
        const validationPayload = payload as ValidationCompletePayload;
        handlers.onValidationComplete?.(validationPayload, event as WebSocketEvent<ValidationCompletePayload>);
        break;
      }
      
      // Chat events
      case 'chat.response': {
        const chatPayload = payload as ChatResponsePayload;
        handlers.onChatResponse?.(chatPayload, event as WebSocketEvent<ChatResponsePayload>);
        break;
      }
      
      case 'chat.typing': {
        const typingPayload = payload as { agent_id: AgentId; is_typing: boolean };
        handlers.onChatTyping?.(typingPayload, event as WebSocketEvent<typeof typingPayload>);
        break;
      }
      
      // Error events
      case 'error': {
        const errorPayload = payload as ErrorPayload;
        setLastError(errorPayload);
        handlers.onError?.(errorPayload, event as WebSocketEvent<ErrorPayload>);
        break;
      }
      
      default:
        console.log('[WS] Unhandled event type:', type, payload);
    }
  }, [handlers]);
  
  // ============================================================================
  // HEARTBEAT
  // ============================================================================
  
  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
    }
    
    heartbeatInterval.current = setInterval(() => {
      if (ws.current?.readyState === WebSocket.OPEN) {
        sendEvent('ping', { timestamp: new Date().toISOString() });
      }
    }, HEARTBEAT_INTERVAL);
  }, [sendEvent]);
  
  const stopHeartbeat = useCallback(() => {
    if (heartbeatInterval.current) {
      clearInterval(heartbeatInterval.current);
      heartbeatInterval.current = null;
    }
  }, []);
  
  // ============================================================================
  // CONNECTION MANAGEMENT
  // ============================================================================
  
  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }
    
    setConnectionState('connecting');
    
    try {
      ws.current = new WebSocket(WS_URL);
      
      ws.current.onopen = () => {
        console.log('[WS] Connection opened');
        reconnectAttempts.current = 0;
        
        // Send connection init
        const clientId = generateClientId();
        sendEvent('connection.init', {
          client_id: clientId,
          token: authToken,
          client_version: '1.0.0',
          capabilities: ['streaming', 'compression']
        });
        
        startHeartbeat();
      };
      
      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as WebSocketEvent<unknown>;
          handleEvent(data);
        } catch (error) {
          console.error('[WS] Failed to parse message:', error);
        }
      };
      
      ws.current.onclose = (event) => {
        console.log('[WS] Connection closed:', event.code, event.reason);
        stopHeartbeat();
        setConnectionState('disconnected');
        setSessionId(null);
        handlers.onDisconnected?.(event.reason || 'Connection closed');
        
        // Attempt reconnection
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts.current),
            30000
          );
          
          setConnectionState('reconnecting');
          handlers.onReconnecting?.(reconnectAttempts.current + 1);
          
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };
      
      ws.current.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
      
    } catch (error) {
      console.error('[WS] Failed to create connection:', error);
      setConnectionState('disconnected');
    }
  }, [authToken, generateClientId, sendEvent, startHeartbeat, stopHeartbeat, handleEvent, handlers]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    
    stopHeartbeat();
    
    if (ws.current) {
      sendEvent('connection.terminate', { reason: 'user_disconnect' });
      ws.current.close(1000, 'User disconnect');
      ws.current = null;
    }
    
    setConnectionState('disconnected');
    setSessionId(null);
    reconnectAttempts.current = MAX_RECONNECT_ATTEMPTS; // Prevent auto-reconnect
  }, [sendEvent, stopHeartbeat]);
  
  // ============================================================================
  // REQUEST METHODS
  // ============================================================================
  
  const submitRequest = useCallback((request: CMERequest): Promise<string> => {
    return new Promise((resolve, reject) => {
      const eventId = sendEvent('request.submit', request);
      
      if (!eventId) {
        reject(new Error('Failed to send request: not connected'));
        return;
      }
      
      // Store promise for resolution when server responds
      pendingPromises.current.set(eventId, { resolve, reject });
      
      // Timeout after 30 seconds
      setTimeout(() => {
        if (pendingPromises.current.has(eventId)) {
          pendingPromises.current.delete(eventId);
          reject(new Error('Request timeout'));
        }
      }, 30000);
    });
  }, [sendEvent]);
  
  const cancelRequest = useCallback((requestId: string) => {
    sendEvent('request.cancel', {
      request_id: requestId,
      reason: 'user_cancelled'
    });
  }, [sendEvent]);
  
  // ============================================================================
  // CHAT METHODS
  // ============================================================================
  
  const sendChatMessage = useCallback((content: string, requestId?: string) => {
    sendEvent('chat.message', {
      content,
      request_id: requestId,
      attachments: []
    });
  }, [sendEvent]);
  
  // ============================================================================
  // CLEANUP
  // ============================================================================
  
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);
  
  // ============================================================================
  // RETURN
  // ============================================================================
  
  return {
    connectionState,
    sessionId,
    lastError,
    connect,
    disconnect,
    submitRequest,
    cancelRequest,
    sendChatMessage,
    isConnected: connectionState === 'connected'
  };
}

// ============================================================================
// WEBSOCKET CONTEXT (for provider pattern)
// ============================================================================


interface WebSocketContextValue extends UseWebSocketReturn {}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

interface WebSocketProviderProps {
  children: ReactNode;
  authToken: string;
  handlers?: EventHandlers;
}

export function WebSocketProvider({ children, authToken, handlers }: WebSocketProviderProps) {
  const ws = useAgentWebSocket(authToken, handlers);
  
  return (
    <WebSocketContext.Provider value={ws}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket(): WebSocketContextValue {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

export default useAgentWebSocket;
