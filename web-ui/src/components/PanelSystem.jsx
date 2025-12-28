import React from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { usePanels } from '../context/PanelContext';
import ChatPanel from './panels/ChatPanel';
import ToolsPanel from './panels/ToolsPanel';
import ArtifactsPanel from './panels/ArtifactsPanel';
import AgentStatusPanel from './panels/AgentStatusPanel';

const PANEL_COMPONENTS = {
    chat: ChatPanel,
    tools: ToolsPanel,
    artifacts: ArtifactsPanel,
    agentStatus: AgentStatusPanel
};

const PANEL_MIN_SIZES = {
    chat: 20,
    tools: 15,
    artifacts: 15,
    agentStatus: 15
};

const ResizeHandle = () => (
    <PanelResizeHandle
        style={{
            width: '6px',
            background: 'transparent',
            position: 'relative',
            cursor: 'col-resize',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        }}
    >
        <div style={{
            width: '2px',
            height: '40px',
            background: 'var(--glass-border)',
            borderRadius: '2px',
            transition: 'all 0.2s ease'
        }} />
    </PanelResizeHandle>
);

const PanelSystem = ({ messages, onSendMessage, isProcessing }) => {
    const { layout, setPanelSizes, isPanelOpen } = usePanels();

    const openPanels = layout.order.filter(id => isPanelOpen(id));

    const handleResize = (sizes) => {
        const sizeMap = {};
        openPanels.forEach((id, idx) => {
            sizeMap[id] = sizes[idx];
        });
        setPanelSizes(sizeMap);
    };

    const renderPanel = (panelId) => {
        const Component = PANEL_COMPONENTS[panelId];
        if (!Component) return null;

        const props = panelId === 'chat'
            ? { messages, onSendMessage, isProcessing }
            : {};

        return (
            <Panel
                key={panelId}
                id={panelId}
                minSize={PANEL_MIN_SIZES[panelId]}
                defaultSize={layout.sizes[panelId] || 50}
                style={{
                    overflow: 'hidden',
                    display: 'flex',
                    flexDirection: 'column'
                }}
            >
                <Component {...props} />
            </Panel>
        );
    };

    return (
        <div style={{
            flex: 1,
            overflow: 'hidden',
            display: 'flex'
        }}>
            <PanelGroup
                direction="horizontal"
                onLayout={handleResize}
                style={{ flex: 1 }}
            >
                {openPanels.map((panelId, idx) => (
                    <React.Fragment key={panelId}>
                        {idx > 0 && <ResizeHandle />}
                        {renderPanel(panelId)}
                    </React.Fragment>
                ))}
            </PanelGroup>
        </div>
    );
};

export default PanelSystem;
