import { API_URL } from './config';

/** Fetches job data by job ID */
export async function getJob(jobId: string) {
    const res = await fetch(`${API_URL}/api/v1/jobs?job_id=${jobId}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
    });
    
    if (!res.ok) {
        throw new Error(`Failed to fetch job with status ${res.status}`);
    }
    
    const data = await res.json();
    console.log('Job fetch response:', data);
    return data.data;
}

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