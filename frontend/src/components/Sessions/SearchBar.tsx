import { useEffect, useRef, useCallback } from 'react';

interface SearchBarProps {
    value: string;
    onChange: (value: string) => void;
}

export function SearchBar({ value, onChange }: SearchBarProps) {
    const inputRef = useRef<HTMLInputElement>(null);

    const handleKeyDown = useCallback((e: KeyboardEvent) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            inputRef.current?.focus();
        }
    }, []);

    useEffect(() => {
        document.addEventListener('keydown', handleKeyDown);
        return () => document.removeEventListener('keydown', handleKeyDown);
    }, [handleKeyDown]);

    const isMac = typeof navigator !== 'undefined' && navigator.platform.toUpperCase().indexOf('MAC') >= 0;

    return (
        <div className="search-bar" role="search">
            <span className="search-bar__icon material-symbols-outlined" aria-hidden="true">
                search
            </span>
            <input
                ref={inputRef}
                type="text"
                className="search-bar__input"
                placeholder="Search candidates, roles, or sessions..."
                value={value}
                onChange={(e) => onChange(e.target.value)}
                aria-label="Search sessions"
            />
            {value ? (
                <button
                    className="search-bar__clear"
                    onClick={() => { onChange(''); inputRef.current?.focus(); }}
                    aria-label="Clear search"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>close</span>
                </button>
            ) : (
                <span className="search-bar__shortcut" aria-hidden="true">
                    {isMac ? '⌘K' : 'Ctrl+K'}
                </span>
            )}
        </div>
    );
}
