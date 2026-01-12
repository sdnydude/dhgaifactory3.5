import React from 'react';
import { motion } from 'framer-motion';

const MessageBubble = ({ message }) => {
    const isUser = message.role === 'user';
    const isStreaming = message.isStreaming;
    const isArtifact = message.isArtifact;

    return (
        <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
            <div className={`flex max-w-[85%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

                {/* Avatar */}
                <div className={`w-8 h-8 rounded-full flex-shrink-0 flex items-center justify-center text-[10px] font-bold 
                    ${isUser ? 'bg-indigo-600 text-white shadow-lg' : 'bg-gradient-to-br from-violet-600 to-indigo-700 text-white shadow-lg'}`}>
                    {isUser ? 'ME' : 'AI'}
                </div>

                {/* Content */}
                <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                    <div className="text-[10px] uppercase tracking-wider font-semibold text-gray-500 mb-1 px-1">
                        {isUser ? 'User Strategy' : 'Factory Intelligence'}
                    </div>
                    <div className={`rounded-2xl px-5 py-3 text-[14px] leading-relaxed shadow-md backdrop-blur-md
                        ${isUser
                            ? 'bg-indigo-600 text-white'
                            : isArtifact
                                ? 'bg-[#1a1a1a] border border-violet-500/30 text-gray-100'
                                : 'bg-[#111111] border border-white/10 text-gray-200'
                        } ${isStreaming ? 'animate-pulse' : ''}`}>
                        {message.content}

                        {isArtifact && (
                            <div className="mt-3 pt-3 border-t border-white/10 flex items-center justify-between text-[10px] text-gray-400">
                                <span className="flex items-center gap-1">
                                    <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                                    Generated Artifact
                                </span>
                                <span className="font-mono">{message.title || 'composition.md'}</span>
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default MessageBubble;
