import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { PanelRightClose, PanelRightOpen, Settings, Sliders } from 'lucide-react';

const MainLayout = () => {
    const [rightPanelOpen, setRightPanelOpen] = useState(false);
    const [rightPanelContent, setRightPanelContent] = useState('prompt-tools');

    const toggleRightPanel = () => setRightPanelOpen(!rightPanelOpen);

    return (
        <div className="main-layout">
            <Sidebar onNewChat={() => { }} />

            <div className="main-layout__content">
                <header className="main-layout__header">
                    <div className="main-layout__brand">
                        <div className="main-layout__brand-title">Digital Harmony Group</div>
                        <div className="main-layout__brand-subtitle">AI Factory Studio</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <button
                            onClick={toggleRightPanel}
                            style={{
                                padding: 'var(--space-2)',
                                borderRadius: 'var(--radius-md)',
                                backgroundColor: rightPanelOpen ? 'var(--color-surface)' : 'transparent',
                                color: rightPanelOpen ? 'var(--color-text)' : 'var(--color-text-muted)',
                                transition: 'all var(--transition-fast)'
                            }}
                            title="Toggle Right Panel"
                        >
                            {rightPanelOpen ? <PanelRightClose size={20} /> : <PanelRightOpen size={20} />}
                        </button>
                    </div>
                </header>

                <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                    <Outlet context={{ setRightPanelOpen, setRightPanelContent }} />
                </div>
            </div>

            {/* Right Panel */}
            <div
                style={{
                    backgroundColor: 'var(--color-paper)',
                    borderLeft: '1px solid var(--color-border)',
                    transition: 'all var(--transition-base)',
                    display: 'flex',
                    flexDirection: 'column',
                    width: rightPanelOpen ? '20rem' : '0',
                    transform: rightPanelOpen ? 'translateX(0)' : 'translateX(100%)',
                    opacity: rightPanelOpen ? 1 : 0,
                    overflow: rightPanelOpen ? 'visible' : 'hidden'
                }}
            >
                <div style={{
                    height: '3.5rem',
                    borderBottom: '1px solid var(--color-border)',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '0 var(--space-4)',
                    fontWeight: 500,
                    fontSize: 'var(--text-sm)',
                    color: 'var(--color-text-muted)'
                }}>
                    {rightPanelContent === 'prompt-tools' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <Sliders size={16} /> Prompt Tools
                        </div>
                    )}
                    {rightPanelContent === 'settings' && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <Settings size={16} /> Settings
                        </div>
                    )}
                </div>

                <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
                    {rightPanelContent === 'prompt-tools' && (
                        <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', textAlign: 'center', marginTop: 'var(--space-12)' }}>
                            Prompt Checker and Refiner tools will appear here.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default MainLayout;
