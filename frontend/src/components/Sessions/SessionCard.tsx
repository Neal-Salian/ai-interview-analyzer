import React, { useEffect, useState } from 'react';
import type { EnhancedSession } from '../../pages/SessionsPage';
import { AvatarInitials } from './AvatarInitials';
import { StatusBadge } from './StatusBadge';
import { formatSessionDate } from './FormatDate';
import client from '../../api/client';

interface SessionCardProps {
    session: EnhancedSession;
    onClick: () => void;
    onStart: (e: React.MouseEvent) => void;
    onEnd: (e: React.MouseEvent) => void;
    onJoin: (e: React.MouseEvent) => void;
    onViewReport: (e: React.MouseEvent) => void;
}

export function SessionCard({ session, onClick, onStart, onEnd, onJoin, onViewReport }: SessionCardProps) {
    const [panelCount, setPanelCount] = useState<number | null>(null);

    useEffect(() => {
        let isMounted = true;
        const fetchPanelCount = async () => {
            try {
                const res = await client.get(`/sessions/${session.session_id}/panel`);
                if (isMounted) {
                    setPanelCount(res.data.length);
                }
            } catch (err) {
                console.error('Failed to fetch panel count', err);
            }
        };
        fetchPanelCount();
        return () => { isMounted = false; };
    }, [session.session_id]);

    const handleActionClick = (e: React.MouseEvent, action: (e: React.MouseEvent) => void) => {
        e.stopPropagation(); // Prevent opening drawer
        action(e);
    };

    return (
        <div 
            onClick={onClick}
            style={{
                backgroundColor: 'var(--bg-surface)',
                borderRadius: '12px',
                border: '1px solid var(--border)',
                boxShadow: 'var(--shadow-card)',
                padding: '1.5rem',
                display: 'flex',
                flexDirection: 'column',
                gap: '1.25rem',
                opacity: session.status === 'completed' ? 0.8 : 1,
                transition: 'transform 0.2s, box-shadow 0.2s, opacity 0.2s',
                cursor: 'pointer',
                minHeight: '220px',
                maxHeight: '280px',
                position: 'relative'
            }}
            onMouseEnter={e => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = 'var(--shadow-elevated)';
                e.currentTarget.style.opacity = '1';
            }}
            onMouseLeave={e => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = 'var(--shadow-card)';
                e.currentTarget.style.opacity = session.status === 'completed' ? '0.8' : '1';
            }}
        >
            {/* Header: Avatar, Info, Status */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                <div style={{ display: 'flex', gap: '1rem', flex: 1, minWidth: 0 }}>
                    <AvatarInitials name={session.candidate} size={44} />
                    <div style={{ minWidth: 0 }}>
                        <h2 style={{ 
                            fontSize: '16px', 
                            fontWeight: 600, 
                            margin: '0 0 4px 0', 
                            whiteSpace: 'nowrap', 
                            overflow: 'hidden', 
                            textOverflow: 'ellipsis' 
                        }}>
                            {session.candidate || 'Unknown Candidate'}
                        </h2>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '4px' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>work</span>
                            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{session.job || 'No Job Specified'}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)', fontSize: '13px' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>schedule</span>
                            {formatSessionDate(session.scheduled_at)}
                        </div>
                    </div>
                </div>
                <StatusBadge status={session.status} />
            </div>

            {/* Metadata Row */}
            <div style={{ 
                display: 'flex', 
                gap: '12px', 
                marginTop: 'auto',
                fontSize: '13px', 
                color: 'var(--text-secondary)',
                backgroundColor: 'var(--bg)',
                padding: '10px 12px',
                borderRadius: '8px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>group</span>
                    {panelCount !== null ? `${panelCount} Panel Member${panelCount !== 1 ? 's' : ''}` : 'Loading...'}
                </div>
                {session.status === 'active' && session.metrics && (
                    <>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>forum</span>
                            Ratio {session.metrics.talkCandidate}% / {session.metrics.talkInterviewer}%
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>mood</span>
                            {session.metrics.sentiment}%
                        </div>
                    </>
                )}
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                {session.status === 'active' && (
                    <>
                        <button
                            onClick={(e) => handleActionClick(e, onJoin)}
                            style={{
                                flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                                backgroundColor: 'var(--accent)', backgroundImage: 'var(--accent-gradient)', color: '#fff', 
                                border: 'none', padding: '10px', borderRadius: '6px', fontWeight: 500, cursor: 'pointer', fontSize: '13px'
                            }}
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>login</span>
                            Join Session
                        </button>
                        <button
                            onClick={(e) => handleActionClick(e, onEnd)}
                            style={{
                                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                                backgroundColor: 'transparent', border: '1px solid var(--danger)', color: 'var(--danger)', 
                                padding: '10px 12px', borderRadius: '6px', fontWeight: 500, cursor: 'pointer', fontSize: '13px'
                            }}
                            title="End Session"
                        >
                            <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>stop_circle</span>
                        </button>
                    </>
                )}
                {session.status === 'scheduled' && (
                    <button
                        onClick={(e) => handleActionClick(e, onStart)}
                        style={{
                            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                            backgroundColor: 'var(--bg-surface-high)', border: '1px solid var(--border)', color: 'var(--text-primary)', 
                            padding: '10px', borderRadius: '6px', fontWeight: 500, cursor: 'pointer', fontSize: '13px'
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>play_circle</span>
                        Start Session
                    </button>
                )}
                {session.status === 'processing' && (
                    <button
                        disabled
                        style={{
                            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                            backgroundColor: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)', 
                            padding: '10px', borderRadius: '6px', fontWeight: 500, cursor: 'not-allowed', fontSize: '13px', opacity: 0.7
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '18px', animation: 'spin 2s linear infinite' }}>sync</span>
                        Processing...
                    </button>
                )}
                {session.status === 'completed' && (
                    <button
                        onClick={(e) => handleActionClick(e, onViewReport)}
                        style={{
                            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px',
                            backgroundColor: 'transparent', color: 'var(--text-secondary)', border: '1px solid var(--border)', 
                            padding: '10px', borderRadius: '6px', fontWeight: 500, cursor: 'pointer', fontSize: '13px'
                        }}
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: '16px' }}>assessment</span>
                        View Report
                    </button>
                )}
            </div>
        </div>
    );
}
