import type { EnhancedSession } from '../../pages/SessionsPage';
import { PanelSection } from './PanelSection';
import { AvatarInitials } from './AvatarInitials';
import { StatusBadge } from './StatusBadge';
import { formatSessionDate } from './FormatDate';

interface SessionDetailsDrawerProps {
    session: EnhancedSession | null;
    isOpen: boolean;
    onClose: () => void;
    onStart: () => void;
    onEnd: () => void;
    onJoin: () => void;
    onViewReport: () => void;
}

export function SessionDetailsDrawer({ session, isOpen, onClose, onStart, onEnd, onJoin, onViewReport }: SessionDetailsDrawerProps) {
    if (!isOpen || !session) return null;

    return (
        <>
            {/* Backdrop */}
            <div 
                style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)',
                    zIndex: 999,
                    transition: 'opacity 0.3s ease'
                }}
                onClick={onClose}
            />

            {/* Drawer */}
            <div
                style={{
                    position: 'fixed',
                    top: 0,
                    right: 0,
                    width: '100%',
                    maxWidth: '450px',
                    height: '100vh',
                    backgroundColor: 'var(--bg)',
                    boxShadow: '-4px 0 24px rgba(0, 0, 0, 0.15)',
                    zIndex: 1000,
                    display: 'flex',
                    flexDirection: 'column',
                    transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
                    transition: 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)',
                    overflowY: 'auto'
                }}
            >
                {/* Header */}
                <div style={{ padding: '24px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <h2 style={{ fontSize: '18px', fontWeight: 600, margin: 0 }}>Session Details</h2>
                    <button 
                        onClick={onClose}
                        style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer', padding: '4px', display: 'flex' }}
                    >
                        <span className="material-symbols-outlined">close</span>
                    </button>
                </div>

                {/* Content */}
                <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px', flex: 1 }}>
                    {/* Candidate Info */}
                    <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                        <AvatarInitials name={session.candidate} size={56} />
                        <div>
                            <h3 style={{ fontSize: '20px', fontWeight: 600, margin: '0 0 4px 0' }}>{session.candidate || 'Unknown Candidate'}</h3>
                            <div style={{ color: 'var(--text-secondary)', fontSize: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>work</span>
                                {session.job || 'No Job Specified'}
                            </div>
                        </div>
                    </div>

                    {/* Status & Time */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Status</span>
                            <StatusBadge status={session.status} />
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Scheduled</span>
                            <span style={{ fontSize: '13px', fontWeight: 500 }}>{formatSessionDate(session.scheduled_at)}</span>
                        </div>
                    </div>

                    {/* Quick Actions based on Status */}
                    <div style={{ marginTop: '8px' }}>
                        {session.status === 'scheduled' && (
                            <button
                                onClick={onStart}
                                style={{
                                    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                    backgroundColor: 'var(--accent)', color: '#fff', padding: '12px', borderRadius: '8px', 
                                    border: 'none', fontWeight: 600, cursor: 'pointer', fontSize: '14px'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>play_circle</span>
                                Start Session
                            </button>
                        )}
                        {session.status === 'active' && (
                            <div style={{ display: 'flex', gap: '12px' }}>
                                <button
                                    onClick={onJoin}
                                    style={{
                                        flex: 2, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                        backgroundColor: 'var(--accent)', color: '#fff', padding: '12px', borderRadius: '8px', 
                                        border: 'none', fontWeight: 600, cursor: 'pointer', fontSize: '14px'
                                    }}
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>login</span>
                                    Join
                                </button>
                                <button
                                    onClick={onEnd}
                                    style={{
                                        flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                        backgroundColor: 'transparent', color: 'var(--danger)', border: '1px solid var(--danger)', 
                                        padding: '12px', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', fontSize: '14px'
                                    }}
                                >
                                    <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>stop_circle</span>
                                    End
                                </button>
                            </div>
                        )}
                        {session.status === 'completed' && (
                            <button
                                onClick={onViewReport}
                                style={{
                                    width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                    backgroundColor: 'var(--bg-surface-high)', color: 'var(--text-primary)', border: '1px solid var(--border)', 
                                    padding: '12px', borderRadius: '8px', fontWeight: 600, cursor: 'pointer', fontSize: '14px'
                                }}
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>assessment</span>
                                View Report
                            </button>
                        )}
                    </div>

                    <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '8px 0' }} />

                    {/* Panel Section */}
                    <div style={{ margin: '-24px -20px 0 -20px' }}>
                        <PanelSection sessionId={session.session_id} />
                    </div>
                </div>
            </div>
        </>
    );
}
