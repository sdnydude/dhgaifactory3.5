import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { PanelRightClose, PanelRightOpen, Settings, Sliders } from 'lucide-react';

const MainLayout = () => {
    const [rightPanelOpen, setRightPanelOpen] = useState(false);
    const [rightPanelContent, setRightPanelContent] = useState('prompt-tools'); // 'prompt-tools', 'settings', etc.

    const toggleRightPanel = () => setRightPanelOpen(!rightPanelOpen);

    return (
        <div className="flex h-screen w-full bg-white text-gray-900 overflow-hidden">
            {/* Left Sidebar (Navigation) */}
            <Sidebar onNewChat={() => { }} />

            {/* Center (Chat/Content) */}
            <div className="flex-1 flex flex-col min-w-0 transition-all duration-300 bg-dhg-surface">
                <header className="h-16 border-b border-gray-100 flex items-center justify-between px-6 bg-white/80 backdrop-blur-sm z-10 sticky top-0">
                    <div className="flex flex-col">
                        <div className="font-serif font-bold text-xl text-dhg-nav tracking-tight">Digital Harmony Group</div>
                        <div className="text-[10px] uppercase tracking-widest text-dhg-primary font-medium">AI Factory Studio</div>
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={toggleRightPanel}
                            className={`p-2 rounded-lg hover:bg-gray-100 transition-colors ${rightPanelOpen ? 'bg-gray-100 text-gray-900' : 'text-gray-500'}`}
                            title="Toggle Right Panel"
                        >
                            {rightPanelOpen ? <PanelRightClose size={20} /> : <PanelRightOpen size={20} />}
                        </button>
                    </div>
                </header>

                <div className="flex-1 overflow-hidden relative">
                    <Outlet context={{ setRightPanelOpen, setRightPanelContent }} />
                </div>
            </div>

            {/* Right Panel (Context/Tools) */}
            <div
                className={`bg-white border-l border-gray-200 transition-all duration-300 ease-in-out flex flex-col
          ${rightPanelOpen ? 'w-80 translate-x-0' : 'w-0 translate-x-full opacity-0 overflow-hidden'}`}
            >
                <div className="h-14 border-b border-gray-100 flex items-center px-4 font-medium text-sm text-gray-600">
                    {rightPanelContent === 'prompt-tools' && (
                        <div className="flex items-center gap-2"><Sliders size={16} /> Prompt Tools</div>
                    )}
                    {rightPanelContent === 'settings' && (
                        <div className="flex items-center gap-2"><Settings size={16} /> Settings</div>
                    )}
                </div>

                <div className="flex-1 overflow-y-auto p-4">
                    {rightPanelContent === 'prompt-tools' && (
                        <div className="text-sm text-gray-500 text-center mt-10">
                            Prompt Checker and Refiner tools will appear here.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MainLayout;
