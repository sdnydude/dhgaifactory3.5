import React, { createContext, useContext, useState } from 'react';

const StudioContext = createContext();

export const StudioProvider = ({ children }) => {
    const [selectedModel, setSelectedModel] = useState(null);
    const [rightPanelOpen, setRightPanelOpen] = useState(true);
    const [rightPanelContent, setRightPanelContent] = useState('prompt-tools');
    const [complianceMode, setComplianceMode] = useState('auto');

    // Theme State: 'light', 'dark', 'system'
    const [theme, setTheme] = useState(() => {
        return localStorage.getItem('dhg-theme') || 'system';
    });

    // Effect to apply theme
    React.useEffect(() => {
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
