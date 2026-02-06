import React, { useState, useEffect } from 'react';
import { Activity, Server, Cpu, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const AgentStatusPanel = () => {
    const [agentStatus, setAgentStatus] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const wsUrl = import.meta.env.VITE_WS_URL || 'ws://10.0.0.251:8011';
                const httpUrl = wsUrl.replace('ws://', 'http://').replace('/ws', '');
                const res = await fetch(`${httpUrl}/health`);
                const data = await res.json();
                setAgentStatus(data.agents || {});
            } catch (err) {
                console.error('Failed to fetch agent status:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 10000);
        return () => clearInterval(interval);
    }, []);

    const getStatusIcon = (status) => {
        if (status === 'healthy') return <CheckCircle size={12} style={{ color: 'var(--color-success)' }} />;
        if (status === 'error') return <AlertCircle size={12} style={{ color: 'var(--color-error)' }} />;
        return <Loader size={12} style={{ color: 'var(--color-warning)' }} />;
    };

    const agents = [
        { id: 'medical-research', name: 'Medical Research', icon: Server },
        { id: 'clinical-practice', name: 'Clinical Practice', icon: Server },
        { id: 'gap-analysis', name: 'Gap Analysis', icon: Server },
        { id: 'needs-assessment', name: 'Needs Assessment', icon: Server },
        { id: 'learning-objectives', name: 'Learning Objectives', icon: Server },
        { id: 'curriculum-design', name: 'Curriculum Design', icon: Server },
        { id: 'research-protocol', name: 'Research Protocol', icon: Server },
        { id: 'marketing-plan', name: 'Marketing Plan', icon: Server },
        { id: 'grant-writer', name: 'Grant Writer', icon: Cpu },
        { id: 'prose-qa', name: 'Prose QA', icon: Server },
        { id: 'compliance-review', name: 'Compliance Review', icon: Server }
    ];

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
                <Activity size={16} style={{ color: 'var(--color-dhg-primary)' }} />
                <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>Agent Status</span>
            </div>

            {/* Status Content */}
            <div style={{
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--space-4)'
            }}>
                {loading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                        <Loader size={24} style={{ animation: 'spin 1s linear infinite' }} />
                    </div>
                ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                        {agents.map(agent => {
                            const status = agentStatus[agent.id] || 'unknown';
                            const Icon = agent.icon;

                            return (
                                <div key={agent.id} style={{
                                    padding: 'var(--space-3)',
                                    background: 'var(--color-surface-panel)',
                                    borderRadius: 'var(--radius-md)',
                                    border: '1px solid var(--glass-border)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                        <Icon size={14} style={{ color: 'var(--color-text-muted)' }} />
                                        <span style={{ fontSize: 'var(--text-xs)' }}>{agent.name}</span>
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
                                        {getStatusIcon(status)}
                                        <span style={{
                                            fontSize: 'var(--text-xs)',
                                            textTransform: 'capitalize',
                                            color: status === 'healthy' ? 'var(--color-success)' : 'var(--color-text-muted)'
                                        }}>
                                            {status}
                                        </span>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AgentStatusPanel;
