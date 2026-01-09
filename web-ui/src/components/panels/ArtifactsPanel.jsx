import React from 'react';
import { FileText, Download, Clock } from 'lucide-react';

const ArtifactsPanel = () => {
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
                gap: 'var(--space-2)',
                background: 'rgba(0,0,0,0.2)',
                flexShrink: 0
            }}>
                <FileText size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Artifacts</span>
            </div>

            {/* Artifacts Content */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--space-4)'
            }}>
                {artifacts.length === 0 ? (
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
                        <p style={{ fontSize: 'var(--text-xs)', marginTop: 'var(--space-1)', opacity: 0.7 }}>
                            Generated content will appear here
                        </p>
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
