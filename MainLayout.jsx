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

const PromptCheckerTool = () => {
    const [prompt, setPrompt] = React.useState('');
    const [loading, setLoading] = React.useState(false);
    const [result, setResult] = React.useState(null);

    const analyzePrompt = async () => {
        if (!prompt.trim()) return;
        setLoading(true);
        try {
            const response = await fetch('http://10.0.0.251:8001/api/prompt-analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error('Prompt analysis failed:', error);
            setResult({ error: 'Analysis failed' });
        }
        setLoading(false);
    };

    const getScoreColor = (score) => {
        if (score >= 0.8) return 'var(--color-dhg-success)';
        if (score >= 0.6) return 'var(--color-dhg-orange)';
        return 'var(--color-dhg-danger)';
    };

    return (
        <div style={{ padding: 'var(--space-4)' }}>
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', marginBottom: 'var(--space-3)' }}>
                Prompt Checker
            </div>
            <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Paste your prompt here to analyze..."
                style={{
                    width: '100%',
                    height: '100px',
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
            <button
                onClick={analyzePrompt}
                disabled={loading || !prompt.trim()}
                style={{
                    width: '100%',
                    padding: 'var(--space-2)',
                    background: loading ? 'var(--color-border)' : 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                    cursor: loading ? 'wait' : 'pointer'
                }}>
                {loading ? 'Analyzing...' : 'Analyze Prompt'}
            </button>

            {result && !result.error && (
                <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--color-surface-panel)', borderRadius: 'var(--radius-md)', border: '1px solid var(--glass-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-2)' }}>
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Overall</span>
                        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: getScoreColor(result.overall_score) }}>{Math.round(result.overall_score * 100)}%</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 'var(--space-2)', marginBottom: 'var(--space-3)' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Clarity</div>
                            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: getScoreColor(result.clarity_score) }}>{Math.round(result.clarity_score * 100)}%</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Specificity</div>
                            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: getScoreColor(result.specificity_score) }}>{Math.round(result.specificity_score * 100)}%</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Compliance</div>
                            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: getScoreColor(result.compliance_score) }}>{Math.round(result.compliance_score * 100)}%</div>
                        </div>
                    </div>
                    <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: 'var(--space-1)' }}>
                        Mode: <span style={{ color: 'var(--color-dhg-primary)', fontWeight: 600 }}>{result.detected_mode.toUpperCase()}</span> | {result.word_count} words | ~{result.estimated_tokens} tokens
                    </div>
                    {result.suggestions && result.suggestions.length > 0 && (
                        <div style={{ fontSize: '10px', color: 'var(--color-text)', marginTop: 'var(--space-2)' }}>
                            {result.suggestions.map((s, i) => (
                                <div key={i} style={{ marginBottom: '2px' }}>• {s}</div>
                            ))}
                        </div>
                    )}
                    {result.flags && result.flags.length > 0 && (
                        <div style={{ fontSize: '10px', color: 'var(--color-dhg-orange)', marginTop: 'var(--space-2)' }}>
                            {result.flags.map((f, i) => (
                                <div key={i}>⚠ {f}</div>
                            ))}
                        </div>
                    )}
                </div>
            )}
            {result && result.error && (
                <div style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--color-dhg-danger)' }}>
                    {result.error}
                </div>
            )}
        </div>
    );
};

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

// Graphics asset packages for batch generation
const GRAPHICS_PACKAGES = [
    { id: 'podcast', name: 'Podcast Package', types: ['thumbnail', 'logo', 'social_post', 'banner'] },
    { id: 'webinar', name: 'Webinar Package', types: ['slide', 'infographic', 'thumbnail', 'certificate'] },
    { id: 'course', name: 'Course Package', types: ['slide', 'diagram', 'infographic', 'certificate', 'thumbnail'] },
    { id: 'clinical', name: 'Clinical Education', types: ['anatomical', 'flowchart', 'moa', 'case_study', 'diagram'] },
    { id: 'custom', name: 'Custom Selection', types: [] }
];

