import type { EnhancedSession } from '../../pages/SessionsPage';

export interface AdminStats {
    totalRecruiters: number;
    activeUsers: number;
    disabledUsers: number;
    auditLogs: number;
}

interface DashboardStatsProps {
    sessions: EnhancedSession[];
    role?: string | null;
    adminStats?: AdminStats | null;
}

interface StatConfig {
    label: string;
    value: number;
    icon: string;
    colorClass: string;
}

export function DashboardStats({ sessions, role, adminStats }: DashboardStatsProps) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    const baseStats: StatConfig[] = [
        {
            label: 'Total Sessions',
            value: sessions.length,
            icon: 'calendar_month',
            colorClass: 'stat-card__icon--total',
        },
        {
            label: "Today's Sessions",
            value: sessions.filter(s => {
                if (!s.scheduled_at) return false;
                const d = new Date(s.scheduled_at);
                return d >= today && d < tomorrow;
            }).length,
            icon: 'today',
            colorClass: 'stat-card__icon--today',
        },
        {
            label: 'Upcoming',
            value: sessions.filter(s => s.status === 'scheduled').length,
            icon: 'upcoming',
            colorClass: 'stat-card__icon--upcoming',
        },
        {
            label: 'Completed',
            value: sessions.filter(s => s.status === 'completed').length,
            icon: 'task_alt',
            colorClass: 'stat-card__icon--completed',
        },
        {
            label: 'Active Now',
            value: sessions.filter(s => s.status === 'active').length,
            icon: 'radio_button_checked',
            colorClass: 'stat-card__icon--active',
        },
        {
            label: 'Cancelled',
            value: sessions.filter(s => s.status === 'cancelled').length,
            icon: 'cancel',
            colorClass: 'stat-card__icon--cancelled',
        },
        {
            label: 'No-Shows',
            value: sessions.filter(s => s.status === 'no_show').length,
            icon: 'person_off',
            colorClass: 'stat-card__icon--noshow',
        },
    ];

    let stats = [...baseStats];

    if (role === 'ADMIN' && adminStats) {
        stats = [
            {
                label: 'Total Recruiters',
                value: adminStats.totalRecruiters,
                icon: 'group',
                colorClass: 'stat-card__icon--total',
            },
            {
                label: 'Active Users',
                value: adminStats.activeUsers,
                icon: 'verified_user',
                colorClass: 'stat-card__icon--active',
            },
            {
                label: 'Disabled Users',
                value: adminStats.disabledUsers,
                icon: 'person_off',
                colorClass: 'stat-card__icon--cancelled',
            },
            {
                label: 'Audit Events',
                value: adminStats.auditLogs,
                icon: 'list_alt',
                colorClass: 'stat-card__icon--completed',
            },
            ...stats
        ];
    }

    return (
        <div className="stats-row" role="status" aria-label="Session statistics summary">
            {stats.map((stat) => (
                <div key={stat.label} className="stat-card" aria-label={`${stat.value} ${stat.label}`}>
                    <div className={`stat-card__icon ${stat.colorClass}`}>
                        <span className="material-symbols-outlined">{stat.icon}</span>
                    </div>
                    <div>
                        <div className="stat-card__value">{stat.value}</div>
                        <div className="stat-card__label">{stat.label}</div>
                    </div>
                </div>
            ))}
        </div>
    );
}

export function DashboardStatsSkeleton() {
    return (
        <div className="stats-row" aria-label="Loading statistics">
            {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="skeleton-stat-card">
                    <div className="skeleton-shimmer" style={{ width: '44px', height: '44px', borderRadius: '12px' }} />
                    <div>
                        <div className="skeleton-shimmer" style={{ width: '48px', height: '24px', marginBottom: '6px' }} />
                        <div className="skeleton-shimmer" style={{ width: '80px', height: '14px' }} />
                    </div>
                </div>
            ))}
        </div>
    );
}
