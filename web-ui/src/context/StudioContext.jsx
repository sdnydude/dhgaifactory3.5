import React, { createContext, useContext, useState, useEffect } from 'react';

const StudioContext = createContext();

// CME Agent Team (12-agent system)
const CME_AGENTS = [
    // Research & Analysis
    { name: 'Medical Research', type: 'cme-agent', description: 'Research guidelines & literature', category: 'research' },
    { name: 'Clinical Practice', type: 'cme-agent', description: 'Analyze practice patterns', category: 'research' },
    { name: 'Gap Analysis', type: 'cme-agent', description: 'Identify knowledge gaps', category: 'research' },
    // Program Design
    { name: 'Needs Assessment', type: 'cme-agent', description: 'Generate needs assessment', category: 'design' },
    { name: 'Learning Objectives', type: 'cme-agent', description: 'Create learning objectives', category: 'design' },
    { name: 'Curriculum Design', type: 'cme-agent', description: 'Design curriculum structure', category: 'design' },
    { name: 'Research Protocol', type: 'cme-agent', description: 'Create research protocols', category: 'design' },
    // Marketing
    { name: 'Marketing Plan', type: 'cme-agent', description: 'Develop marketing strategy', category: 'marketing' },
    // Final Deliverables
    { name: 'Grant Writer', type: 'cme-agent', description: 'Write grant application', category: 'deliverables' },
    { name: 'Prose QA', type: 'cme-agent', description: 'Quality assurance check', category: 'qa' },
    { name: 'Compliance Review', type: 'cme-agent', description: 'Regulatory compliance', category: 'qa' }
];

// Recipe workflows (orchestrated agent chains)
const CME_RECIPES = [
    { name: 'Full Pipeline', type: 'cme-recipe', description: 'Complete CME grant workflow', agents: 'all' },
    { name: 'Needs Package', type: 'cme-recipe', description: 'Research → Gap → Needs Assessment', agents: '1-3,5' },
    { name: 'Curriculum Package', type: 'cme-recipe', description: 'Design curriculum + objectives', agents: '5-8' },
    { name: 'Grant Package', type: 'cme-recipe', description: 'Grant writing + QA + compliance', agents: '10-12' }
];


export const StudioProvider = ({ children }) => {
    const [selectedModel, setSelectedModel] = useState(null);
    const [availableModels, setAvailableModels] = useState([...CME_AGENTS, ...CME_RECIPES]);
    const [cmeAgents] = useState(CME_AGENTS);
    const [cmeRecipes] = useState(CME_RECIPES);
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
                        setAvailableModels([...CME_AGENTS, ...CME_RECIPES, ...ollamaList]);
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
        cmeAgents,
        cmeRecipes,
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
