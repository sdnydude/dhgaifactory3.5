import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import Sidebar from './Sidebar';
import ModelSelector from './ModelSelector';
import PanelSystem from './PanelSystem';
import { PanelProvider, usePanels } from '../context/PanelContext';
import { Layout, MessageSquare, Sliders, FileText, Activity, RotateCcw } from 'lucide-react';
import { useStudio } from '../context/StudioContext';

const PANEL_ICONS = {
    chat: MessageSquare,
    tools: Sliders,
    artifacts: FileText,
    agentStatus: Activity
};

const PANEL_LABELS = {
    chat: 'Chat',
    tools: 'Tools',
    artifacts: 'Artifacts',
    agentStatus: 'Agents'
};

const PanelToggleButton = ({ panelId }) => {
    const { togglePanel, isPanelOpen } = usePanels();
    const isOpen = isPanelOpen(panelId);
    const Icon = PANEL_ICONS[panelId];

    return (
        <button
            onClick={() => togglePanel(panelId)}
            style={{
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-md)',
                backgroundColor: isOpen ? 'var(--color-surface-panel)' : 'transparent',
                color: isOpen ? 'var(--color-text)' : 'var(--color-text-muted)',
                border: isOpen ? '1px solid var(--glass-border)' : '1px solid transparent',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                transition: 'all var(--transition-fast)',
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                cursor: 'pointer'
            }}
            title={`Toggle ${PANEL_LABELS[panelId]}`}
        >
            <Icon size={14} />
            <span>{PANEL_LABELS[panelId]}</span>
        </button>
    );
};

const MainLayoutInner = ({ messages, onSendMessage, isProcessing }) => {
    const { selectedModel, setSelectedModel } = useStudio();
    const { resetLayout, availablePanels } = usePanels();
    const location = useLocation();

    const isStudioPage = location.pathname === '/chat' || location.pathname === '/';

    return (
        <div className="main-layout" style={{ background: 'var(--gradient-body)', minHeight: '100vh' }}>
            <Sidebar onNewChat={() => { }} />

            <div className="main-layout__content">
                <header className="main-layout__header" style={{
                    borderBottom: '1px solid var(--glass-border)',
                    background: 'var(--glass-bg)',
                    backdropFilter: 'var(--glass-blur)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                        <div className="main-layout__brand">
                            <div className="main-layout__brand-title" style={{ color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                <Layout size={24} style={{ color: 'var(--color-dhg-primary)' }} />
                                Digital Harmony Group
                            </div>
                            <div className="main-layout__brand-subtitle">AI Factory Studio V3.5</div>
                        </div>

                        <div style={{ width: '1px', height: '24px', background: 'var(--glass-border)' }} />

                        <ModelSelector
                            selectedModel={selectedModel}
                            onSelectModel={setSelectedModel}
                        />
                    </div>

                    {isStudioPage && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            {availablePanels.map(panelId => (
                                <PanelToggleButton key={panelId} panelId={panelId} />
                            ))}
                            <div style={{ width: '1px', height: '20px', background: 'var(--glass-border)', margin: '0 var(--space-2)' }} />
                            <button
                                onClick={resetLayout}
                                style={{
                                    padding: 'var(--space-2)',
                                    borderRadius: 'var(--radius-md)',
                                    background: 'transparent',
                                    border: '1px solid transparent',
                                    color: 'var(--color-text-muted)',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center'
                                }}
                                title="Reset Layout"
                            >
                                <RotateCcw size={14} />
                            </button>
                        </div>
                    )}
                </header>

                <div style={{ flex: 1, overflow: 'hidden', position: 'relative', padding: 'var(--space-2)' }}>
                    {isStudioPage ? (
                        <PanelSystem
                            messages={messages}
                            onSendMessage={onSendMessage}
                            isProcessing={isProcessing}
                        />
                    ) : (
                        <Outlet />
                    )}
                </div>
            </div>
        </div>
    );
};

const MainLayout = (props) => {
    return (
        <PanelProvider>
            <MainLayoutInner {...props} />
        </PanelProvider>
    );
};

export default MainLayout;