const VISUAL_TYPES = {
    core: [
        { id: 'infographic', name: 'Infographic' },
        { id: 'slide', name: 'Slide' },
        { id: 'chart', name: 'Chart' },
        { id: 'diagram', name: 'Diagram' },
        { id: 'illustration', name: 'Illustration' }
    ],
    cme: [
        { id: 'thumbnail', name: 'Thumbnail' },
        { id: 'certificate', name: 'Certificate' },
        { id: 'logo', name: 'Logo' },
        { id: 'timeline', name: 'Timeline' },
        { id: 'comparison', name: 'Comparison' },
        { id: 'anatomical', name: 'Anatomical' },
        { id: 'flowchart', name: 'Flowchart' },
        { id: 'case_study', name: 'Case Study' },
        { id: 'moa', name: 'MOA Diagram' }
    ],
    social: [
        { id: 'social_post', name: 'Social Post' },
        { id: 'banner', name: 'Banner' },
        { id: 'avatar', name: 'Avatar' }
    ],
    data: [
        { id: 'heatmap', name: 'Heatmap' },
        { id: 'dashboard', name: 'Dashboard' },
        { id: 'scorecard', name: 'Scorecard' }
    ]
};

const VisualsToolPanel = ({ onGeneratedImages }) => {
    const [prompt, setPrompt] = useState('');
    const [selectedPackage, setSelectedPackage] = useState('custom');
    const [selectedTypes, setSelectedTypes] = useState([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [results, setResults] = useState([]);

    const handlePackageChange = (packageId) => {
        setSelectedPackage(packageId);
        const pkg = GRAPHICS_PACKAGES.find(p => p.id === packageId);
        if (pkg && pkg.types.length > 0) {
            setSelectedTypes(pkg.types);
        }
    };

    const toggleType = (typeId) => {
        setSelectedPackage('custom');
        setSelectedTypes(prev =>
            prev.includes(typeId)
                ? prev.filter(t => t !== typeId)
                : [...prev, typeId]
        );
    };

    const handleSubmit = async () => {
        if (!prompt.trim() || selectedTypes.length === 0) return;

        setIsGenerating(true);
        setResults([]);

        try {
            const newResults = [];
            for (const visualType of selectedTypes) {
                const response = await fetch('http://10.0.0.251:8008/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        topic: prompt,
                        visual_type: visualType,
                        style: 'medical-professional'
                    })
                });
                const data = await response.json();
                newResults.push({ type: visualType, ...data });
            }
            setResults(newResults);
            // Call callback to display in IDE gallery
            if (onGeneratedImages) {
                onGeneratedImages(newResults);
            }
        } catch (error) {
            console.error('Generation failed:', error);
        } finally {
            setIsGenerating(false);
        }
    };

    return (
        <div style={{ padding: 'var(--space-4)', overflowY: 'auto', height: '100%' }}>
            <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', marginBottom: 'var(--space-3)' }}>
                🎨 Nano Banana Pro Visuals
            </div>

            {/* Prompt Input */}
            <div style={{ marginBottom: 'var(--space-3)' }}>
                <label style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', display: 'block', marginBottom: 'var(--space-1)' }}>
                    Describe your visuals
                </label>
                <textarea
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    placeholder="e.g., Type 2 diabetes management best practices, focusing on lifestyle modifications..."
                    style={{
                        width: '100%',
                        minHeight: '80px',
                        padding: 'var(--space-2)',
                        background: 'var(--color-surface-panel)',
                        border: '1px solid var(--glass-border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--color-text)',
                        fontSize: 'var(--text-xs)',
                        resize: 'vertical'
                    }}
                />
            </div>

            {/* Graphics Package Dropdown */}
            <div style={{ marginBottom: 'var(--space-3)' }}>
                <label style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', display: 'block', marginBottom: 'var(--space-1)' }}>
                    Graphics Package
                </label>
                <select
                    value={selectedPackage}
                    onChange={(e) => handlePackageChange(e.target.value)}
                    style={{
                        width: '100%',
                        padding: 'var(--space-2)',
                        background: 'var(--color-surface-panel)',
                        border: '1px solid var(--glass-border)',
                        borderRadius: 'var(--radius-md)',
                        color: 'var(--color-text)',
                        fontSize: 'var(--text-xs)'
                    }}
                >
                    {GRAPHICS_PACKAGES.map(pkg => (
                        <option key={pkg.id} value={pkg.id}>{pkg.name}</option>
                    ))}
                </select>
            </div>

            {/* Visual Types Multi-Select */}
            <div style={{ marginBottom: 'var(--space-3)' }}>
                <label style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', display: 'block', marginBottom: 'var(--space-2)' }}>
                    Visual Types ({selectedTypes.length} selected)
                </label>

                {Object.entries(VISUAL_TYPES).map(([category, types]) => (
                    <div key={category} style={{ marginBottom: 'var(--space-2)' }}>
                        <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                            {category === 'core' ? 'Core' : category === 'cme' ? 'CME' : category === 'social' ? 'Social' : 'Data'}
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                            {types.map(type => (
                                <button
                                    key={type.id}
                                    onClick={() => toggleType(type.id)}
                                    style={{
                                        padding: '4px 8px',
                                        fontSize: '10px',
                                        borderRadius: 'var(--radius-sm)',
                                        border: '1px solid',
                                        borderColor: selectedTypes.includes(type.id) ? 'var(--color-dhg-primary)' : 'var(--glass-border)',
                                        background: selectedTypes.includes(type.id)
                                            ? 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))'
                                            : 'transparent',
                                        color: selectedTypes.includes(type.id) ? 'white' : 'var(--color-text-muted)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {type.name}
                                </button>
                            ))}
                        </div>
                    </div>
                ))}
            </div>

            {/* Submit Button */}
            <button
                onClick={handleSubmit}
                disabled={isGenerating || !prompt.trim() || selectedTypes.length === 0}
                style={{
                    width: '100%',
                    padding: 'var(--space-3)',
                    background: isGenerating
                        ? 'var(--glass-bg)'
                        : 'linear-gradient(135deg, var(--color-dhg-primary), var(--color-dhg-accent))',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    fontSize: 'var(--text-sm)',
                    fontWeight: 600,
                    color: 'white',
                    cursor: isGenerating ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 'var(--space-2)',
                    opacity: (!prompt.trim() || selectedTypes.length === 0) ? 0.5 : 1
                }}
            >
                {isGenerating ? '⏳ Generating...' : '🎨 Generate Visuals'}
            </button>

            {/* Results Preview */}
            {results.length > 0 && (
                <div style={{ marginTop: 'var(--space-4)' }}>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>
                        Generated ({results.length})
                    </div>
                    {results.map((result, i) => (
                        <div key={i} style={{
                            padding: 'var(--space-2)',
                            background: 'var(--color-surface-panel)',
                            border: '1px solid var(--glass-border)',
                            borderRadius: 'var(--radius-md)',
                            marginBottom: 'var(--space-2)',
                            fontSize: '10px'
                        }}>
                            <div style={{ color: 'var(--color-text)', fontWeight: 600 }}>{result.type}</div>
                            <div style={{ color: result.status === 'success' ? 'var(--color-success)' : 'var(--color-error)' }}>
                                {result.status} {result.metadata?.image_id && `• ID: ${result.metadata.image_id.slice(0, 8)}...`}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const LEFT_TABS = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'agents', label: 'Agents', icon: Bot },
    { id: 'history', label: 'History', icon: History },
    { id: 'status', label: 'Status', icon: Activity }
];

const RIGHT_TABS = [
    { id: 'visuals', label: 'Visuals', icon: Layout },
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

const RightPanelContent = ({ activeTab, onGeneratedImages }) => {
    switch (activeTab) {
        case 'visuals': return <VisualsToolPanel onGeneratedImages={onGeneratedImages} />;
        case 'prompt': return <PromptCheckerTool />;
        case 'transcribe': return <TranscriptionTool />;
        case 'upload': return <MediaUploadTool />;
        default: return <VisualsToolPanel onGeneratedImages={onGeneratedImages} />;
    }
};

// IDE Gallery View for generated images
const IDEGalleryView = ({ generatedImages }) => {
    if (!generatedImages || generatedImages.length === 0) {
        return (
            <div style={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-text-muted)',
                padding: 'var(--space-6)'
            }}>
                <Code size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-4)' }} />
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 600 }}>Visual Gallery</div>
                <div style={{ fontSize: 'var(--text-sm)', marginTop: 'var(--space-2)', textAlign: 'center' }}>
                    Generated images will appear here.<br />
                    Use the Visuals panel → Generate to create medical visuals.
                </div>
            </div>
        );
    }

    return (
        <div style={{
            height: '100%',
            overflowY: 'auto',
            padding: 'var(--space-4)',
            background: 'var(--gradient-body)'
        }}>
            <div style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 600,
                color: 'var(--color-text)',
                marginBottom: 'var(--space-4)',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-2)'
            }}>
                🎨 Generated Visuals ({generatedImages.length})
            </div>
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                gap: 'var(--space-4)'
            }}>
                {generatedImages.map((img, i) => (
                    <div key={i} style={{
                        background: 'var(--glass-bg)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--glass-border)',
                        overflow: 'hidden',
                        boxShadow: '0 4px 16px rgba(0,0,0,0.2)'
                    }}>
                        {img.image_base64 ? (
                            <img
                                src={`data:image/jpeg;base64,${img.image_base64}`}
                                alt={img.type}
                                style={{
                                    width: '100%',
                                    height: '200px',
                                    objectFit: 'cover'
                                }}
                            />
                        ) : (
                            <div style={{
                                width: '100%',
                                height: '200px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                background: 'var(--color-surface-panel)',
                                color: 'var(--color-text-muted)'
                            }}>
                                {img.status === 'error' ? '❌ Error' : '⏳ Loading...'}
                            </div>
                        )}
                        <div style={{ padding: 'var(--space-3)' }}>
                            <div style={{
                                fontSize: 'var(--text-sm)',
                                fontWeight: 600,
                                color: 'var(--color-text)',
                                textTransform: 'capitalize'
                            }}>
                                {img.type?.replace('_', ' ')}
                            </div>
                            <div style={{
                                fontSize: '10px',
                                color: img.status === 'success' ? 'var(--color-success)' : 'var(--color-error)',
                                marginTop: '4px'
                            }}>
                                {img.status} • {img.generation_model || 'Nano Banana Pro'}
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

const CenterViewContent = ({ activeView, generatedImages }) => {
    if (activeView === 'chat') return <Outlet />;
    if (activeView === 'ide') return <IDEGalleryView generatedImages={generatedImages} />;
    return (
        <div style={{
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-muted)'
        }}>
            <div style={{ textAlign: 'center' }}>
                {activeView === 'langgraph' && <GitBranch size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-4)' }} />}
                {activeView === 'registry' && <Database size={48} style={{ opacity: 0.3, marginBottom: 'var(--space-4)' }} />}
                <div style={{ fontSize: 'var(--text-lg)', fontWeight: 600 }}>
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
    const [rightTab, setRightTab] = useState('visuals');
    const [centerView, setCenterView] = useState('ide');
    const [generatedImages, setGeneratedImages] = useState([]);

    const handleGeneratedImages = (images) => {
        setGeneratedImages(prev => [...images, ...prev]);
        setCenterView('ide'); // Switch to IDE view to show generated images
    };

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
                                    <CenterViewContent activeView={centerView} generatedImages={generatedImages} />
                                </div>
                            </Panel>
                            {showRightPanel && (
                                <>
                                    <ResizeHandle />
                                    <Panel id="right" order={3} defaultSize={22} minSize={15} maxSize={40}>
                                        <div style={glassPanelStyle('right')}>
                                            <PanelTabs tabs={RIGHT_TABS} activeTab={rightTab} onTabChange={setRightTab} />
                                            <div style={{ flex: 1, overflowY: 'auto' }}>
                                                <RightPanelContent activeTab={rightTab} onGeneratedImages={handleGeneratedImages} />
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
