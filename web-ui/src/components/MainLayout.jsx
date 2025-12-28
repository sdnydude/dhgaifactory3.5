import React, { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { Link } from 'react-router-dom';
import ModelSelector from './ModelSelector';
import PromptRefiner from './panels/PromptRefiner';
import {
    PanelRightClose, PanelRightOpen, PanelLeftClose, PanelLeftOpen,
    Settings, Sliders, Layout, Activity, FileText, History,
    Zap, Search, MessageSquare, Bot, Upload, Link2, Mic,
    Code, GitBranch, Database, ChevronDown, Plus, Shield
} from 'lucide-react';
import { useStudio } from '../context/StudioContext';

const ResizeHandle = () => (
    <PanelResizeHandle style={{
        width: '8px',
        background: 'transparent',
        cursor: 'col-resize',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative'
    }}>
        <div style={{
            width: '3px',
            height: '48px',
            background: 'linear-gradient(180deg, transparent, var(--color-dhg-primary), transparent)',
            borderRadius: '3px',
            opacity: 0.5,
            transition: 'opacity 0.2s, width 0.2s'
        }} />
    </PanelResizeHandle>
);

const PanelTabs = ({ tabs, activeTab, onTabChange }) => (
    <div style={{
        display: 'flex',
        gap: '2px',
        padding: 'var(--space-2) var(--space-3)',
        borderBottom: '1px solid var(--glass-border)',
        background: 'rgba(0,0,0,0.2)',
        overflowX: 'auto',
        flexShrink: 0
    }}>
        {tabs.map(tab => (
            <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                style={{
                    padding: 'var(--space-2) var(--space-3)',
                    borderRadius: 'var(--radius-sm)',
                    background: activeTab === tab.id ? 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))' : 'transparent',
                    color: activeTab === tab.id ? 'white' : 'var(--color-text-muted)',
                    border: 'none',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    whiteSpace: 'nowrap',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                }}
            >
                {tab.icon && <tab.icon size={12} />}
                {tab.label}
            </button>
        ))}
    </div>
);

const ViewSelector = ({ views, activeView, onViewChange }) => {
    const [isOpen, setIsOpen] = useState(false);
    const currentView = views.find(v => v.id === activeView);

    return (
        <div style={{ position: 'relative' }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    padding: 'var(--space-2) var(--space-3)',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--glass-bg)',
                    color: 'var(--color-text)',
                    border: '1px solid var(--glass-border)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 500,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)'
                }}
            >
                {currentView?.icon && <currentView.icon size={14} />}
                {currentView?.label}
                <ChevronDown size={12} />
            </button>
            {isOpen && (
                <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    marginTop: 'var(--space-1)',
                    background: 'var(--color-surface-panel)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-md)',
                    padding: 'var(--space-2)',
                    zIndex: 100,
                    minWidth: '160px',
                    boxShadow: '0 8px 32px rgba(0,0,0,0.3)'
                }}>
                    {views.map(view => (
                        <button
                            key={view.id}
                            onClick={() => { onViewChange(view.id); setIsOpen(false); }}
                            style={{
                                width: '100%',
                                padding: 'var(--space-2) var(--space-3)',
                                borderRadius: 'var(--radius-sm)',
                                background: activeView === view.id ? 'var(--glass-bg)' : 'transparent',
                                color: 'var(--color-text)',
                                border: 'none',
                                fontSize: 'var(--text-xs)',
                                cursor: 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-2)',
                                textAlign: 'left'
                            }}
                        >
                            {view.icon && <view.icon size={14} />}
                            {view.label}
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
};

const ChatTabContent = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)' }}>
            Recent Conversations
        </div>
        {['CME Needs Assessment', 'Non-CME Strategy', 'Medical Research Query', 'Curriculum Design'].map((chat, i) => (
            <Link to="/chat" key={i} style={{
                display: 'block',
                padding: 'var(--space-3)',
                background: i === 0 ? 'var(--glass-bg)' : 'transparent',
                borderRadius: 'var(--radius-md)',
                border: i === 0 ? '1px solid var(--glass-border)' : 'none',
                marginBottom: 'var(--space-1)',
                cursor: 'pointer',
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text)',
                textDecoration: 'none'
            }}>
                <MessageSquare size={12} style={{ marginRight: '8px', opacity: 0.5 }} />
                {chat}
            </Link>
        ))}
    </div>
);

