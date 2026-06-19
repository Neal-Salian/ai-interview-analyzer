

interface AvatarInitialsProps {
    name: string | null;
    size?: number;
}

export function AvatarInitials({ name, size = 40 }: AvatarInitialsProps) {
    const getInitials = (fullName: string) => {
        const names = fullName.trim().split(' ').filter(Boolean);
        if (names.length === 0) return '?';
        if (names.length === 1) return names[0].charAt(0).toUpperCase();
        return (names[0].charAt(0) + names[names.length - 1].charAt(0)).toUpperCase();
    };

    const initials = name ? getInitials(name) : '?';

    // A subtle gradient or background color based on name length or just a generic one
    const bgColor = 'var(--bg-surface-high)';
    const textColor = 'var(--text-primary)';

    return (
        <div style={{
            width: `${size}px`,
            height: `${size}px`,
            minWidth: `${size}px`,
            borderRadius: '50%',
            backgroundColor: bgColor,
            color: textColor,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: `${size * 0.4}px`,
            fontWeight: 600,
            border: '1px solid var(--border)',
            boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.05)'
        }}>
            {initials}
        </div>
    );
}
