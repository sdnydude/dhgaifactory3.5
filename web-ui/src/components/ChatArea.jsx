import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { Send } from 'lucide-react';
import HarmonicLoader from './HarmonicLoader';

const ChatArea = ({ messages, onSendMessage, isProcessing, streamingContent }) => {
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isProcessing]);

    const handleSend = () => {
        if (inputValue.trim()) {
            onSendMessage(inputValue);
            setInputValue('');
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-area">
            <div className="chat-area__messages">
                {messages.length === 0 ? (
                    <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--color-text-muted)',
                        padding: 'var(--space-8)'
                    }}>
                        <div style={{
                            width: '5rem',
                            height: '5rem',
                            background: 'var(--glass-bg)',
                            backdropFilter: 'var(--glass-blur)',
                            borderRadius: '30%',
                            border: '1px solid var(--glass-border)',
                            marginBottom: 'var(--space-6)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 0 40px rgba(139, 92, 246, 0.2)',
                            transform: 'rotate(-5deg)'
                        }}>
                            <div style={{
                                width: '2.5rem',
                                height: '2.5rem',
                                borderRadius: '50%',
                                background: 'var(--gradient-primary)',
                                boxShadow: '0 0 20px var(--color-dhg-primary)'
                            }}></div>
                        </div>
                        <h2 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, margin: 0, color: 'var(--color-text)' }}>
                            Factory Intelligence Online
                        </h2>
                        <p style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)', opacity: 0.7 }}>
                            Initialize a session to begin multi-agent orchestration.
                        </p>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, index) => (
                            <MessageBubble key={index} message={msg} />
                        ))}

                        {isProcessing && (
                            <div className="streaming-indicator">
                                {streamingContent ? (
                                    <MessageBubble
                                        message={{
                                            role: 'assistant',
                                            content: streamingContent,
                                            isStreaming: true
                                        }}
                                    />
                                ) : (
                                    <HarmonicLoader />
                                )}
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </>
                )}
            </div>

            <div className="chat-area__input-container">
                <div className="chat-area__input-wrapper">
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type your message..."
                        className="chat-area__input"
                        disabled={isProcessing}
                        rows={3}
                        style={{
                            resize: 'none',
                            whiteSpace: 'pre-wrap',
                            wordWrap: 'break-word',
                            color: '#ffffff',
                            caretColor: '#ffffff',
                            lineHeight: '1.5'
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isProcessing}
                        className="chat-area__send-button"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatArea;
