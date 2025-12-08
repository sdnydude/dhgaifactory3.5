import React, { useState, useRef, useEffect } from 'react';
import MessageBubble from './MessageBubble';
import { Send, Paperclip } from 'lucide-react';
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
        <div className="flex-1 flex flex-col h-full relative bg-dhg-surface/50">
            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6">
                {messages.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center text-dhg-muted opacity-60">
                        <div className="w-16 h-16 bg-white rounded-2xl shadow-sm border border-gray-100 mb-4 flex items-center justify-center">
                            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-dhg-primary to-dhg-accent"></div>
                        </div>
                        <p className="text-lg font-medium font-serif text-dhg-nav">Start a new composition</p>
                        <p className="text-sm">Collaborate with the AI Factory</p>
                    </div>
                ) : (
                    <>
                        {messages.map((msg, index) => (
                            <MessageBubble key={index} message={msg} />
                        ))}

                        {/* Processing Indicator */}
                        {isProcessing && (
                            <div className="flex justify-start animate-fade-in">
                                <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none p-4 shadow-sm flex items-center gap-3">
                                    <div className="w-6 h-6 rounded-full bg-dhg-primary/10 flex items-center justify-center text-[10px] font-bold text-dhg-primary">
                                        AI
                                    </div>
                                    <div className="flex flex-col gap-1">
                                        <div className="text-xs font-semibold text-dhg-muted uppercase tracking-wide">Harmonizing...</div>
                                        <HarmonicLoader />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </>
                )}
            </div>

            {/* Input Area */}
            <div className="p-4 bg-white/80 backdrop-blur border-t border-gray-100">
                <div className="max-w-4xl mx-auto relative rounded-xl border border-gray-200 shadow-sm bg-white focus-within:ring-2 focus-within:ring-dhg-primary/20 focus-within:border-dhg-primary transition-all duration-200">
                    <textarea
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Describe your vision..."
                        className="w-full p-4 pr-24 max-h-48 min-h-[60px] resize-none outline-none text-dhg-text placeholder-dhg-muted/50 bg-transparent rounded-xl font-sans"
                        rows={1}
                    />

                    <div className="absolute right-2 bottom-2 flex items-center gap-1">
                        <button className="p-2 text-dhg-muted hover:text-dhg-primary hover:bg-dhg-surface rounded-lg transition-colors" title="Attach context">
                            <Paperclip size={20} />
                        </button>
                        <button
                            onClick={handleSend}
                            disabled={!inputValue.trim() || isProcessing}
                            className={`p-2 rounded-lg transition-all duration-200 ${inputValue.trim() && !isProcessing
                                    ? 'bg-dhg-nav text-white hover:bg-slate-800 shadow-md'
                                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                                }`}
                        >
                            <Send size={18} />
                        </button>
                    </div>
                </div>
                <div className="text-center mt-2">
                    <p className="text-[10px] text-dhg-muted">Digital Harmony Group AI • Tuning innovation to the rhythm of humanity</p>
                </div>
            </div>
        </div>
    );
};

export default ChatArea;
