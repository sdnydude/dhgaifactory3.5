import React from 'react';
import { motion } from 'framer-motion';

const MessageBubble = ({ message }) => {
    const isUser = message.role === 'user';

    return (
        <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-6`}>
            <div className={`flex max-w-[80%] gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>

                {/* Avatar */}
                <div className={`w-8 h-8 rounded-sm flex-shrink-0 flex items-center justify-center text-xs font-medium 
          ${isUser ? 'bg-gray-500 text-white' : 'bg-[#d94838] text-white'}`}>
                    {isUser ? 'ME' : 'AI'}
                </div>

                {/* Content */}
                <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                    <div className="text-sm font-medium text-gray-500 mb-1">{isUser ? 'You' : 'DHG AI Factory'}</div>
                    <div className={`rounded-xl px-4 py-3 text-[15px] leading-relaxed shadow-sm
            ${isUser ? 'bg-[#f4f4f4] text-gray-800' : 'bg-white border border-gray-100 text-gray-800'}`}>
                        {message.content}
                    </div>
                </div>

            </div>
        </div>
    );
};

export default MessageBubble;
