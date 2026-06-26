import { useState, useEffect, useCallback } from 'react';
import client from '../api/client';

export interface RuntimeDetails {
    progress: number;
    current_step: string;
    failed_component: string | null;
    duration_ms: number | null;
}

export function useRuntimeStatus(sessionId: string | undefined, shouldPoll: boolean = true) {
    const [aiRuntime, setAiRuntime] = useState<string>('not_initialized');
    const [aiRuntimeDetails, setAiRuntimeDetails] = useState<RuntimeDetails>({
        progress: 0,
        current_step: '',
        failed_component: null,
        duration_ms: null
    });

    const pollRuntime = useCallback(async () => {
        if (!sessionId) return;
        try {
            const res = await client.get(`/sessions/${sessionId}/runtime-status`);
            setAiRuntime(res.data.runtime);
            setAiRuntimeDetails({
                progress: res.data.progress,
                current_step: res.data.current_step,
                failed_component: res.data.failed_component,
                duration_ms: res.data.duration_ms
            });
        } catch (e) {
            console.error('Failed to fetch runtime status', e);
        }
    }, [sessionId]);

    useEffect(() => {
        if (!shouldPoll || !sessionId) return;
        
        pollRuntime();
        const interval = setInterval(pollRuntime, 3000);
        return () => clearInterval(interval);
    }, [shouldPoll, sessionId, pollRuntime]);

    const retryInitialization = async () => {
        if (!sessionId) return;
        try {
            await client.post(`/sessions/${sessionId}/initialize-ai`);
            pollRuntime();
        } catch (e) {
            console.error('Failed to retry initialization', e);
        }
    };

    return { aiRuntime, aiRuntimeDetails, retryInitialization };
}