const AgentsTabContent = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)' }}>
            Select AI Agent
        </div>
        {[
            { name: 'Medical LLM', desc: 'Healthcare & clinical', status: 'online' },
            { name: 'Research', desc: 'Literature & data', status: 'online' },
            { name: 'Curriculum', desc: 'Training design', status: 'online' },
            { name: 'Outcomes', desc: 'Analytics & metrics', status: 'idle' },
            { name: 'QA/Compliance', desc: 'Regulatory review', status: 'online' },
            { name: 'Competitor Intel', desc: 'Market analysis', status: 'offline' }
        ].map(agent => (
            <div key={agent.name} style={{
                padding: 'var(--space-3)',
                background: 'var(--color-surface-panel)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--glass-border)',
                marginBottom: 'var(--space-2)',
                cursor: 'pointer'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                        <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)' }}>{agent.name}</div>
                        <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>{agent.desc}</div>
                    </div>
                    <span style={{
                        fontSize: '10px',
                        color: agent.status === 'online' ? 'var(--color-success)' : agent.status === 'idle' ? 'var(--color-warning)' : 'var(--color-error)'
                    }}>●</span>
                </div>
            </div>
        ))}
    </div>
);

const HistoryTabContent = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)' }}>
            Compositions & Sessions
        </div>
        {['Project Alpha', 'Research Bundle', 'Training Series'].map((item, i) => (
            <div key={i} style={{
                padding: 'var(--space-3)',
                background: 'var(--color-surface-panel)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--glass-border)',
                marginBottom: 'var(--space-2)',
                cursor: 'pointer'
            }}>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text)' }}>{item}</div>
                <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '4px' }}>3 linked sessions</div>
            </div>
        ))}
    </div>
);

const StatusTabContent = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)' }}>
            System Health
        </div>
        <div style={{ display: 'grid', gap: 'var(--space-2)' }}>
            {[
                { label: 'Orchestrator', value: 'Connected', color: 'var(--color-success)' },
                { label: 'Agents Online', value: '5/6', color: 'var(--color-warning)' },
                { label: 'Queue Depth', value: '0', color: 'var(--color-success)' },
                { label: 'Avg Response', value: '1.2s', color: 'var(--color-success)' }
            ].map(stat => (
                <div key={stat.label} style={{
                    padding: 'var(--space-3)',
                    background: 'var(--color-surface-panel)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--glass-border)',
                    display: 'flex',
                    justifyContent: 'space-between'
                }}>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>{stat.label}</span>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: stat.color }}>{stat.value}</span>
                </div>
            ))}
        </div>
    </div>
);

const PromptCheckerTool = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', marginBottom: 'var(--space-3)' }}>
            Prompt Checker
        </div>
        <textarea
            placeholder="Paste your prompt here to analyze..."
            style={{
                width: '100%',
                height: '120px',
                padding: 'var(--space-3)',
                background: 'var(--color-surface-panel)',
                border: '1px solid var(--glass-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontSize: 'var(--text-xs)',
                resize: 'vertical',
                marginBottom: 'var(--space-3)'
            }}
        />
        <button style={{
            width: '100%',
            padding: 'var(--space-2)',
            background: 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))',
            color: 'white',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            cursor: 'pointer'
        }}>
            Analyze Prompt
        </button>
    </div>
);

const TranscriptionTool = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', marginBottom: 'var(--space-3)' }}>
            Transcription Engine
        </div>
        <div style={{ marginBottom: 'var(--space-3)' }}>
            <label style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', display: 'block', marginBottom: 'var(--space-1)' }}>
                Media URL
            </label>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <input
                    type="text"
                    placeholder="https://..."
                    style={{
                        flex: 1,
                        padding: 'var(--space-2)',
                        background: 'var(--color-surface-panel)',
                        border: '1px solid var(--glass-border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--color-text)',
                        fontSize: 'var(--text-xs)'
                    }}
                />
                <button style={{
                    padding: 'var(--space-2)',
                    background: 'var(--glass-bg)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-text)',
                    cursor: 'pointer'
                }}>
                    <Link2 size={14} />
                </button>
            </div>
        </div>
        <div style={{ marginBottom: 'var(--space-3)' }}>
            <label style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', display: 'block', marginBottom: 'var(--space-1)' }}>
                Project Options
            </label>
            <select style={{
                width: '100%',
                padding: 'var(--space-2)',
                background: 'var(--color-surface-panel)',
                border: '1px solid var(--glass-border)',
                borderRadius: 'var(--radius-md)',
                color: 'var(--color-text)',
                fontSize: 'var(--text-xs)'
            }}>
                <option>Medical Transcription</option>
                <option>Interview</option>
                <option>Lecture</option>
                <option>Meeting Notes</option>
            </select>
        </div>
        <button style={{
            width: '100%',
            padding: 'var(--space-2)',
            background: 'var(--glass-bg)',
            border: '1px solid var(--glass-border)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-xs)',
            color: 'var(--color-text)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 'var(--space-2)'
        }}>
            <Mic size={14} />
            Start Transcription
        </button>
    </div>
);

