import React, { useState } from 'react';
import './MainLayout.css';

// Placeholder panels (will be replaced by real components later)
const ChatPanelPlaceholder = () => <div className="panel-content">Chat Panel</div>;
const MainPanelPlaceholder = () => <div className="panel-content">Main Dashboard</div>;
const ResultsPanelPlaceholder = () => <div className="panel-content">Results Panel</div>;

const MainLayout = () => {
    return (
        <div className="main-layout">
            <aside className="panel-left">
                <ChatPanelPlaceholder />
            </aside>

            <main className="panel-center">
                <MainPanelPlaceholder />
            </main>

            <aside className="panel-right">
                <ResultsPanelPlaceholder />
            </aside>
        </div>
    );
};

export default MainLayout;
