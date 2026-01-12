import { useState, useEffect, useRef, useCallback } from 'react';

export const useWebSocket = (url) => {
    const [messages, setMessages] = useState([]);
    const [isConnected, setIsConnected] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [streamingContent, setStreamingContent] = useState('');
    const [agentEvents, setAgentEvents] = useState([]);
    const [validationResult, setValidationResult] = useState(null);

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
                        setStreamingContent('');
                    } else if (type === 'agent.status' || type === 'status') {
                        setAgentEvents(prev => [...prev, { ...payload, timestamp: new Date().toISOString() }]);
                    } else if (type === 'content.chunk') {
                        setStreamingContent(prev => prev + (payload.chunk || ''));
                        setIsProcessing(true);
                    } else if (type === 'content.complete') {
                        setMessages(prev => [...prev, {
                            role: 'assistant',
                            content: streamingContent || payload.content || 'Generation complete.',
                            metadata: payload.metadata,
                            isArtifact: true,
                            title: payload.title
                        }]);
                        setStreamingContent('');
                        setIsProcessing(false);
                    } else if (type === 'validation.complete') {
                        setValidationResult(payload);
                    } else if (type === 'connection.ack') {
                        console.log('Handshake acknowledged:', payload);
                    } else if (type === 'error') {
                        console.error('Server error:', payload.message);
                        setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${payload.message}`, isError: true }]);
                        setIsProcessing(false);
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
    }, [url, streamingContent]);

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
            setStreamingContent('');
            setValidationResult(null);
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
        setAgentEvents([]);
        setStreamingContent('');
    }, []);

    const addMessage = useCallback((message) => {
        setMessages(prev => [...prev, message]);
    }, []);

    return {
        messages,
        isConnected,
        isProcessing,
        streamingContent,
        agentEvents,
        validationResult,
        sendMessage,
        clearMessages,
        addMessage,
        setIsProcessing
    };
};
