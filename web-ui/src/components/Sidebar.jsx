import React from 'react';
import { Plus, MessageSquare, Settings, Shield, User } from 'lucide-react';
import { Link } from 'react-router-dom';

const Sidebar = ({ onNewChat }) => {
    return (
        <div className="sidebar">
            <div style={{ padding: 'var(--space-4)' }}>
                <button
                    onClick={onNewChat}
                    className="sidebar__new-button"
                >
                    <Plus size={18} />
                    <span>New Composition</span>
                </button>
            </div>

            <div style={{ flex: 1, overflowY: 'auto', padding: '0 var(--space-2)' }}>
                <div style={{
                    fontSize: '0.6875rem',
                    fontWeight: 700,
                    color: 'var(--color-text-muted)',
                    padding: 'var(--space-2) var(--space-3)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em'
                }}>
                    Recents
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
                    <Link to="/chat" className="sidebar__nav-item">
                        <MessageSquare size={16} />
                        <span>CME Needs Assessment</span>
                    </Link>
                    <Link to="/chat" className="sidebar__nav-item">
                        <MessageSquare size={16} />
                        <span>Non-CME Strategy</span>
                    </Link>
                </div>
            </div>

            <div style={{ padding: 'var(--space-2)', display: 'flex', flexDirection: 'column', gap: 'var(--space-1)', borderTop: '1px solid var(--color-border)' }}>
                <Link to="/walkthrough" className="sidebar__nav-item">
                    <MessageSquare size={16} />
                    <span>System Walkthrough</span>
                </Link>
                <Link to="/admin" className="sidebar__nav-item">
                    <Shield size={16} />
                    <span>Admin Panel</span>
                </Link>
                <Link to="/settings" className="sidebar__nav-item">
                    <Settings size={16} />
                    <span>Settings</span>
                </Link>
            </div>
        </div>
    );
};

export default Sidebar;
