import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { Send } from 'lucide-react';
import HarmonicLoader from './HarmonicLoader';

const ChatArea = ({ messages, onSendMessage, isProcessing }) => {
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
                        opacity: 0.6
                    }}>
                        <div style={{
                            width: '4rem',
                            height: '4rem',
                            backgroundColor: 'white',
                            borderRadius: 'var(--radius-xl)',
                            boxShadow: 'var(--shadow-sm)',
                            border: '1px solid var(--color-border)',
                            marginBottom: 'var(--space-4)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <div style={{
                                width: '2rem',
                                height: '2rem',
                                borderRadius: '50%',
                                background: 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))'
                            }}></div>
                        </div>
                        <p style={{ fontSize: 'var(--text-lg)', fontWeight: 500, fontFamily: 'var(--font-serif)', color: 'var(--color-dhg-nav)' }}>
                            Start a new composition
                        </p>
                        <p style={{ fontSize: 'var(--text-sm)' }}>Collaborate with the AI Factory</p>
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

            <div className="chat-area__input-container">
                <div className="chat-area__input-wrapper">
                    <input
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Type your message..."
                        className="chat-area__input"
                        disabled={isProcessing}
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
