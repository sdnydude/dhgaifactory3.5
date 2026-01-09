import React, { useState } from 'react';
import { Sparkles, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';
import { motion } from 'framer-motion';

const PromptTools = () => {
    // Determining state for demonstration - in a real app this would analyze the input
    const [analysisStatus, setAnalysisStatus] = useState('idle'); // idle, analyzing, complete

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
            <div className="dhg-card" style={{
                background: 'var(--color-surface-panel)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-4)',
                border: '1px solid var(--glass-border)'
            }}>
                <h4 style={{
                    margin: '0 0 var(--space-3) 0',
                    fontSize: 'var(--text-sm)',
                    fontWeight: 600,
                    color: 'var(--color-text)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)'
                }}>
                    <Sparkles size={16} className="text-dhg-accent" style={{ color: 'var(--color-dhg-accent)' }} />
                    Prompt Quality
                </h4>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--text-xs)' }}>
                        <span style={{ color: 'var(--color-text-muted)' }}>Clarity</span>
                        <div style={{ width: '60%', height: '6px', background: 'var(--color-surface-bg)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: '85%', height: '100%', background: 'var(--color-dhg-success)', borderRadius: '3px' }}></div>
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--text-xs)' }}>
                        <span style={{ color: 'var(--color-text-muted)' }}>Specificity</span>
                        <div style={{ width: '60%', height: '6px', background: 'var(--color-surface-bg)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: '60%', height: '100%', background: 'var(--color-dhg-orange)', borderRadius: '3px' }}></div>
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 'var(--text-xs)' }}>
                        <span style={{ color: 'var(--color-text-muted)' }}>Context</span>
                        <div style={{ width: '60%', height: '6px', background: 'var(--color-surface-bg)', borderRadius: '3px', overflow: 'hidden' }}>
                            <div style={{ width: '40%', height: '100%', background: 'var(--color-dhg-danger)', borderRadius: '3px' }}></div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="dhg-card" style={{
                background: 'var(--color-surface-panel)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-4)',
                border: '1px solid var(--glass-border)'
            }}>
                <h4 style={{
                    margin: '0 0 var(--space-3) 0',
                    fontSize: 'var(--text-sm)',
                    fontWeight: 600,
                    color: 'var(--color-text)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)'
                }}>
                    <RefreshCw size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                    Suggestions
                </h4>

                <ul style={{
                    listStyle: 'none',
                    padding: 0,
                    margin: 0,
                    fontSize: 'var(--text-sm)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 'var(--space-3)'
                }}>
                    <li style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'start' }}>
                        <AlertTriangle size={14} style={{ color: 'var(--color-dhg-orange)', marginTop: '2px', flexShrink: 0 }} />
                        <span style={{ color: 'var(--color-text-muted)' }}>
                            Add more context about the target audience (e.g., "for medical professionals").
                        </span>
                    </li>
                    <li style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'start' }}>
                        <CheckCircle size={14} style={{ color: 'var(--color-dhg-success)', marginTop: '2px', flexShrink: 0 }} />
                        <span style={{ color: 'var(--color-text-muted)' }}>
                            Tone is appropriate for a professional setting.
                        </span>
                    </li>
                </ul>

                <button style={{
                    marginTop: 'var(--space-4)',
                    width: '100%',
                    padding: 'var(--space-2)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 500,
                    color: 'var(--color-dhg-primary)',
                    background: 'rgba(59, 130, 246, 0.1)',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    transition: 'all 0.2s ease',
                    cursor: 'pointer'
                }}>
                    Auto-Optimize Prompt
                </button>
            </div>
        </div>
    );
};

export default PromptTools;
