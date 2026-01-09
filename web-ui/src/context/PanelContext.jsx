import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const PanelContext = createContext(null);

const DEFAULT_LAYOUT = {
    panels: ['chat', 'tools'],
    sizes: { chat: 60, tools: 40 },
    collapsed: {},
    order: ['chat', 'tools', 'artifacts', 'agentStatus']
};

const STORAGE_KEY = 'dhg-panel-layout';

const validateLayout = (layout) => {
    if (!layout || typeof layout !== 'object') return DEFAULT_LAYOUT;

    return {
        panels: Array.isArray(layout.panels) ? layout.panels : DEFAULT_LAYOUT.panels,
        sizes: (layout.sizes && typeof layout.sizes === 'object') ? layout.sizes : DEFAULT_LAYOUT.sizes,
        collapsed: (layout.collapsed && typeof layout.collapsed === 'object') ? layout.collapsed : DEFAULT_LAYOUT.collapsed,
        order: Array.isArray(layout.order) ? layout.order : DEFAULT_LAYOUT.order
    };
};

export const PanelProvider = ({ children }) => {
    const [layout, setLayout] = useState(() => {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                return validateLayout(parsed);
            }
        } catch (err) {
            console.warn('Failed to parse panel layout from localStorage, using defaults:', err);
            localStorage.removeItem(STORAGE_KEY);
        }
        return DEFAULT_LAYOUT;
    });

    useEffect(() => {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(layout));
        } catch {
            // Ignore localStorage errors
        }
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
        localStorage.removeItem(STORAGE_KEY);
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
