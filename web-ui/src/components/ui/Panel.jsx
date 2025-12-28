import React from 'react';
import { motion } from 'framer-motion';
import '../../styles/components.css'; // Ensure creating specific styles or use util classes

const Panel = ({ children, className = '', title, actions }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className={`dhg-panel ${className}`}
            style={{
                background: 'var(--glass-bg)',
                backdropFilter: 'var(--glass-blur)',
                border: '1px solid var(--glass-border)',
                borderRadius: 'var(--radius-lg)',
                boxShadow: 'var(--glass-shadow)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
            }}
        >
            {(title || actions) && (
                <div style={{
                    padding: 'var(--space-4)',
                    borderBottom: '1px solid var(--glass-border)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(255,255,255,0.03)'
                }}>
                    {title && <h3 style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 600 }}>{title}</h3>}
                    {actions && <div className="panel-actions">{actions}</div>}
                </div>
            )}
            <div style={{ padding: 'var(--space-4)', flex: 1, overflowY: 'auto' }}>
                {children}
            </div>
        </motion.div>
    );
};

export default Panel;
