import { ImprovedResult } from '@/components/common/resume_previewer_context';
import { API_URL } from './config';

/** Uploads job descriptions and returns a job_id */
export async function uploadJobDescriptions(
    descriptions: string[],
    resumeId: string
): Promise<string> {
    const res = await fetch(`${API_URL}/api/v1/jobs/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_descriptions: descriptions, resume_id: resumeId }),
    });
    if (!res.ok) throw new Error(`Upload failed with status ${res.status}`);
    const data = await res.json();
    console.log('Job upload response:', data);
    return data.job_id[0];
}

/**
 * Streaming variant of /improve. Calls `onProgress` for each status event the
 * server emits, and resolves with the same `ImprovedResult` shape as the
 * non-streaming version. The final result is emitted with `status: "completed"`.
 *
 * Falls back to plain non-streaming fetch if `text/event-stream` is unavailable
 * (e.g. some dev proxies buffer the response).
 */
export async function improveResumeStream(
    resumeId: string,
    jobId: string,
    onProgress?: (status: string, message: string) => void
): Promise<ImprovedResult> {
    const res = await fetch(
        `${API_URL}/api/v1/resumes/improve?stream=true`,
        {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
            body: JSON.stringify({ resume_id: resumeId, job_id: jobId }),
        }
    );

    if (!res.ok) {
        const text = await res.text();
        throw new Error(`Improve failed with status ${res.status}: ${text}`);
    }

    if (!res.body) {
        throw new Error('Streaming response has no body');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let finalResult: ImprovedResult | null = null;

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE messages are separated by \n\n
        let sep: number;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, sep);
            buffer = buffer.slice(sep + 2);
            const dataLine = rawEvent
                .split('\n')
                .filter((l) => l.startsWith('data:'))
                .map((l) => l.slice(5).trim())
                .join('');
            if (!dataLine) continue;
            let payload: { status: string; message?: string; result?: ImprovedResult } | null = null;
            try {
                payload = JSON.parse(dataLine);
            } catch {
                console.warn('Failed to parse SSE event:', dataLine);
                continue;
            }
            if (!payload) continue;
            if (payload.status === 'completed' && payload.result) {
                finalResult = payload.result;
            } else if (payload.status === 'error') {
                throw new Error(payload.message || 'Unknown streaming error');
            } else if (onProgress) {
                onProgress(payload.status, payload.message ?? '');
            }
        }
    }

    if (!finalResult) {
        throw new Error('Stream ended without a completed result');
    }
    return finalResult;
}

/** Improves the resume and returns the full preview object (non-streaming). */
export async function improveResume(
    resumeId: string,
    jobId: string
): Promise<ImprovedResult> {
    let response: Response;
    try {
        response = await fetch(`${API_URL}/api/v1/resumes/improve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resume_id: resumeId, job_id: jobId }),
        });
    } catch (networkError) {
        console.error('Network error during improveResume:', networkError);
        throw networkError;
    }

    const text = await response.text();
    if (!response.ok) {
        console.error('Improve failed response body:', text);
        throw new Error(`Improve failed with status ${response.status}: ${text}`);
    }

    let data: ImprovedResult;
    try {
        data = JSON.parse(text) as ImprovedResult;
    } catch (parseError) {
        console.error('Failed to parse improveResume response:', parseError, 'Raw response:', text);
        throw parseError;
    }

    console.log('Resume improvement response:', data);
    return data;
}
