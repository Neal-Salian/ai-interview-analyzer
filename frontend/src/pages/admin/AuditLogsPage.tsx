import { useEffect, useState } from 'react';
import Navbar from '../../components/Navbar';
import PageTransition from '../../components/PageTransition';
import client from '../../api/client';

interface AuditLog {
    id: string;
    action: string;
    user_id: string;
    ip_address: string;
    metadata_info?: any;
    created_at: string;
}

export default function AuditLogsPage() {
    const [logs, setLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchLogs = async () => {
        setLoading(true);
        setError('');
        try {
            // NOTE: This endpoint may not exist yet. Documenting separately.
            const res = await client.get('/admin/audit-logs');
            setLogs(res.data);
        } catch (err: any) {
            console.error('Failed to fetch audit logs', err);
            if (err.response?.status === 404) {
                setError('Audit logs endpoint (/admin/audit-logs) is not currently implemented on the backend.');
            } else {
                setError('Failed to fetch audit logs. Backend endpoint may be missing.');
            }
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, []);

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />
            <PageTransition>
                <div style={{ padding: '32px 24px', maxWidth: '1200px', margin: '0 auto' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                        <h1 style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>Audit Logs</h1>
                        <button onClick={fetchLogs} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)', padding: '8px 16px', borderRadius: 'var(--radius)', cursor: 'pointer' }}>
                            Refresh
                        </button>
                    </div>

                    {error && (
                        <div style={{ background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', padding: '16px', borderRadius: 'var(--radius)', marginBottom: '24px' }}>
                            {error}
                        </div>
                    )}

                    <div style={{ background: 'var(--bg-surface-high)', borderRadius: '16px', border: '1px solid var(--border)', overflow: 'hidden' }}>
                        {loading ? (
                            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading logs...</div>
                        ) : logs.length === 0 && !error ? (
                            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>No audit logs found.</div>
                        ) : logs.length > 0 ? (
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>Timestamp</th>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>User ID</th>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>Action</th>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>IP Address</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {logs.map(log => (
                                        <tr key={log.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                            <td style={{ padding: '16px', fontSize: '14px' }}>{new Date(log.created_at).toLocaleString()}</td>
                                            <td style={{ padding: '16px', fontSize: '14px', fontFamily: 'monospace' }}>{log.user_id}</td>
                                            <td style={{ padding: '16px', fontSize: '14px' }}>
                                                <span style={{ background: 'var(--bg)', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', border: '1px solid var(--border)' }}>
                                                    {log.action}
                                                </span>
                                            </td>
                                            <td style={{ padding: '16px', fontSize: '14px', color: 'var(--text-secondary)' }}>{log.ip_address || 'N/A'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : null}
                    </div>
                </div>
            </PageTransition>
        </div>
    );
}
