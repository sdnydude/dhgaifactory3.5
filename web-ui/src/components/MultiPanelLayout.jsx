import React, { useState } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { MessageSquare, Sliders, Activity, FileText } from 'lucide-react';

const ResizeHandle = () => (
    <PanelResizeHandle
        style={{
            width: '8px',
            background: 'transparent',
            cursor: 'col-resize',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'background 0.2s'
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(139, 92, 246, 0.3)'}
        onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
    >
        <div style={{
            width: '2px',
            height: '40px',
            background: 'var(--glass-border)',
            borderRadius: '2px'
        }} />
    </PanelResizeHandle>
);

const PanelHeader = ({ icon: Icon, title }) => (
    <div style={{
        padding: 'var(--space-3) var(--space-4)',
        borderBottom: '1px solid var(--glass-border)',
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-2)',
        background: 'rgba(0,0,0,0.2)',
        flexShrink: 0
    }}>
        <Icon size={16} style={{ color: 'var(--color-dhg-primary)' }} />
        <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--color-text)' }}>{title}</span>
    </div>
);

const ChatPanelContent = ({ messages = [], onSendMessage, isProcessing }) => {
    const [input, setInput] = useState('');

    const handleSend = () => {
        if (input.trim() && onSendMessage) {
            onSendMessage(input);
            setInput('');
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <PanelHeader icon={MessageSquare} title="Chat" />
            <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
                {messages.length === 0 ? (
                    <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--color-text-muted)'
                    }}>
                        <div style={{
                            width: '4rem',
                            height: '4rem',
                            background: 'var(--glass-bg)',
                            borderRadius: '30%',
                            border: '1px solid var(--glass-border)',
                            marginBottom: 'var(--space-4)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            boxShadow: '0 0 40px rgba(139, 92, 246, 0.2)'
                        }}>
                            <div style={{
                                width: '2rem',
                                height: '2rem',
                                borderRadius: '50%',
                                background: 'var(--gradient-primary)',
                                boxShadow: '0 0 20px var(--color-dhg-primary)'
                            }} />
                        </div>
                        <h3 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, margin: 0 }}>
                            Factory Intelligence Online
                        </h3>
                        <p style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)', opacity: 0.7 }}>
                            Start a conversation to begin orchestration.
                        </p>
                    </div>
                ) : (
                    messages.map((msg, idx) => (
                        <div key={idx} style={{
                            marginBottom: 'var(--space-3)',
                            padding: 'var(--space-3)',
                            background: msg.role === 'user' ? 'var(--color-surface-panel)' : 'var(--glass-bg)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            color: 'var(--color-text)'
                        }}>
                            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-1)' }}>
                                {msg.role === 'user' ? 'You' : 'Assistant'}
                            </div>
                            <div style={{ fontSize: 'var(--text-sm)', whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        </div>
                    ))
                )}
                {isProcessing && (
                    <div style={{ color: 'var(--color-dhg-primary)', fontSize: 'var(--text-sm)' }}>
                        Processing...
                    </div>
                )}
            </div>
            <div style={{
                padding: 'var(--space-4)',
                borderTop: '1px solid var(--glass-border)',
                background: 'rgba(0,0,0,0.1)'
            }}>
                <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="Type your message..."
                        disabled={isProcessing}
                        rows={3}
                        style={{
                            flex: 1,
                            resize: 'none',
                            padding: 'var(--space-3)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            background: 'var(--color-surface-panel)',
                            color: '#ffffff',
                            fontSize: 'var(--text-sm)',
                            outline: 'none'
                        }}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || isProcessing}
                        style={{
                            padding: 'var(--space-3)',
                            borderRadius: 'var(--radius-md)',
                            background: input.trim() ? 'var(--gradient-primary)' : 'var(--glass-bg)',
                            border: '1px solid var(--glass-border)',
                            color: 'white',
                            cursor: input.trim() ? 'pointer' : 'not-allowed',
                            opacity: input.trim() ? 1 : 0.5,
                            alignSelf: 'flex-end'
                        }}
                    >
                        Send
                    </button>
                </div>
            </div>
        </div>
    );
};