const MediaUploadTool = () => (
    <div style={{ padding: 'var(--space-4)' }}>
        <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', marginBottom: 'var(--space-3)' }}>
            Media Upload
        </div>
        <div style={{
            padding: 'var(--space-6)',
            background: 'var(--color-surface-panel)',
            border: '2px dashed var(--glass-border)',
            borderRadius: 'var(--radius-md)',
            textAlign: 'center',
            cursor: 'pointer'
        }}>
            <Upload size={24} style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }} />
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                Drop files here or click to upload
            </div>
            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginTop: 'var(--space-1)' }}>
                MP3, MP4, WAV, PDF
            </div>
        </div>
    </div>
);

const LEFT_TABS = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'agents', label: 'Agents', icon: Bot },
    { id: 'history', label: 'History', icon: History },
    { id: 'status', label: 'Status', icon: Activity }
];

const RIGHT_TABS = [
    { id: 'prompt', label: 'Prompt', icon: Sliders },
    { id: 'transcribe', label: 'Transcribe', icon: Mic },
    { id: 'upload', label: 'Upload', icon: Upload }
];

const CENTER_VIEWS = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'ide', label: 'IDE', icon: Code },
    { id: 'langgraph', label: 'LangGraph', icon: GitBranch },
    { id: 'registry', label: 'Registry', icon: Database }
];

const LeftPanelContent = ({ activeTab }) => {
    switch (activeTab) {
        case 'chat': return <ChatTabContent />;
        case 'agents': return <AgentsTabContent />;
        case 'history': return <HistoryTabContent />;
        case 'status': return <StatusTabContent />;
        default: return <ChatTabContent />;
    }
};

const RightPanelContent = ({ activeTab }) => {
    switch (activeTab) {
        case 'prompt': return <PromptCheckerTool />;
        case 'transcribe': return <TranscriptionTool />;
        case 'upload': return <MediaUploadTool />;
        default: return <PromptCheckerTool />;
    }
};

const CenterViewContent = ({ activeView }) => {
    if (activeView === 'chat') return <Outlet />;
    return (
        <div style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-muted)'
        }}>
            <div style={{ textAlign: 'center' }}>
                {activeView === 'ide' && <Code size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-4)' }} />}
                {activeView === 'langgraph' && <GitBranch size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-4)' }} />}
                {activeView === 'registry' && <Database size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-4)' }} />}
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 600 }}>
                    {activeView === 'ide' && 'IDE View'}
                    {activeView === 'langgraph' && 'LangGraph View'}
                    {activeView === 'registry' && 'Registry View'}
                </div>
                <div style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>Coming soon</div>
            </div>
        </div>
    );
};

