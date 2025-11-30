// DHG AI Factory - Chat Panel Component
// Real-time chat interface with the Orchestrator agent

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Paperclip, 
  Bot, 
  User, 
  Loader,
  Sparkles,
  MessageSquare
} from 'lucide-react';
import { cn } from '../lib/utils';
import { useAppStore, selectMessages, selectIsConnected } from '../store/useAppStore';
import { useWebSocket } from '../hooks/useAgentWebSocket';
import { ChatMessage, AgentId, AGENT_CONFIGS } from '../types';

// ============================================================================
// TYPES
// ============================================================================

interface ChatPanelProps {
  className?: string;
  requestId?: string;
}

interface MessageBubbleProps {
  message: ChatMessage;
  isLast: boolean;
}

interface SuggestionChipProps {
  text: string;
  onClick: () => void;
}

// ============================================================================
// SUGGESTION CHIP COMPONENT
// ============================================================================

const SuggestionChip: React.FC<SuggestionChipProps> = ({ text, onClick }) => (
  <button
    onClick={onClick}
    className={cn(
      'px-3 py-1.5 text-xs font-medium rounded-full',
      'bg-blue-50 text-blue-700 hover:bg-blue-100',
      'border border-blue-200 hover:border-blue-300',
      'transition-all duration-200',
      'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1'
    )}
  >
    {text}
  </button>
);