const ToolsPanelContent = () => (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <PanelHeader icon={Sliders} title="Tools" />
        <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
            <div style={{
                padding: 'var(--space-4)',
                background: 'var(--color-surface-panel)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--glass-border)',
                marginBottom: 'var(--space-3)'
            }}>
                <h4 style={{ margin: 0, marginBottom: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-text)' }}>
                    Prompt Refiner
                </h4>
                <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                    AI-powered prompt enhancement tools
                </p>
            </div>
            <div style={{
                padding: 'var(--space-4)',
                background: 'var(--color-surface-panel)',
                borderRadius: 'var(--radius-lg)',
                border: '1px solid var(--glass-border)'
            }}>
                <h4 style={{ margin: 0, marginBottom: 'var(--space-2)', fontSize: 'var(--text-sm)', color: 'var(--color-text)' }}>
                    Compliance Mode
                </h4>
                <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                    {['Auto', 'CME', 'Non-CME'].map(mode => (
                        <button key={mode} style={{
                            padding: 'var(--space-2) var(--space-3)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            background: mode === 'Auto' ? 'var(--gradient-primary)' : 'var(--glass-bg)',
                            color: 'var(--color-text)',
                            fontSize: 'var(--text-xs)',
                            cursor: 'pointer'
                        }}>
                            {mode}
                        </button>
                    ))}
                </div>
            </div>
        </div>
    </div>
);

const AgentsPanelContent = () => (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <PanelHeader icon={Activity} title="Agents" />
        <div style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-4)' }}>
            {['Medical LLM', 'Research', 'Curriculum', 'Outcomes', 'QA/Compliance'].map(agent => (
                <div key={agent} style={{
                    padding: 'var(--space-3)',
                    background: 'var(--color-surface-panel)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--glass-border)',
                    marginBottom: 'var(--space-2)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text)' }}>{agent}</span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success)' }}>●</span>
                </div>
            ))}
        </div>
    </div>
);

const ArtifactsPanelContent = () => (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <PanelHeader icon={FileText} title="Artifacts" />
        <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-muted)',
            padding: 'var(--space-4)'
        }}>
            <FileText size={32} style={{ opacity: 0.3, marginBottom: 'var(--space-3)' }} />
            <p style={{ fontSize: 'var(--text-sm)', margin: 0 }}>No artifacts yet</p>
            <p style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)', opacity: 0.7 }}>
                Generated content will appear here
            </p>
        </div>
    </div>
);

const PANELS = {
    chat: { component: ChatPanelContent, icon: MessageSquare, label: 'Chat', minSize: 25, defaultSize: 50 },
    tools: { component: ToolsPanelContent, icon: Sliders, label: 'Tools', minSize: 15, defaultSize: 25 },
    agents: { component: AgentsPanelContent, icon: Activity, label: 'Agents', minSize: 15, defaultSize: 15 },
    artifacts: { component: ArtifactsPanelContent, icon: FileText, label: 'Artifacts', minSize: 15, defaultSize: 10 }
};

const MultiPanelLayout = ({ messages, onSendMessage, isProcessing }) => {
    const [activePanels, setActivePanels] = useState(['chat', 'tools']);

    const togglePanel = (panelId) => {
        setActivePanels(prev =>
            prev.includes(panelId)
                ? prev.filter(p => p !== panelId)
                : [...prev, panelId]
        );
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Panel Toggle Buttons */}
            <div style={{
                display: 'flex',
                gap: 'var(--space-2)',
                padding: 'var(--space-2) var(--space-4)',
                borderBottom: '1px solid var(--glass-border)',
                background: 'rgba(0,0,0,0.1)'
            }}>
                {Object.entries(PANELS).map(([id, { icon: Icon, label }]) => {
                    const isActive = activePanels.includes(id);
                    return (
                        <button
                            key={id}
                            onClick={() => togglePanel(id)}
                            style={{
                                padding: 'var(--space-2) var(--space-3)',
                                borderRadius: 'var(--radius-md)',
                                background: isActive ? 'var(--color-surface-panel)' : 'transparent',
                                color: isActive ? 'var(--color-text)' : 'var(--color-text-muted)',
                                border: isActive ? '1px solid var(--glass-border)' : '1px solid transparent',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-2)',
                                fontSize: 'var(--text-xs)',
                                fontWeight: 500,
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                            }}
                        >
                            <Icon size={14} />
                            {label}
                        </button>
                    );
                })}
            </div>

            {/* Panel Content Area */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
                {activePanels.length === 0 ? (
                    <div style={{
                        height: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--color-text-muted)'
                    }}>
                        <p>No panels open. Click a panel button above.</p>
                    </div>
                ) : (
                    <PanelGroup direction="horizontal" style={{ height: '100%' }}>
                        {activePanels.map((panelId, idx) => {
                            const panel = PANELS[panelId];
                            if (!panel) return null;
                            const Component = panel.component;
                            const props = panelId === 'chat' ? { messages, onSendMessage, isProcessing } : {};

                            return (
                                <React.Fragment key={panelId}>
                                    {idx > 0 && <ResizeHandle />}
                                    <Panel
                                        id={panelId}
                                        minSize={panel.minSize}
                                        defaultSize={panel.defaultSize}
                                        style={{
                                            background: 'var(--glass-bg)',
                                            backdropFilter: 'var(--glass-blur)',
                                            border: '1px solid var(--glass-border)',
                                            borderRadius: 'var(--radius-lg)',
                                            margin: 'var(--space-2)',
                                            overflow: 'hidden',
                                            display: 'flex',
                                            flexDirection: 'column'
                                        }}
                                    >
                                        <Component {...props} />
                                    </Panel>
                                </React.Fragment>
                            );
                        })}
                    </PanelGroup>
                )}
            </div>
        </div>
    );
};

export default MultiPanelLayout;
