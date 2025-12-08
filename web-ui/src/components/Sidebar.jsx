import React from 'react';
import { Plus, MessageSquare, Settings, Shield, User } from 'lucide-react';
import { Link } from 'react-router-dom';

const Sidebar = ({ onNewChat }) => {
    return (
        <div className="w-64 bg-dhg-surface border-r border-gray-100 h-screen flex flex-col font-sans text-dhg-text">
            <div className="p-4">
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center justify-center gap-2 bg-dhg-nav hover:bg-slate-800 text-white px-4 py-3 rounded-xl transition-all shadow-sm hover:shadow-md font-medium text-sm group"
                >
                    <Plus size={18} className="text-dhg-primary group-hover:text-white transition-colors" />
                    <span>New Composition</span>
                </button>
            </div>

            <div className="flex-1 overflow-y-auto px-2">
                <div className="text-[11px] font-bold text-gray-400 px-3 py-2 uppercase tracking-wider">Recents</div>
                <div className="space-y-0.5">
                    <Link to="/chat" className="block w-full text-left px-3 py-2 rounded-lg hover:bg-gray-200 text-sm truncate transition-colors">
                        CME Needs Assessment
                    </Link>
                    <Link to="/chat" className="block w-full text-left px-3 py-2 rounded-lg hover:bg-gray-200 text-sm truncate transition-colors">
                        Non-CME Strategy
                    </Link>
                </div>
            </div>

            <div className="p-2 space-y-0.5 border-t border-gray-200">
                <Link to="/admin" className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-200 text-sm transition-colors">
                    <Shield size={16} />
                    <div>Admin Panel</div>
                </Link>
                <Link to="/settings" className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-200 text-sm transition-colors">
                    <Settings size={16} />
                    <div>Settings</div>
                </Link>
            </div>

            <div className="p-3 border-t border-gray-200">
                <div className="flex items-center gap-2 px-2 py-1">
                    <div className="w-6 h-6 rounded-full bg-purple-600 flex items-center justify-center text-white text-xs font-medium">SW</div>
                    <div className="flex-1 text-left overflow-hidden">
                        <div className="font-medium text-sm truncate">swebber64</div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Sidebar;
