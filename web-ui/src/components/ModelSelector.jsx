import React, { useState } from 'react';
import { ChevronDown, Cpu, Cloud, Zap, Check, Server } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStudio } from '../context/StudioContext';

const ModelSelector = ({ selectedModel, onSelectModel }) => {
    const [isOpen, setIsOpen] = useState(false);
    const { availableModels, ollamaModels } = useStudio();

    // Build model groups dynamically
    const modelGroups = [
        {
            category: 'Cloud Models',
            icon: <Cloud size={16} />,
            items: [
                { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro', provider: 'Google', type: 'cloud' },
                { id: 'claude-haiku-4-5-20251015', name: 'Claude Haiku 4.5', provider: 'Anthropic', type: 'cloud' },
                { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'OpenAI', type: 'cloud' }
            ]
        },
        {
            category: 'Open Models (Ollama)',
            icon: <Server size={16} />,
            items: ollamaModels.map(m => ({
                id: m.name,
                name: m.name.replace(':latest', ''),
                provider: m.description || 'Ollama',
                type: 'ollama'
            }))
        },
        {
            category: 'DHG Agents',
            icon: <Zap size={16} />,
            items: availableModels
                .filter(m => m.type === 'internal')
                .map(m => ({
                    id: m.name.toLowerCase().replace(/[^a-z0-9]/g, '-'),
                    name: m.name,
                    provider: m.description || 'Internal',
                    type: 'internal'
                }))
        }
    ].filter(group => group.items.length > 0);

    // Default to first agent if nothing selected
    const active = selectedModel || modelGroups[0]?.items[0] || { id: 'default', name: 'Select Model' };

    return (
        <div style={{ position: 'relative', zIndex: 50 }}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-2)',
                    padding: 'var(--space-2) var(--space-4)',
                    background: 'var(--glass-bg)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--color-text)',
                    cursor: 'pointer',
                    minWidth: '200px',
                    justifyContent: 'space-between',
                    transition: 'all 0.2s ease'
                }}
                className="hover-glass"
            >
                <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                    <span style={{ color: active.type === 'ollama' ? '#10b981' : 'var(--color-dhg-primary)' }}>
                        {active.type === 'ollama' ? <Server size={16} /> :
                            active.type === 'cloud' ? <Cloud size={16} /> : <Zap size={16} />}
                    </span>
                    <span style={{ fontWeight: 500 }}>{active.name}</span>
                </span>
                <ChevronDown size={14} style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s' }} />
            </button>

            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 5 }}
                        style={{
                            position: 'absolute',
                            top: '100%',
                            left: 0,
                            width: '280px',
                            marginTop: 'var(--space-2)',
                            background: 'var(--color-surface-panel)',
                            border: '1px solid var(--glass-border)',
                            borderRadius: 'var(--radius-lg)',
                            padding: 'var(--space-2)',
                            boxShadow: 'var(--shadow-xl)',
                            maxHeight: '400px',
                            overflowY: 'auto'
                        }}
                    >
                        {modelGroups.map((group) => (
                            <div key={group.category} style={{ marginBottom: 'var(--space-2)' }}>
                                <div style={{
                                    padding: 'var(--space-2)',
                                    fontSize: 'var(--text-xs)',
                                    color: 'var(--color-text-muted)',
                                    textTransform: 'uppercase',
                                    fontWeight: 600,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--space-2)'
                                }}>
                                    {group.icon} {group.category}
                                </div>
                                {group.items.map((item) => (
                                    <button
                                        key={item.id}
                                        onClick={() => {
                                            onSelectModel?.(item);
                                            setIsOpen(false);
                                        }}
                                        style={{
                                            width: '100%',
                                            textAlign: 'left',
                                            padding: 'var(--space-2) var(--space-3)',
                                            borderRadius: 'var(--radius-md)',
                                            background: active.id === item.id ?
                                                (item.type === 'ollama' ? '#10b981' : 'var(--color-dhg-primary)') :
                                                'transparent',
                                            color: active.id === item.id ? 'white' : 'var(--color-text)',
                                            border: 'none',
                                            cursor: 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'space-between',
                                            marginBottom: '2px',
                                            transition: 'background 0.2s'
                                        }}
                                        className={active.id !== item.id ? "hover-item" : ""}
                                    >
                                        <div>
                                            <div style={{ fontSize: 'var(--text-sm)' }}>{item.name}</div>
                                            <div style={{ fontSize: '10px', opacity: 0.7 }}>{item.provider}</div>
                                        </div>
                                        {active.id === item.id && <Check size={14} />}
                                    </button>
                                ))}
                            </div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
            <style>{`
        .hover-glass:hover {
          background: var(--glass-bg-hover) !important;
          border-color: var(--color-dhg-primary) !important;
        }
        .hover-item:hover {
          background: rgba(255,255,255,0.05) !important;
        }
      `}</style>
        </div>
    );
};

export default ModelSelector;
