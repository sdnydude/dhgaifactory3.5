import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const PanelContext = createContext(null);

const DEFAULT_LAYOUT = {
    panels: ['chat', 'tools'],
    sizes: { chat: 60, tools: 40 },
    collapsed: {},
    order: ['chat', 'tools', 'artifacts', 'agentStatus']
};

const STORAGE_KEY = 'dhg-panel-layout';

export const PanelProvider = ({ children }) => {
    const [layout, setLayout] = useState(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : DEFAULT_LAYOUT;
    });

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
    }, [layout]);

    const togglePanel = useCallback((panelId) => {
        setLayout(prev => {
            const panels = prev.panels.includes(panelId)
                ? prev.panels.filter(p => p !== panelId)
                : [...prev.panels, panelId];
            return { ...prev, panels };
        });
    }, []);

    const setPanelSizes = useCallback((sizes) => {
        setLayout(prev => ({ ...prev, sizes: { ...prev.sizes, ...sizes } }));
    }, []);

    const collapsePanel = useCallback((panelId, collapsed) => {
        setLayout(prev => ({
            ...prev,
            collapsed: { ...prev.collapsed, [panelId]: collapsed }
        }));
    }, []);

    const reorderPanels = useCallback((newOrder) => {
        setLayout(prev => ({ ...prev, order: newOrder }));
    }, []);

    const resetLayout = useCallback(() => {
        setLayout(DEFAULT_LAYOUT);
    }, []);

    const isPanelOpen = useCallback((panelId) => {
        return layout.panels.includes(panelId);
    }, [layout.panels]);

    const isPanelCollapsed = useCallback((panelId) => {
        return layout.collapsed[panelId] || false;
    }, [layout.collapsed]);

    return (
        <PanelContext.Provider value={{
            layout,
            togglePanel,
            setPanelSizes,
            collapsePanel,
            reorderPanels,
            resetLayout,
            isPanelOpen,
            isPanelCollapsed,
            availablePanels: ['chat', 'tools', 'artifacts', 'agentStatus']
        }}>
            {children}
        </PanelContext.Provider>
    );
};

export const usePanels = () => {
    const context = useContext(PanelContext);
    if (!context) {
        throw new Error('usePanels must be used within a PanelProvider');
    }
    return context;
};

export default PanelContext;
