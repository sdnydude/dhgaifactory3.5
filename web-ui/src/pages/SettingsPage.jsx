import React, { useState } from 'react';
import { User, Palette, Monitor, Edit2, Shield, Bell, Moon, Sun, Globe, Cpu } from 'lucide-react';
import { useStudio } from '../context/StudioContext';
import Panel from '../components/ui/Panel';

const SettingsPage = () => {
    const { setSelectedModel, selectedModel, theme, setTheme } = useStudio();

    return (
        <div style={{
            padding: 'var(--space-8)',
            maxWidth: '70rem',
            margin: '0 auto',
            color: 'var(--color-text)',
            display: 'flex',
            flexDirection: 'column',
            gap: 'var(--space-8)'
        }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{
                    fontSize: 'var(--text-2xl)',
                    fontWeight: 700,
                    color: 'var(--color-text)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-3)'
                }}>
                    <User size={32} style={{ color: 'var(--color-dhg-primary)' }} />
                    Command Configuration
                </h1>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', background: 'var(--glass-bg)', padding: 'var(--space-2) var(--space-4)', borderRadius: 'var(--radius-xl)', border: '1px solid var(--glass-border)' }}>
                    Admin Access Level: **Full Autonomy**
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-8)' }}>
                {/* Profile & Appearance */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
                    <Panel title="Profile Identity" actions={<Edit2 size={16} />}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)' }}>
                            <div style={{
                                width: '5rem',
                                height: '5rem',
                                borderRadius: 'var(--radius-xl)',
                                background: 'var(--gradient-primary)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--space-3)',
                                justifyContent: 'center',
                                color: 'white',
                                fontSize: 'var(--text-xl)',
                                fontWeight: 800,
                                boxShadow: 'var(--shadow-lg)',
                                border: '2px solid rgba(255,255,255,0.1)'
                            }}>
                                DH
                            </div>
                            <div>
                                <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>DHG Principal</div>
                                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>admin@dhg.sh</div>
                                <div style={{
                                    marginTop: 'var(--space-2)',
                                    display: 'inline-block',
                                    padding: '2px 8px',
                                    background: 'rgba(59, 130, 246, 0.1)',
                                    color: 'var(--color-dhg-primary)',
                                    borderRadius: '4px',
                                    fontSize: '10px',
                                    fontWeight: 700
                                }}>VERIFIED PARTNER</div>
                            </div>
                        </div>
                    </Panel>

                    <Panel title="Visual Environment" actions={<Palette size={16} />}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-3)' }}>
                            {[
                                { id: 'light', icon: <Sun size={14} />, label: 'Deep Light' },
                                { id: 'dark', icon: <Moon size={14} />, label: 'Space Dark' },
                                { id: 'system', icon: <Globe size={14} />, label: 'Auto Sync' },
                            ].map((t) => (
                                <button
                                    key={t.id}
                                    onClick={() => setTheme(t.id)}
                                    style={{
                                        border: theme === t.id ? '2px solid var(--color-dhg-primary)' : '1px solid var(--glass-border)',
                                        background: theme === t.id ? 'var(--gradient-primary)' : 'rgba(255,255,255,0.02)',
                                        color: theme === t.id ? 'white' : 'var(--color-text)',
                                        padding: 'var(--space-4) var(--space-2)',
                                        borderRadius: 'var(--radius-lg)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        gap: 'var(--space-2)'
                                    }}
                                >
                                    {t.icon}
                                    <span style={{ fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{t.label}</span>
                                </button>
                            ))}
                        </div>
                    </Panel>
                </div>

                {/* Intelligence & Communications */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
                    <Panel title="Intelligence Default" actions={<Monitor size={16} />}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
                            <div>
                                <label style={labelStyle}>Primary Core Model</label>
                                <select style={selectStyle}>
                                    <optgroup label="Cloud Tier">
                                        <option>Gemini 1.5 Pro (Recommended)</option>
                                        <option>Claude 3.5 Sonnet</option>
                                        <option>GPT-4o</option>
                                    </optgroup>
                                    <optgroup label="Local Tier">
                                        <option>Llama 3 70B (Local)</option>
                                        <option>Nano Banana Pro (Custom)</option>
                                    </optgroup>
                                </select>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: 'var(--space-3)', background: 'rgba(255,255,255,0.02)', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                                    <Cpu size={14} style={{ color: 'var(--color-dhg-accent)' }} />
                                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500 }}>Autonomous Fallback</span>
                                </div>
                                <div style={{ width: '32px', height: '18px', background: 'var(--color-dhg-success)', borderRadius: '9px', position: 'relative' }}>
                                    <div style={{ width: '14px', height: '14px', background: 'white', borderRadius: '50%', position: 'absolute', right: '2px', top: '2px' }}></div>
                                </div>
                            </div>
                        </div>
                    </Panel>

                    <Panel title="Command Notifications" actions={<Bell size={16} />}>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
                            {[
                                { label: 'Agent Completion Alerts', active: true },
                                { label: 'System Health Warnings', active: true },
                                { label: 'Security Verifications', active: false },
                            ].map((n, i) => (
                                <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                    <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>{n.label}</span>
                                    <div style={{ width: '32px', height: '18px', background: n.active ? 'var(--color-dhg-primary)' : 'var(--color-border)', borderRadius: '9px', position: 'relative', cursor: 'pointer' }}>
                                        <div style={{ width: '14px', height: '14px', background: 'white', borderRadius: '50%', position: 'absolute', [n.active ? 'right' : 'left']: '2px', top: '2px' }}></div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </Panel>
                </div>
            </div>

            <div style={{
                padding: 'var(--space-6)',
                background: 'var(--glass-bg)',
                border: '1px solid var(--glass-border)',
                borderRadius: 'var(--radius-xl)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
                    <Shield size={24} style={{ color: 'var(--color-dhg-orange)' }} />
                    <div>
                        <div style={{ fontWeight: 700, fontSize: 'var(--text-sm)' }}>Privacy Protocol V3.5</div>
                        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>End-to-end encrypted locally-hosted database.</div>
                    </div>
                </div>
                <button style={{
                    padding: 'var(--space-2) var(--space-4)',
                    background: 'transparent',
                    border: '1px solid var(--color-dhg-danger)',
                    color: 'var(--color-dhg-danger)',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 700,
                    cursor: 'pointer'
                }}>Delete Account & Data</button>
            </div>
        </div>
    );
};

const labelStyle = {
    display: 'block',
    fontSize: 'var(--text-xs)',
    fontWeight: 600,
    marginBottom: 'var(--space-2)',
    color: 'var(--color-text-muted)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
};

const selectStyle = {
    width: '100%',
    background: 'var(--color-surface-panel)',
    border: '1px solid var(--glass-border)',
    borderRadius: 'var(--radius-md)',
    padding: 'var(--space-3)',
    color: 'var(--color-text)',
    outline: 'none',
    fontSize: 'var(--text-sm)',
    cursor: 'pointer'
};
export default SettingsPage;
