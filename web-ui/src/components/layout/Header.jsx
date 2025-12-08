import React from 'react';
import './Header.css';

const Header = () => {
    return (
        <header className="header">
            <div className="header-left">
                <div className="logo-area">
                    <span className="logo-icon">🏭</span>
                    <span className="logo-text">DHG AI Factory</span>
                </div>
                <nav className="main-nav">
                    <a href="#" className="nav-item active">Generate</a>
                    <a href="#" className="nav-item">History</a>
                    <a href="#" className="nav-item">Settings</a>
                </nav>
            </div>

            <div className="header-right">
                <div className="mode-badge">
                    <span className="status-dot"></span>
                    CME Compliant
                </div>
                <div className="user-profile">
                    <div className="avatar">SW</div>
                </div>
            </div>
        </header>
    );
};

export default Header;
