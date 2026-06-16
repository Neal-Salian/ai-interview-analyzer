import { useEffect, useState } from 'react';
import client from '../../api/client';

export function PanelSection({ sessionId }: { sessionId: string }) {
    const [members, setMembers] = useState<any[]>([]);
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [role, setRole] = useState('');
    const [notifyInvite, setNotifyInvite] = useState(true);
    const [notifyReport, setNotifyReport] = useState(true);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const fetchMembers = async () => {
        try {
            const res = await client.get(`/sessions/${sessionId}/panel`);
            setMembers(res.data);
        } catch { }
    };

    useEffect(() => { fetchMembers() }, [sessionId]);

    const addMember = async () => {
        if (!name || !email) { setError('Name and email are required'); return; }
        setError('');
        setLoading(true);
        try {
            await client.post(`/sessions/${sessionId}/panel`, {
                name, email, role: role || null,
                notify_invite: notifyInvite, notify_report: notifyReport,
            });
            setName(''); setEmail(''); setRole('');
            await fetchMembers();
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to add member');
        } finally {
            setLoading(false);
        }
    };

    const removeMember = async (memberId: string) => {
        try {
            await client.delete(`/sessions/${sessionId}/panel/${memberId}`);
            await fetchMembers();
        } catch { }
    };

    const panelInputStyle: React.CSSProperties = {
        width: '100%', background: 'var(--bg-surface-high)', border: '1px solid var(--border)',
        borderRadius: 'var(--radius)', padding: '8px 10px', color: 'var(--text-primary)',
        fontSize: '13px', outline: 'none', fontFamily: 'var(--font-body)', boxSizing: 'border-box'
    };

    return (
        <div style={{ marginTop: '24px', padding: '20px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)' }}>
            <h4 style={{ margin: '0 0 16px', fontSize: '14px', fontFamily: 'var(--font-heading)', fontWeight: 600 }}>Panel Members</h4>

            {members.length === 0 ? (
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>No panel members yet.</p>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
                    {members.map(m => (
                        <div key={m.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-surface-high)', borderRadius: 'var(--radius)', fontSize: '13px' }}>
                            <div>
                                <span style={{ fontWeight: 600 }}>{m.name}</span>
                                {m.role && <span style={{ color: 'var(--text-secondary)', marginLeft: '8px' }}>· {m.role}</span>}
                                <span style={{ color: 'var(--text-secondary)', marginLeft: '8px', display: 'block', marginTop: '2px' }}>{m.email}</span>
                            </div>
                            <button
                                onClick={() => removeMember(m.id)}
                                style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '12px' }}
                            >
                                Remove
                            </button>
                        </div>
                    ))}
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '12px', marginBottom: '12px' }}>
                {[
                    { label: 'Name', value: name, setter: setName, placeholder: 'Jane Smith' },
                    { label: 'Email', value: email, setter: setEmail, placeholder: 'jane@company.com' },
                    { label: 'Role', value: role, setter: setRole, placeholder: 'Technical Lead' },
                ].map(({ label, value, setter, placeholder }) => (
                    <div key={label}>
                        <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', color: 'var(--text-secondary)' }}>{label}</label>
                        <input value={value} onChange={e => setter(e.target.value)} placeholder={placeholder} style={panelInputStyle} />
                    </div>
                ))}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px', fontSize: '13px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                    <input type="checkbox" checked={notifyInvite} onChange={e => setNotifyInvite(e.target.checked)} />
                    Send invite email
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                    <input type="checkbox" checked={notifyReport} onChange={e => setNotifyReport(e.target.checked)} />
                    Send report when ready
                </label>
            </div>

            {error && <p style={{ color: 'var(--danger)', fontSize: '13px', marginBottom: '8px' }}>{error}</p>}

            <button onClick={addMember} disabled={loading} style={{ width: '100%', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 'var(--radius)', padding: '10px 16px', fontSize: '13px', fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}>
                {loading ? 'Adding...' : 'Add Panel Member'}
            </button>
        </div>
    );
}
