import React, { createContext, useContext, useState, useEffect } from 'react';

const StudioContext = createContext();

// Internal agents (always available)
const INTERNAL_AGENTS = [
    { name: 'Medical LLM', type: 'internal', description: 'Healthcare & clinical analysis' },
    { name: 'Research', type: 'internal', description: 'Literature & data research' },
    { name: 'Curriculum', type: 'internal', description: 'Training design' },
    { name: 'Outcomes', type: 'internal', description: 'Analytics & metrics' },
    { name: 'QA/Compliance', type: 'internal', description: 'Regulatory review' }
];

export const StudioProvider = ({ children }) => {
    const [selectedModel, setSelectedModel] = useState(null);
    const [availableModels, setAvailableModels] = useState([...INTERNAL_AGENTS]);
    const [ollamaModels, setOllamaModels] = useState([]);
    const [rightPanelOpen, setRightPanelOpen] = useState(true);
    const [rightPanelContent, setRightPanelContent] = useState('prompt-tools');
    const [complianceMode, setComplianceMode] = useState('auto');

    // Theme State: 'light', 'dark', 'system'
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('dhg-theme') || 'system';
    });

    // Fetch Ollama models on mount
    useEffect(() => {
        const fetchOllamaModels = async () => {
            try {
                const response = await fetch('http://10.0.0.251:8011/api/ollama/models');
                if (response.ok) {
                    const data = await response.json();
                    if (data.models && data.models.length > 0) {
                        const ollamaList = data.models.map(m => ({
                            name: m.name,
                            type: 'ollama',
                            description: `${m.parameter_size} - ${m.family}`,
                            size_gb: m.size_gb
                        }));
                        setOllamaModels(ollamaList);
                        setAvailableModels([...INTERNAL_AGENTS, ...ollamaList]);
                    }
                }
            } catch (error) {
                console.warn('Could not fetch Ollama models:', error);
            }
        };
        fetchOllamaModels();
    }, []);

    // Effect to apply theme
    useEffect(() => {
        const root = document.documentElement;

        const applyTheme = (targetTheme) => {
            if (targetTheme === 'system') {
                const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                root.setAttribute('data-theme', systemDark ? 'dark' : 'light');
            } else {
                root.setAttribute('data-theme', targetTheme);
            }
        };

        applyTheme(theme);
        localStorage.setItem('dhg-theme', theme);

        // Listener for system changes if in system mode
        if (theme === 'system') {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const handleChange = (e) => {
                root.setAttribute('data-theme', e.matches ? 'dark' : 'light');
            };
            mediaQuery.addEventListener('change', handleChange);
            return () => mediaQuery.removeEventListener('change', handleChange);
        }
    }, [theme]);

    const value = {
        selectedModel,
        setSelectedModel,
        availableModels,
        ollamaModels,
        rightPanelOpen,
        setRightPanelOpen,
        rightPanelContent,
        setRightPanelContent,
        complianceMode,
        setComplianceMode,
        theme,
        setTheme
    };


    return (
        <StudioContext.Provider value={value}>
            {children}
        </StudioContext.Provider>
    );
};

export const useStudio = () => {
    const context = useContext(StudioContext);
    if (!context) {
        throw new Error('useStudio must be used within a StudioProvider');
    }
    return context;
};
