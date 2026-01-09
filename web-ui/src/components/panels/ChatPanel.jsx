import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from '../MessageBubble';
import { Send, MessageSquare } from 'lucide-react';
import HarmonicLoader from '../HarmonicLoader';

const ChatPanel = ({ messages = [], onSendMessage, isProcessing }) => {
    const [inputValue, setInputValue] = useState('');
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isProcessing]);

    const handleSend = () => {
        if (inputValue.trim() && onSendMessage) {
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
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            background: 'var(--glass-bg)',
            backdropFilter: 'var(--glass-blur)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--glass-border)',
            overflow: 'hidden'
        }}>
            {/* Panel Header */}
            <div style={{
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '1px solid var(--glass-border)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                background: 'rgba(0,0,0,0.2)',
                flexShrink: 0
            }}>
                <MessageSquare size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Chat</span>
            </div>

            {/* Messages Area */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--space-4)'
            }}>
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
                            width: '4rem',
                            height: '4rem',
                            background: 'var(--glass-bg)',
                            backdropFilter: 'var(--glass-blur)',
                            borderRadius: '30%',
                            border: '1px solid var(--glass-border)',
                            marginBottom: 'var(--space-4)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 0 40px rgba(139, 92, 246, 0.2)'
                        }}>
                            <div style={{
                                width: '2rem',
                                height: '2rem',
                                borderRadius: '50%',
                                background: 'var(--gradient-primary)',
                                boxShadow: '0 0 20px var(--color-dhg-primary)'
                            }} />
                        </div>
                        <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, margin: 0 }}>
                            Factory Intelligence Online
                        </h3>
                        <p style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)', opacity: 0.7 }}>
                            Start a conversation to begin orchestration.
                        </p>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, index) => (
                            <MessageBubble key={index} message={msg} />
                        ))}
                        {isProcessing && <HarmonicLoader />}
                        <div ref={messagesEndRef} />
                    </>
                )}
            </div>

            {/* Input Area */}
            <div style={{
                padding: 'var(--space-4)',
                borderTop: '1px solid var(--glass-border)',
                background: 'rgba(0,0,0,0.1)',
                flexShrink: 0
            }}>
                <div style={{
                    display: 'flex',
                    gap: 'var(--space-2)',
                    alignItems: 'flex-end'
                }}>
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type your message..."
                        disabled={isProcessing}
                        rows={3}
                        style={{
                            flex: 1,
                            resize: 'none',
                            padding: 'var(--space-3)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            background: 'var(--color-surface-panel)',
                            color: '#ffffff',
                            caretColor: '#ffffff',
                            fontSize: 'var(--text-sm)',
                            lineHeight: '1.5',
                            outline: 'none'
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!inputValue.trim() || isProcessing}
                        style={{
                            padding: 'var(--space-3)',
                            borderRadius: 'var(--radius-md)',
                            background: inputValue.trim() ? 'var(--gradient-primary)' : 'var(--glass-bg)',
                            border: '1px solid var(--glass-border)',
                            color: 'white',
                            cursor: inputValue.trim() ? 'pointer' : 'not-allowed',
                            opacity: inputValue.trim() ? 1 : 0.5
                        }}
                    >
                        <Send size={20} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ChatPanel;