// ============================================================================
// MESSAGE BUBBLE COMPONENT
// ============================================================================

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, isLast }) => {
  const isUser = message.role === 'user';
  const agentConfig = message.agent_id ? AGENT_CONFIGS[message.agent_id] : null;
  
  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true
    });
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'flex gap-2 max-w-[85%]',
        isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
      )}
    >
      {/* Avatar */}
      <div className={cn(
        'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
        isUser 
          ? 'bg-blue-600' 
          : agentConfig 
            ? 'text-white' 
            : 'bg-gray-200'
      )}
      style={agentConfig ? { backgroundColor: agentConfig.color } : undefined}
      >
        {isUser ? (
          <User className="w-4 h-4 text-white" />
        ) : agentConfig ? (
          <span className="text-sm">{agentConfig.icon}</span>
        ) : (
          <Bot className="w-4 h-4 text-gray-600" />
        )}
      </div>
      
      {/* Message Content */}
      <div className="flex flex-col gap-1">
        {/* Agent Name (for agent messages) */}
        {!isUser && agentConfig && (
          <span className="text-xs font-medium text-gray-500 ml-1">
            {agentConfig.name}
          </span>
        )}
        
        {/* Bubble */}
        <div className={cn(
          'px-4 py-2.5 rounded-2xl',
          isUser 
            ? 'bg-blue-600 text-white rounded-tr-sm' 
            : 'bg-white border border-gray-200 text-gray-900 rounded-tl-sm'
        )}>
          <p className="text-sm whitespace-pre-wrap break-words">
            {message.content}
          </p>
        </div>
        
        {/* Timestamp */}
        <span className={cn(
          'text-[10px] text-gray-400',
          isUser ? 'text-right mr-1' : 'ml-1'
        )}>
          {formatTime(message.timestamp)}
        </span>
        
        {/* Suggestions (for agent messages) */}
        {!isUser && message.suggestions && message.suggestions.length > 0 && isLast && (
          <div className="flex flex-wrap gap-2 mt-2">
            {message.suggestions.map((suggestion, idx) => (
              <SuggestionChip 
                key={idx} 
                text={suggestion}
                onClick={() => {/* Will be handled by parent */}}
              />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
};

// ============================================================================
// TYPING INDICATOR COMPONENT
// ============================================================================

const TypingIndicator: React.FC<{ agentId?: AgentId }> = ({ agentId }) => {
  const agentConfig = agentId ? AGENT_CONFIGS[agentId] : null;
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className="flex items-center gap-2 max-w-[85%] mr-auto"
    >
      <div 
        className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
        style={{ backgroundColor: agentConfig?.color || '#6B7280' }}
      >
        {agentConfig ? (
          <span className="text-sm">{agentConfig.icon}</span>
        ) : (
          <Bot className="w-4 h-4 text-white" />
        )}
      </div>
      
      <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
        <div className="flex gap-1">
          <motion.span 
            className="w-2 h-2 bg-gray-400 rounded-full"
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: 0 }}
          />
          <motion.span 
            className="w-2 h-2 bg-gray-400 rounded-full"
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: 0.15 }}
          />
          <motion.span 
            className="w-2 h-2 bg-gray-400 rounded-full"
            animate={{ y: [0, -4, 0] }}
            transition={{ duration: 0.6, repeat: Infinity, delay: 0.3 }}
          />
        </div>
      </div>
    </motion.div>
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const ChatPanel: React.FC<ChatPanelProps> = ({ className, requestId }) => {
  const messages = useAppStore(selectMessages);
  const isTyping = useAppStore(state => state.isTyping);
  const isConnected = useAppStore(selectIsConnected);
  
  const { sendChatMessage } = useWebSocket();
  
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);
  
  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);
  
  const handleSend = useCallback(async () => {
    if (!inputValue.trim() || isSending || !isConnected) return;
    
    const content = inputValue.trim();
    setInputValue('');
    setIsSending(true);
    
    try {
      // Add user message to store immediately
      useAppStore.getState().addMessage({
        id: `msg_${Date.now()}`,
        timestamp: new Date().toISOString(),
        role: 'user',
        content
      });
      
      // Send via WebSocket
      sendChatMessage(content, requestId);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }, [inputValue, isSending, isConnected, sendChatMessage, requestId]);
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };
  
  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    inputRef.current?.focus();
  };
  
  return (
    <div className={cn('flex flex-col h-full bg-gray-50', className)}>
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-white border-b border-gray-200">
        <div className="flex items-center gap-2">
          <div 
            className="w-8 h-8 rounded-full flex items-center justify-center"
            style={{ backgroundColor: AGENT_CONFIGS.orchestrator.color }}
          >
            <span className="text-sm">{AGENT_CONFIGS.orchestrator.icon}</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">Chat with Orchestrator</h3>
            <div className="flex items-center gap-1.5">
              <div className={cn(
                'w-2 h-2 rounded-full',
                isConnected ? 'bg-green-500' : 'bg-gray-300'
              )} />
              <span className="text-xs text-gray-500">
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-full bg-blue-50 flex items-center justify-center mb-4">
              <MessageSquare className="w-8 h-8 text-blue-500" />
            </div>
            <h4 className="text-sm font-medium text-gray-900 mb-1">
              Start a conversation
            </h4>
            <p className="text-xs text-gray-500 max-w-[200px]">
              Ask questions about your CME content or request modifications
            </p>
            
            {/* Quick Start Suggestions */}
            <div className="flex flex-wrap gap-2 mt-4 justify-center">
              <SuggestionChip 
                text="Generate needs assessment" 
                onClick={() => handleSuggestionClick('Generate a needs assessment for Type 2 diabetes management')}
              />
              <SuggestionChip 
                text="Create curriculum" 
                onClick={() => handleSuggestionClick('Create a curriculum outline for cardiovascular risk management')}
              />
            </div>
          </div>
        ) : (
          <>
            {messages.map((message, idx) => (
              <MessageBubble 
                key={message.id} 
                message={message}
                isLast={idx === messages.length - 1}
              />
            ))}
          </>
        )}
        
        {/* Typing Indicator */}
        <AnimatePresence>
          {isTyping && <TypingIndicator agentId="orchestrator" />}
        </AnimatePresence>
        
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <div className="p-4 bg-white border-t border-gray-200">
        <div className={cn(
          'flex items-end gap-2 rounded-2xl border bg-gray-50 p-2',
          'focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100',
          !isConnected && 'opacity-50 cursor-not-allowed'
        )}>
          {/* Attachment Button */}
          <button 
            className="p-2 text-gray-400 hover:text-gray-600 transition-colors rounded-lg hover:bg-gray-100"
            disabled={!isConnected}
          >
            <Paperclip className="w-5 h-5" />
          </button>
          
          {/* Text Input */}
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isConnected ? "Type a message..." : "Connecting..."}
            disabled={!isConnected}
            rows={1}
            className={cn(
              'flex-1 resize-none bg-transparent border-none outline-none',
              'text-sm text-gray-900 placeholder-gray-400',
              'py-2 max-h-[120px]'
            )}
          />
          
          {/* Send Button */}
          <button
            onClick={handleSend}
            disabled={!inputValue.trim() || isSending || !isConnected}
            className={cn(
              'p-2 rounded-xl transition-all duration-200',
              inputValue.trim() && isConnected
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            )}
          >
            {isSending ? (
              <Loader className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        
        {/* AI Assistance Hint */}
        <div className="flex items-center justify-center gap-1.5 mt-2">
          <Sparkles className="w-3 h-3 text-gray-400" />
          <span className="text-[10px] text-gray-400">
            Powered by LangGraph Multi-Agent System
          </span>
        </div>
      </div>
    </div>
  );
};

export default ChatPanel;
