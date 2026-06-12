import React, { useState, useRef, useEffect } from 'react';
import client from '../api/client';

export default function ReportChat({ sessionId }: { sessionId: string }) {
    const [messages, setMessages] = useState<{ role: 'user' | 'assistant', text: string, evidence?: any[] }[]>([
        { role: 'assistant', text: 'Hi! I am your AI assistant. Ask me any questions about the metrics or the interview.' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const endRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!input.trim() || loading) return;

        const question = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', text: question }]);
        setLoading(true);

        try {
            const res = await client.post(`/analysis/${sessionId}/explain`, { question });
            setMessages(prev => [...prev, { 
                role: 'assistant', 
                text: res.data.answer,
                evidence: res.data.evidence 
            }]);
        } catch (err) {
            console.error('Explanation failed', err);
            setMessages(prev => [...prev, { role: 'assistant', text: 'Sorry, I encountered an error while trying to answer that.' }]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '400px', border: '1px solid var(--border)', borderRadius: '6px', overflow: 'hidden' }}>
            {/* Chat Area */}
            <div style={{ flex: 1, padding: '16px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '12px', background: 'var(--bg)' }}>
                {messages.map((m, i) => (
                    <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                        <div style={{
                            background: m.role === 'user' ? 'var(--accent)' : 'var(--bg-surface)',
                            color: m.role === 'user' ? '#fff' : 'var(--text-primary)',
                            padding: '10px 14px',
                            borderRadius: '12px',
                            borderBottomRightRadius: m.role === 'user' ? '2px' : '12px',
                            borderBottomLeftRadius: m.role === 'assistant' ? '2px' : '12px',
                            maxWidth: '80%',
                            fontSize: '13px',
                            lineHeight: 1.5,
                            border: m.role === 'assistant' ? '1px solid var(--border)' : 'none',
                        }}>
                            {m.text}
                        </div>
                        {m.role === 'assistant' && m.evidence && m.evidence.length > 0 && (
                            <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '4px', maxWidth: '80%' }}>
                                <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 600 }}>Evidence:</div>
                                {m.evidence.map((ev, idx) => (
                                    <div key={idx} style={{
                                        fontSize: '11px',
                                        color: 'var(--text-secondary)',
                                        background: 'var(--bg-surface)',
                                        padding: '6px 8px',
                                        borderRadius: '4px',
                                        borderLeft: '2px solid var(--accent)',
                                    }}>
                                        "{ev.quote}"
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
                {loading && (
                    <div style={{ alignSelf: 'flex-start', fontSize: '12px', color: 'var(--text-secondary)' }}>
                        Thinking...
                    </div>
                )}
                <div ref={endRef} />
            </div>

            {/* Input Area */}
            <form onSubmit={handleSend} style={{ display: 'flex', borderTop: '1px solid var(--border)', background: 'var(--bg-surface)' }}>
                <input
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    placeholder="Ask a question about the report..."
                    style={{ flex: 1, padding: '12px 16px', border: 'none', background: 'transparent', color: 'var(--text-primary)', outline: 'none', fontSize: '13px' }}
                />
                <button 
                    type="submit" 
                    disabled={loading || !input.trim()}
                    style={{ 
                        padding: '0 20px', background: 'var(--accent)', color: '#fff', border: 'none', 
                        cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                        opacity: loading || !input.trim() ? 0.6 : 1,
                        fontWeight: 600, fontSize: '13px'
                    }}
                >
                    Send
                </button>
            </form>
        </div>
    );
}
