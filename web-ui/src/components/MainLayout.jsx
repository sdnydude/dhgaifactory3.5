import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import ModelSelector from './ModelSelector';
import PromptRefiner from './panels/PromptRefiner';
import { PanelRightClose, PanelRightOpen, Settings, Sliders, Layout } from 'lucide-react';
import { useStudio } from '../context/StudioContext';

const MainLayout = () => {
    const {
        rightPanelOpen,
        setRightPanelOpen,
        rightPanelContent,
        selectedModel,
        setSelectedModel
    } = useStudio();

    const toggleRightPanel = () => setRightPanelOpen(!rightPanelOpen);

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

                        {/* Vertical Divider */}
                        <div style={{ width: '1px', height: '24px', background: 'var(--glass-border)' }}></div>

                        <ModelSelector
                            selectedModel={selectedModel}
                            onSelectModel={setSelectedModel}
                        />
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <button
                            onClick={toggleRightPanel}
                            style={{
                                padding: 'var(--space-2) var(--space-4)',
                                borderRadius: 'var(--radius-md)',
                                backgroundColor: rightPanelOpen ? 'var(--color-surface-panel)' : 'var(--glass-bg)',
                                color: rightPanelOpen ? 'var(--color-text)' : 'var(--color-text-muted)',
                                border: '1px solid var(--glass-border)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-2)',
                                transition: 'all var(--transition-fast)',
                                fontSize: 'var(--text-xs)',
                                fontWeight: 500
                            }}
                            title="Toggle Utility Cockpit"
                        >
                            <Sliders size={18} />
                            Cockpit Tools
                            {rightPanelOpen ? <PanelRightClose size={16} /> : <PanelRightOpen size={16} />}
                        </button>
                    </div>
                </header>

                <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                    <Outlet />
                </div>
            </div>

            {/* Right Panel / Cockpit Tools */}
            <div
                style={{
                    backgroundColor: 'var(--glass-bg)',
                    backdropFilter: 'var(--glass-blur)',
                    borderLeft: '1px solid var(--glass-border)',
                    transition: 'all var(--transition-base)',
                    display: 'flex',
                    flexDirection: 'column',
                    width: rightPanelOpen ? '22rem' : '0',
                    transform: rightPanelOpen ? 'translateX(0)' : 'translateX(100%)',
                    opacity: rightPanelOpen ? 1 : 0,
                    overflow: rightPanelOpen ? 'visible' : 'hidden',
                    position: 'relative',
                    zIndex: 10,
                    boxShadow: '-8px 0 32px rgba(0,0,0,0.3)'
                }}
            >
                <div style={{
                    height: '5rem',
                    borderBottom: '1px solid var(--glass-border)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '0 var(--space-4)',
                    fontWeight: 600,
                    fontSize: 'var(--text-sm)',
                    color: 'var(--color-text)',
                    background: 'rgba(0,0,0,0.2)'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <Sliders size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                        Operational Cockpit
                    </div>

                    <button onClick={toggleRightPanel} style={{ color: 'var(--color-text-muted)' }}>
                        <PanelRightClose size={16} />
                    </button>
                </div>

                <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
                    <PromptRefiner />

                    {rightPanelContent === 'settings' && (
                        <div style={{
                            marginTop: 'var(--space-6)',
                            padding: 'var(--space-4)',
                            background: 'var(--color-surface-panel)',
                            borderRadius: 'var(--radius-lg)',
                            border: '1px solid var(--glass-border)'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
                                <Settings size={16} />
                                <span style={{ fontWeight: 600 }}>Quick Settings</span>
                            </div>
                            {/* Settings content would go here */}
                            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                                Settings configuration available in the full settings page.
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
export default MainLayout;