const MainLayout = () => {
    const { selectedModel, setSelectedModel } = useStudio();
    const location = useLocation();
    const isStudioPage = location.pathname === '/chat' || location.pathname === '/';

    const [showLeftPanel, setShowLeftPanel] = useState(true);
    const [showRightPanel, setShowRightPanel] = useState(true);
    const [leftTab, setLeftTab] = useState('agents');
    const [rightTab, setRightTab] = useState('prompt');
    const [centerView, setCenterView] = useState('chat');

    const glassPanelStyle = (side) => ({
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--glass-bg)',
        backdropFilter: 'var(--glass-blur)',
        boxShadow: side === 'left'
            ? 'inset -12px 0 24px rgba(0,0,0,0.15), 4px 0 16px rgba(0,0,0,0.1)'
            : 'inset 12px 0 24px rgba(0,0,0,0.15), -4px 0 16px rgba(0,0,0,0.1)'
    });

    return (
        <div className="main-layout" style={{ background: 'var(--gradient-body)', minHeight: '100vh' }}>
            <div className="main-layout__content" style={{ display: 'flex', flexDirection: 'column', marginLeft: 0 }}>
                <header className="main-layout__header" style={{
                    borderBottom: '1px solid var(--glass-border)',
                    background: 'var(--glass-bg)',
                    backdropFilter: 'var(--glass-blur)',
                    flexShrink: 0
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                        <div className="main-layout__brand">
                            <div className="main-layout__brand-title" style={{ color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                <Layout size={24} style={{ color: 'var(--color-dhg-primary)' }} />
                                Digital Harmony Group
                            </div>
                            <div className="main-layout__brand-subtitle">AI Factory Studio V3.5</div>
                        </div>
                        <div style={{ width: '1px', height: '24px', background: 'var(--glass-border)' }}></div>
                        <ModelSelector selectedModel={selectedModel} onSelectModel={setSelectedModel} />
                        {isStudioPage && (
                            <>
                                <div style={{ width: '1px', height: '24px', background: 'var(--glass-border)' }}></div>
                                <ViewSelector views={CENTER_VIEWS} activeView={centerView} onViewChange={setCenterView} />
                            </>
                        )}
                    </div>

                    {isStudioPage && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                            <button
                                onClick={() => setShowLeftPanel(!showLeftPanel)}
                                style={{
                                    padding: 'var(--space-2)',
                                    borderRadius: 'var(--radius-md)',
                                    backgroundColor: showLeftPanel ? 'var(--color-surface-panel)' : 'var(--glass-bg)',
                                    color: showLeftPanel ? 'var(--color-text)' : 'var(--color-text-muted)',
                                    border: '1px solid var(--glass-border)',
                                    cursor: 'pointer'
                                }}
                            >
                                {showLeftPanel ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
                            </button>
                            <button
                                onClick={() => setShowRightPanel(!showRightPanel)}
                                style={{
                                    padding: 'var(--space-2)',
                                    borderRadius: 'var(--radius-md)',
                                    backgroundColor: showRightPanel ? 'var(--color-surface-panel)' : 'var(--glass-bg)',
                                    color: showRightPanel ? 'var(--color-text)' : 'var(--color-text-muted)',
                                    border: '1px solid var(--glass-border)',
                                    cursor: 'pointer'
                                }}
                            >
                                {showRightPanel ? <PanelRightClose size={18} /> : <PanelRightOpen size={18} />}
                            </button>
                        </div>
                    )}
                </header>

                <div style={{ flex: 1, height: 'calc(100vh - 5rem)', overflow: 'hidden' }}>
                    {isStudioPage ? (
                        <PanelGroup direction="horizontal" style={{ height: '100%' }}>
                            {showLeftPanel && (
                                <>
                                    <Panel id="left" order={1} defaultSize={22} minSize={15} maxSize={40}>
                                        <div style={glassPanelStyle('left')}>
                                            {/* New Composition Button */}
                                            <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--glass-border)' }}>
                                                <button style={{
                                                    width: '100%',
                                                    padding: 'var(--space-3)',
                                                    background: 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))',
                                                    color: 'white',
                                                    border: 'none',
                                                    borderRadius: 'var(--radius-md)',
                                                    fontSize: 'var(--text-sm)',
                                                    fontWeight: 600,
                                                    cursor: 'pointer',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    gap: 'var(--space-2)',
                                                    boxShadow: '0 4px 12px rgba(125, 80, 196, 0.4)'
                                                }}>
                                                    <Plus size={18} />
                                                    New Composition
                                                </button>
                                            </div>
                                            <PanelTabs tabs={LEFT_TABS} activeTab={leftTab} onTabChange={setLeftTab} />
                                            <div style={{ flex: 1, overflowY: 'auto' }}>
                                                <LeftPanelContent activeTab={leftTab} />
                                            </div>
                                            {/* Bottom Navigation Links */}
                                            <div style={{ padding: 'var(--space-2)', borderTop: '1px solid var(--glass-border)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                                                <Link to="/walkthrough" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', textDecoration: 'none' }}>
                                                    <MessageSquare size={14} /> System Walkthrough
                                                </Link>
                                                <Link to="/admin" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', textDecoration: 'none' }}>
                                                    <Shield size={14} /> Admin Panel
                                                </Link>
                                                <Link to="/settings" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', padding: 'var(--space-2) var(--space-3)', borderRadius: 'var(--radius-sm)', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', textDecoration: 'none' }}>
                                                    <Settings size={14} /> Settings
                                                </Link>
                                            </div>
                                        </div>
                                    </Panel>
                                    <ResizeHandle />
                                </>
                            )}
                            <Panel
                                id="center"
                                order={2}
                                defaultSize={showLeftPanel && showRightPanel ? 56 : showLeftPanel || showRightPanel ? 78 : 100}
                                minSize={30}
                            >
                                <div style={{ height: '100%', overflow: 'hidden' }}>
                                    <CenterViewContent activeView={centerView} />
                                </div>
                            </Panel>
                            {showRightPanel && (
                                <>
                                    <ResizeHandle />
                                    <Panel id="right" order={3} defaultSize={22} minSize={15} maxSize={40}>
                                        <div style={glassPanelStyle('right')}>
                                            <PanelTabs tabs={RIGHT_TABS} activeTab={rightTab} onTabChange={setRightTab} />
                                            <div style={{ flex: 1, overflowY: 'auto' }}>
                                                <RightPanelContent activeTab={rightTab} />
                                            </div>
                                        </div>
                                    </Panel>
                                </>
                            )}
                        </PanelGroup>
                    ) : (
                        <Outlet />
                    )}
                </div>
            </div>
        </div>
    );
};

export default MainLayout;
