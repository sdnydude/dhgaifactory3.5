import React, { useState } from 'react';
import { Sliders, Wand2, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react';
import { useStudio } from '../../context/StudioContext';

const CollapsibleSection = ({ title, icon: Icon, children, defaultOpen = true }) => {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div style={{
            background: 'var(--color-surface-panel)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--glass-border)',
            marginBottom: 'var(--space-3)',
            overflow: 'hidden'
        }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    width: '100%',
                    padding: 'var(--space-3) var(--space-4)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: 'var(--color-text)'
                }}
            >
                {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                <Icon size={14} style={{ color: 'var(--color-dhg-primary)' }} />
                <span style={{ fontWeight: 600, fontSize: 'var(--text-xs)' }}>{title}</span>
            </button>
            {isOpen && (
                <div style={{ padding: '0 var(--space-4) var(--space-4)' }}>
                    {children}
                </div>
            )}
        </div>
    );
};

const ToolsPanel = () => {
    const { complianceMode, setComplianceMode } = useStudio();
    const [promptText, setPromptText] = useState('');

    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            background: 'var(--glass-bg)',
            backdropFilter: 'var(--glass-blur)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--glass-border)',
            overflow: 'hidden'
        }}>
            {/* Panel Header */}
            <div style={{
                padding: 'var(--space-3) var(--space-4)',
                borderBottom: '1px solid var(--glass-border)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)',
                background: 'rgba(0,0,0,0.2)',
                flexShrink: 0
            }}>
                <Sliders size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Tools</span>
            </div>

            {/* Tools Content */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--space-4)'
            }}>
                <CollapsibleSection title="Smart Refiner" icon={Wand2}>
                    <textarea
                        value={promptText}
                        onChange={(e) => setPromptText(e.target.value)}
                        placeholder="Paste your prompt here for AI-powered refinement..."
                        style={{
                            width: '100%',
                            minHeight: '80px',
                            padding: 'var(--space-3)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            background: 'var(--glass-bg)',
                            color: 'var(--color-text)',
                            fontSize: 'var(--text-xs)',
                            resize: 'vertical',
                            outline: 'none'
                        }}
                    />
                    <button style={{
                        marginTop: 'var(--space-2)',
                        padding: 'var(--space-2) var(--space-3)',
                        background: 'var(--gradient-primary)',
                        border: 'none',
                        borderRadius: 'var(--radius-md)',
                        color: 'white',
                        fontSize: 'var(--text-xs)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-1)'
                    }}>
                        <Wand2 size={12} />
                        Refine Prompt
                    </button>
                </CollapsibleSection>

                <CollapsibleSection title="Compliance Mode" icon={CheckCircle}>
                    <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
                        {['auto', 'cme', 'non_cme'].map(mode => (
                            <button
                                key={mode}
                                onClick={() => setComplianceMode(mode)}
                                style={{
                                    padding: 'var(--space-2) var(--space-3)',
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid var(--glass-border)',
                                    background: complianceMode === mode ? 'var(--gradient-primary)' : 'var(--glass-bg)',
                                    color: 'var(--color-text)',
                                    fontSize: 'var(--text-xs)',
                                    cursor: 'pointer',
                                    textTransform: 'uppercase'
                                }}
                            >
                                {mode.replace('_', '-')}
                            </button>
                        ))}
                    </div>
                </CollapsibleSection>
            </div>
        </div>
    );
};

export default ToolsPanel;
