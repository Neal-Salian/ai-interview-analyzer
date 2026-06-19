import { useEffect, useState } from 'react';
import Navbar from '../../components/Navbar';
import PageTransition from '../../components/PageTransition';
import client from '../../api/client';
import { useTheme } from '../../context/ThemeContext';

interface User {
    id: string;
    username: string;
    role: string;
    is_active: boolean;
}

export default function UsersPage() {
    const [users, setUsers] = useState<User[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchUsers = async () => {
        setLoading(true);
        setError('');
        try {
            const res = await client.get('/admin/users');
            setUsers(res.data);
        } catch (err: any) {
            console.error('Failed to fetch users', err);
            setError(err.response?.data?.detail || 'Failed to fetch users.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const toggleStatus = async (user: User) => {
        try {
            if (user.is_active) {
                await client.patch(`/admin/users/${user.id}/disable`);
            } else {
                await client.patch(`/admin/users/${user.id}/enable`);
            }
            await fetchUsers();
        } catch (err: any) {
            console.error('Failed to toggle status', err);
            alert('Failed to update user status.');
        }
    };

    const changeRole = async (user: User, newRole: string) => {
        if (user.role === newRole) return;
        try {
            await client.patch(`/admin/users/${user.id}/role`, { role: newRole });
            await fetchUsers();
        } catch (err: any) {
            console.error('Failed to change role', err);
            alert('Failed to update user role.');
        }
    };

    return (
        <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text-primary)' }}>
            <Navbar />
            <PageTransition>
                <div style={{ padding: '32px 24px', maxWidth: '1200px', margin: '0 auto' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                        <h1 style={{ fontSize: '24px', fontWeight: 700, fontFamily: 'var(--font-heading)' }}>Users</h1>
                        <button onClick={fetchUsers} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text-secondary)', padding: '8px 16px', borderRadius: 'var(--radius)', cursor: 'pointer' }}>
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
                            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>Loading users...</div>
                        ) : users.length === 0 ? (
                            <div style={{ padding: '32px', textAlign: 'center', color: 'var(--text-secondary)' }}>No users found.</div>
                        ) : (
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>Username</th>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>Role</th>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase' }}>Status</th>
                                        <th style={{ padding: '16px', fontWeight: 600, color: 'var(--text-secondary)', fontSize: '12px', textTransform: 'uppercase', textAlign: 'right' }}>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {users.map(user => (
                                        <tr key={user.id} style={{ borderBottom: '1px solid var(--border)' }}>
                                            <td style={{ padding: '16px', fontSize: '14px' }}>{user.username}</td>
                                            <td style={{ padding: '16px', fontSize: '14px' }}>
                                                <select
                                                    value={user.role}
                                                    onChange={e => changeRole(user, e.target.value)}
                                                    style={{
                                                        background: 'var(--bg)',
                                                        color: 'var(--text-primary)',
                                                        border: '1px solid var(--border)',
                                                        padding: '4px 8px',
                                                        borderRadius: '4px',
                                                        fontSize: '13px'
                                                    }}
                                                >
                                                    <option value="ADMIN">ADMIN</option>
                                                    <option value="RECRUITER">RECRUITER</option>
                                                </select>
                                            </td>
                                            <td style={{ padding: '16px', fontSize: '14px' }}>
                                                <span style={{
                                                    background: user.is_active ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                                                    color: user.is_active ? '#22c55e' : '#ef4444',
                                                    padding: '4px 8px',
                                                    borderRadius: '12px',
                                                    fontSize: '11px',
                                                    fontWeight: 600
                                                }}>
                                                    {user.is_active ? 'ACTIVE' : 'DISABLED'}
                                                </span>
                                            </td>
                                            <td style={{ padding: '16px', textAlign: 'right' }}>
                                                <button
                                                    onClick={() => toggleStatus(user)}
                                                    style={{
                                                        background: 'transparent',
                                                        border: '1px solid var(--border)',
                                                        color: user.is_active ? '#ef4444' : '#22c55e',
                                                        padding: '6px 12px',
                                                        borderRadius: 'var(--radius)',
                                                        fontSize: '12px',
                                                        cursor: 'pointer'
                                                    }}
                                                >
                                                    {user.is_active ? 'Disable' : 'Enable'}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        )}
                    </div>
                </div>
            </PageTransition>
        </div>
    );
}
