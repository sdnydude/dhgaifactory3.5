import React from 'react';

const HarmonicLoader = () => {
    return (
        <div className="flex items-center justify-center gap-1.5 h-8">
            <div className="w-1.5 h-6 bg-dhg-primary rounded-full animate-wave" style={{ animationDelay: '0s' }}></div>
            <div className="w-1.5 h-6 bg-dhg-accent rounded-full animate-wave" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-1.5 h-6 bg-dhg-success rounded-full animate-wave" style={{ animationDelay: '0.2s' }}></div>
            <div className="w-1.5 h-6 bg-dhg-primary rounded-full animate-wave" style={{ animationDelay: '0.3s' }}></div>
            <div className="w-1.5 h-6 bg-dhg-accent rounded-full animate-wave" style={{ animationDelay: '0.4s' }}></div>
        </div>
    );
};

export default HarmonicLoader;
