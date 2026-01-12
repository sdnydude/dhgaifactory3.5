import React from 'react';
import { FileText, Download, Clock } from 'lucide-react';

const ArtifactsPanel = ({ validation = null }) => {
    const artifacts = [];

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
                justifyContent: 'space-between',
                background: 'rgba(0,0,0,0.2)',
                flexShrink: 0
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <FileText size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                    <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Artifacts</span>
                </div>
                {validation && (
                    <span style={{
                        fontSize: '9px',
                        padding: '2px 6px',
                        borderRadius: '10px',
                        background: validation.overall_status === 'passed' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                        color: validation.overall_status === 'passed' ? 'var(--color-success)' : 'var(--color-error)',
                        fontWeight: 700,
                        textTransform: 'uppercase'
                    }}>
                        QA: {validation.overall_status}
                    </span>
                )}
            </div>

            {/* Artifacts Content */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--space-4)'
            }}>
                {validation && (
                    <div style={{
                        padding: 'var(--space-4)',
                        background: 'rgba(0,0,0,0.1)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--glass-border)',
                        marginBottom: 'var(--space-4)'
                    }}>
                        <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)', fontWeight: 600, textTransform: 'uppercase' }}>
                            QA Verification Results
                        </div>
                        {validation.checks?.map((check, i) => (
                            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                                <span style={{ fontSize: '11px', color: 'var(--color-text)' }}>{check.check?.replace(/_/g, ' ') || 'Check'}</span>
                                <span style={{ fontSize: '10px', color: check.status === 'passed' ? 'var(--color-success)' : 'var(--color-error)' }}>{check.status === 'passed' ? '✓' : '✗'}</span>
                            </div>
                        ))}
                    </div>
                )}

                {artifacts.length === 0 && !validation ? (
                    <div style={{
                        height: '100%',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--color-text-muted)',
                        textAlign: 'center'
                    }}>
                        <FileText size={32} style={{ opacity: 0.3, marginBottom: 'var(--space-3)' }} />
                        <p style={{ fontSize: 'var(--text-sm)', margin: 0 }}>No artifacts yet</p>
                    </div>
                ) : (
                    artifacts.map((artifact, idx) => (
                        <div key={idx} style={{
                            padding: 'var(--space-3)',
                            background: 'var(--color-surface-panel)',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            marginBottom: 'var(--space-2)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                        }}>
                            <div>
                                <div style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>
                                    {artifact.name}
                                </div>
                                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
                                    <Clock size={10} />
                                    {artifact.timestamp}
                                </div>
                            </div>
                            <button style={{
                                padding: 'var(--space-2)',
                                background: 'var(--glass-bg)',
                                border: '1px solid var(--glass-border)',
                                borderRadius: 'var(--radius-md)',
                                color: 'var(--color-text)',
                                cursor: 'pointer'
                            }}>
                                <Download size={14} />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default ArtifactsPanel;
