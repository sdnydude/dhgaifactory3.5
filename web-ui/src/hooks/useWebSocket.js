import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (url) => {
    const [messages, setMessages] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const socketRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);

    const connect = useCallback(() => {
        try {
            if (socketRef.current?.readyState === WebSocket.OPEN) return;

            console.log('Connecting to WebSocket:', url);
            const ws = new WebSocket(url);
            socketRef.current = ws;

            ws.onopen = () => {
                console.log('WebSocket Connected');
                ws.send(JSON.stringify({ type: 'connection.init' }));
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const { type, payload } = data;

                    if (type === 'chat.response') {
                        setMessages(prev => [...prev, { role: 'assistant', content: payload.content || payload }]);
                        setIsProcessing(false);
                    } else if (type === 'status' || type === 'agent.status') {
                        console.log('Status update:', payload);
                    } else if (type === 'connection.ack') {
                        console.log('Handshake acknowledged:', payload);
                    }
                } catch (err) {
                    console.error('Error parsing WebSocket message:', err);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket Disconnected');
                setIsConnected(false);
                reconnectTimeoutRef.current = setTimeout(connect, 3000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket Error:', error);
                ws.close();
            };

        } catch (err) {
            console.error('Connection failed:', err);
        }
    }, [url]);

    useEffect(() => {
        connect();
        return () => {
            if (socketRef.current) {
                socketRef.current.close();
            }
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
        };
    }, [connect]);

    const sendMessage = useCallback((content, metadata = {}) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            const msg = {
                type: 'chat.message',
                data: {
                    content,
                    ...metadata
                }
            };
            socketRef.current.send(JSON.stringify(msg));
            setMessages(prev => [...prev, { role: 'user', content }]);
            setIsProcessing(true);
        } else {
            console.error('WebSocket is not connected');
        }
    }, []);

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    // Helper to add messages directly (for non-WebSocket flows like Ollama)
    const addMessage = useCallback((message) => {
        setMessages(prev => [...prev, message]);
    }, []);

    return {
        messages,
        isConnected,
        isProcessing,
        sendMessage,
        clearMessages,
        addMessage,
        setIsProcessing
    };
};
