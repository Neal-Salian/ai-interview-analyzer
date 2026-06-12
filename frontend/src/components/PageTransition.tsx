import React, { useEffect, useState } from 'react';

export default function PageTransition({ children, className = '' }: { children: React.ReactNode, className?: string }) {
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        // Trigger the transition shortly after mount to ensure the DOM is ready
        const timer = requestAnimationFrame(() => {
            setIsVisible(true);
        });
        return () => cancelAnimationFrame(timer);
    }, []);

    return (
        <div className={`page-transition ${isVisible ? 'visible' : ''} ${className}`} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {children}
        </div>
    );
}
