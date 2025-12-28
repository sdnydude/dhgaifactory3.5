import React, { useState } from 'react';
import { Sparkles, CheckCircle, AlertTriangle, RefreshCw, Zap, Type, AlignLeft } from 'lucide-react';
import Panel from '../ui/Panel';

const PromptRefiner = () => {
    const [isRefining, setIsRefining] = useState(false);

    const handleRefine = () => {
        setIsRefining(true);
        setTimeout(() => setIsRefining(false), 1500);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <Panel title="Prompt Checker" actions={<Sparkles size={16} style={{ color: 'var(--color-dhg-accent)' }} />}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                            <span style={{ color: 'var(--color-text-muted)' }}>Clarity Score</span>
                            <span style={{ color: 'var(--color-dhg-success)' }}>85%</span>
                        </div>
                        <div style={{ height: '6px', background: 'var(--color-surface-bg)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: '85%', height: '100%', background: 'var(--color-dhg-success)' }}></div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                            <span style={{ color: 'var(--color-text-muted)' }}>Specificity</span>
                            <span style={{ color: 'var(--color-dhg-orange)' }}>62%</span>
                        </div>
                        <div style={{ height: '6px', background: 'var(--color-surface-bg)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: '62%', height: '100%', background: 'var(--color-dhg-orange)' }}></div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', fontWeight: 500 }}>
                            <span style={{ color: 'var(--color-text-muted)' }}>Tone Consistency</span>
                            <span style={{ color: 'var(--color-dhg-primary)' }}>92%</span>
                        </div>
                        <div style={{ height: '6px', background: 'var(--color-surface-bg)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: '92%', height: '100%', background: 'var(--color-dhg-primary)' }}></div>
                        </div>
                    </div>
                </div>
            </Panel>

            <Panel title="Smart Refiner" actions={<Zap size={16} style={{ color: 'var(--color-dhg-orange)' }} />}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <div style={{
                        padding: 'var(--space-3)',
                        background: 'rgba(255,255,255,0.03)',
                        borderRadius: 'var(--radius-md)',
                        borderLeft: '3px solid var(--color-dhg-orange)',
                        fontSize: 'var(--text-sm)'
                    }}>
                        <p style={{ margin: 0, color: 'var(--color-text-muted)', fontStyle: 'italic' }}>
                            "Consider specifying the target audience as 'medical clinicians' to narrow the scope of the diagnostic output."
                        </p>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
                        <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', fontSize: 'var(--text-xs)' }}>
                            <CheckCircle size={14} style={{ color: 'var(--color-dhg-success)' }} />
                            <span>Corrected technical terminology</span>
                        </div>
                        <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', fontSize: 'var(--text-xs)' }}>
                            <AlertTriangle size={14} style={{ color: 'var(--color-dhg-orange)' }} />
                            <span>Missing data constraints</span>
                        </div>
                    </div>

                    <button
                        onClick={handleRefine}
                        disabled={isRefining}
                        style={{
                            marginTop: 'var(--space-2)',
                            width: '100%',
                            padding: 'var(--space-3)',
                            background: 'var(--gradient-orange)',
                            color: 'white',
                            border: 'none',
                            borderRadius: 'var(--radius-md)',
                            fontWeight: 600,
                            fontSize: 'var(--text-xs)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: 'var(--space-2)',
                            boxShadow: 'var(--shadow-md)',
                            opacity: isRefining ? 0.7 : 1
                        }}
                    >
                        {isRefining ? <RefreshCw size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                        {isRefining ? 'Refining...' : 'Auto-Refine Prompt'}
                    </button>
                </div>
            </Panel>

            <Panel title="Quick Formatting">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)' }}>
                    <button style={toolButtonStyle}>
                        <Type size={14} /> Bullet Points
                    </button>
                    <button style={toolButtonStyle}>
                        <AlignLeft size={14} /> Clear Format
                    </button>
                </div>
            </Panel>
        </div>
    );
};

const toolButtonStyle = {
    padding: 'var(--space-2)',
    background: 'var(--color-surface-panel)',
    border: '1px solid var(--glass-border)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--color-text)',
    fontSize: 'var(--text-xs)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 'var(--space-2)',
    cursor: 'pointer',
    transition: 'all 0.2s'
};

export default PromptRefiner;
