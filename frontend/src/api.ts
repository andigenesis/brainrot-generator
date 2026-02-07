// API client for brainrot generator backend

export interface JobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'complete' | 'error';
  progress: number;
  video_url?: string;
  error?: string;
}

export interface GenerateResponse {
  job_id: string;
  status: string;
}

const API_BASE = '/api';

export async function submitText(text: string): Promise<GenerateResponse> {
  const formData = new FormData();
  formData.append('text', text);

  const response = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to submit text: ${response.statusText}`);
  }

  return response.json();
}

export async function submitFile(file: File): Promise<GenerateResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to submit file: ${response.statusText}`);
  }

  return response.json();
}

export async function submitAudio(audioBlob: Blob): Promise<GenerateResponse> {
  const formData = new FormData();
  formData.append('file', audioBlob, 'recording.webm');

  const response = await fetch(`${API_BASE}/generate`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Failed to submit audio: ${response.statusText}`);
  }

  return response.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);

  if (!response.ok) {
    throw new Error(`Failed to get job status: ${response.statusText}`);
  }

  return response.json();
}

export function getVideoUrl(videoId: string): string {
  return `${API_BASE}/videos/${videoId}`;
}
