import React, { useState } from 'react';
import { Key, BarChart3, Database, Shield, Radio, Activity, Plus, Terminal, Zap, Server, Globe } from 'lucide-react';
import Panel from '../components/ui/Panel';

const AdminPage = () => {
    const [apiKeys] = useState([
        { id: 1, provider: 'OpenAI', maskedKey: 'sk-....4f9a', active: true, usage: '2.4k tokens' },
        { id: 2, provider: 'Anthropic', maskedKey: 'sk-ant-....9d21', active: true, usage: '1.1k tokens' },
        { id: 3, provider: 'Google Gemini', maskedKey: 'Not configured', active: false, usage: '0 tokens' },
    ]);

    const [logs] = useState([
        { time: '14:22:01', level: 'INFO', msg: 'Orchestrator successfully routed query to Gemini 1.5 Pro' },
        { time: '14:21:45', level: 'WARN', msg: 'Medical-LLM agent reported high latency (450ms)' },
        { time: '14:20:12', level: 'ERROR', msg: 'Failed to connect to Competitor Intel Agent (Port 8006)' },
        { time: '14:18:30', level: 'INFO', msg: 'User "Admin" updated global system configuration' },
    ]);

    const stats = [
        { label: 'System Uptime', value: '99.8%', sub: 'Last 30 days', icon: <Server size={12} color="var(--color-dhg-success)" /> },
        { label: 'Active Sessions', value: '12', sub: 'Across 4 agents', icon: <Activity size={12} color="var(--color-dhg-primary)" /> },
        { label: 'Throughput', value: '4.2 req/s', sub: 'Current load', icon: <Globe size={12} color="var(--color-dhg-accent)" /> },
    ];

    return (
        <div style={{
            padding: 'var(--space-8)',
            maxWidth: '90rem',
            margin: '0 auto',
            color: 'var(--color-text)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-8)'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                <div>
                    <h1 style={{
                        fontSize: 'var(--text-2xl)',
                        fontWeight: 700,
                        color: 'var(--color-text)',
                        margin: 0,
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--space-3)'
                    }}>
                        <Shield size={32} style={{ color: 'var(--color-dhg-primary)' }} />
                        AIFactory Control Center
                    </h1>
                    <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)' }}>
                        Manage global parameters, API authorizations, and agent health.
                    </p>
                </div>

                <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
                    <button style={secondaryButtonStyle}>System Export</button>
                    <button style={{ ...primaryButtonStyle, background: 'var(--gradient-primary)' }}>Force Restart All</button>
                </div>
            </div>

            {/* Stats Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: 'var(--space-6)'
            }}>
                {stats.map((stat, index) => (
                    <div key={index} style={{
                        background: 'var(--glass-bg)',
                        backdropFilter: 'var(--glass-blur)',
                        border: '1px solid var(--glass-border)',
                        borderRadius: 'var(--radius-xl)',
                        padding: 'var(--space-6)',
                        boxShadow: 'var(--glass-shadow)'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', fontWeight: 500 }}>{stat.label}</div>
                            <div style={{ padding: 'var(--space-2)', background: 'rgba(255,255,255,0.03)', borderRadius: 'var(--radius-md)' }}>{stat.icon}</div>
                        </div>
                        <div style={{ fontSize: 'var(--text-3xl)', fontWeight: 700, color: 'var(--color-text)', marginTop: 'var(--space-2)' }}>{stat.value}</div>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-4)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ color: 'var(--color-dhg-success)', fontWeight: 600 }}>● Live</span>
                            <span>{stat.sub}</span>
                        </div>
                    </div>
                ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 'var(--space-8)' }}>
                {/* Left Column: Keys & Services */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
                    <Panel title="Agent Authorization Keys" actions={<Plus size={16} />}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
                            <thead>
                                <tr style={{ color: 'var(--color-text-muted)', textAlign: 'left', borderBottom: '1px solid var(--glass-border)' }}>
                                    <th style={{ padding: 'var(--space-4)', fontWeight: 500 }}>Provider</th>
                                    <th style={{ padding: 'var(--space-4)', fontWeight: 500 }}>Usage</th>
                                    <th style={{ padding: 'var(--space-4)', fontWeight: 500 }}>Status</th>
                                    <th style={{ padding: 'var(--space-4)', textAlign: 'right', fontWeight: 500 }}>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {apiKeys.map((key) => (
                                    <tr key={key.id} style={{ borderBottom: '1px solid var(--glass-border)' }}>
                                        <td style={{ padding: 'var(--space-4)' }}>
                                            <div style={{ fontWeight: 600 }}>{key.provider}</div>
                                            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontFamily: 'monospace' }}>{key.maskedKey}</div>
                                        </td>
                                        <td style={{ padding: 'var(--space-4)', color: 'var(--color-text-muted)' }}>{key.usage}</td>
                                        <td style={{ padding: 'var(--space-4)' }}>
                                            <span style={{
                                                padding: '4px 12px',
                                                borderRadius: '20px',
                                                fontSize: '10px',
                                                fontWeight: 700,
                                                background: key.active ? 'rgba(16, 185, 129, 0.1)' : 'rgba(148, 163, 184, 0.1)',
                                                color: key.active ? 'var(--color-dhg-success)' : 'var(--color-text-muted)',
                                                border: `1px solid ${key.active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(148, 163, 184, 0.2)'}`
                                            }}>
                                                {key.active ? 'ENABLED' : 'DISABLED'}
                                            </span>
                                        </td>
                                        <td style={{ padding: 'var(--space-4)', textAlign: 'right' }}>
                                            <button style={{ color: 'var(--color-dhg-primary)', background: 'none', border: 'none', cursor: 'pointer', fontWeight: 600 }}>Configure</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </Panel>

                    <Panel title="Advanced Telemetry (Service Mesh)">
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                            {[
                                { name: 'Registry DB (Postgres)', port: '5432', latency: '4ms', status: 'healthy' },
                                { name: 'Orchestrator V3', port: '8011', latency: '12ms', status: 'healthy' },
                                { name: 'Medical Diagnostic Agent', port: '8002', latency: '412ms', status: 'warning' },
                                { name: 'Security & Compliance V2', port: '8007', latency: 'inf', status: 'critical' },
                            ].map((service, i) => (
                                <div key={i} style={{
                                    padding: 'var(--space-4)',
                                    background: 'rgba(255,255,255,0.02)',
                                    borderRadius: 'var(--radius-lg)',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    border: '1px solid var(--glass-border)'
                                }}>
                                    <div>
                                        <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{service.name}</div>
                                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Port {service.port} • Local Domain</div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontWeight: 700, fontSize: 'var(--text-xs)', color: service.status === 'healthy' ? 'var(--color-dhg-success)' : service.status === 'warning' ? 'var(--color-dhg-orange)' : 'var(--color-dhg-danger)' }}>
                                            {service.latency}
                                        </div>
                                        <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>LATENCY</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Panel>
                </div>

                {/* Right Column: Real-time Logs */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)' }}>
                    <Panel title="Live Action Trace" actions={<Terminal size={16} />}>
                        <div style={{
                            background: '#020617',
                            padding: 'var(--space-4)',
                            borderRadius: 'var(--radius-md)',
                            fontFamily: 'monospace',
                            fontSize: '0.7rem',
                            minHeight: '400px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 'var(--space-3)',
                            overflowY: 'auto',
                            maxHeight: '600px',
                            border: '1px solid #1e293b'
                        }}>
                            {logs.map((log, i) => (
                                <div key={i} style={{ borderLeft: `2px solid ${log.level === 'ERROR' ? '#ef4444' : log.level === 'WARN' ? '#f97316' : '#3b82f6'}`, paddingLeft: '8px' }}>
                                    <span style={{ color: '#64748b', marginRight: '8px' }}>[{log.time}]</span>
                                    <span style={{
                                        color: log.level === 'ERROR' ? '#f87171' : log.level === 'WARN' ? '#fbbf24' : '#60a5fa',
                                        fontWeight: 'bold',
                                        marginRight: '8px'
                                    }}>{log.level}</span>
                                    <span style={{ color: '#cbd5e1' }}>{log.msg}</span>
                                </div>
                            ))}
                            <div style={{ marginTop: 'auto', color: '#334155', animation: 'fadeIn 1s infinite alternate' }}>_ system listening...</div>
                        </div>
                    </Panel>

                    <div style={{
                        background: 'var(--gradient-orange)',
                        padding: 'var(--space-6)',
                        borderRadius: 'var(--radius-xl)',
                        color: 'white',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'var(--space-4)',
                        boxShadow: 'var(--shadow-lg)'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
                            <Zap size={24} fill="white" />
                            <span style={{ fontWeight: 700, fontSize: 'var(--text-lg)' }}>Antigravity Mode</span>
                        </div>
                        <p style={{ fontSize: 'var(--text-xs)', opacity: 0.9, lineHeight: 1.5 }}>
                            Autonomous optimization is currently ACTIVE. Agents are monitoring port availability and self-healing connection strings.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

const primaryButtonStyle = {
    padding: 'var(--space-3) var(--space-6)',
    borderRadius: 'var(--radius-md)',
    color: 'white',
    fontWeight: 600,
    fontSize: 'var(--text-xs)',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s'
};

const secondaryButtonStyle = {
    padding: 'var(--space-3) var(--space-6)',
    borderRadius: 'var(--radius-md)',
    color: 'var(--color-text)',
    fontWeight: 600,
    fontSize: 'var(--text-xs)',
    border: '1px solid var(--glass-border)',
    background: 'var(--glass-bg)',
    cursor: 'pointer',
    transition: 'all 0.2s'
};
export default AdminPage;
