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
                setIsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const { type, payload } = data;

                    if (type === 'message') {
                        // Standard chat message
                        setMessages(prev => [...prev, { role: 'assistant', content: payload }]);
                        setIsProcessing(false);
                    } else if (type === 'status') {
                        // Status update (e.g. "Researching...", "Generating...")
                        // TODO: specific UX for status updates?
                    }

                } catch (err) {
                    console.error('Error parsing WebSocket message:', err);
                }
            };

            ws.onclose = () => {
                console.log('WebSocket Disconnected');
                setIsConnected(false);
                // Attempt reconnect after 3 seconds
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

    const sendMessage = useCallback((content) => {
        if (socketRef.current?.readyState === WebSocket.OPEN) {
            const msg = {
                type: 'message', // Standardize message format
                payload: content
            };
            socketRef.current.send(JSON.stringify(msg));

            // Optimistic update
            setMessages(prev => [...prev, { role: 'user', content }]);
            setIsProcessing(true);
        } else {
            console.error('WebSocket is not connected');
            // Could show toast error here
        }
    }, []);

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    return { messages, isConnected, isProcessing, sendMessage, clearMessages };
};
