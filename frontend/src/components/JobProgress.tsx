import { useEffect, useState } from 'react';
import { getJobStatus, JobStatus } from '../api';

interface JobProgressProps {
  jobId: string;
  onComplete: (videoUrl: string) => void;
}

export default function JobProgress({ jobId, onComplete }: JobProgressProps) {
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let intervalId: number;

    const pollStatus = async () => {
      try {
        const jobStatus = await getJobStatus(jobId);
        setStatus(jobStatus);

        if (jobStatus.status === 'complete' && jobStatus.video_url) {
          clearInterval(intervalId);
          onComplete(jobStatus.video_url);
        } else if (jobStatus.status === 'error') {
          clearInterval(intervalId);
          setError(jobStatus.error || 'Unknown error occurred');
        }
      } catch (err) {
        console.error('Error polling job status:', err);
        setError(err instanceof Error ? err.message : 'Failed to get job status');
        clearInterval(intervalId);
      }
    };

    // Poll immediately, then every 2 seconds
    pollStatus();
    intervalId = window.setInterval(pollStatus, 2000);

    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [jobId, onComplete]);

  if (error) {
    return (
      <div className="w-full max-w-2xl mx-auto p-6 bg-red-900/20 border border-red-700 rounded-lg">
        <div className="flex items-start">
          <svg
            className="h-6 w-6 text-red-400 mr-3 flex-shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <h3 className="text-lg font-semibold text-red-400 mb-1">Error</h3>
            <p className="text-red-300">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  if (!status) {
    return (
      <div className="w-full max-w-2xl mx-auto p-6 bg-gray-800 rounded-lg">
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-4 bg-gray-700 rounded w-3/4"></div>
            <div className="h-4 bg-gray-700 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  const statusEmoji = {
    queued: '⏳',
    processing: '⚙️',
    complete: '✅',
    error: '❌',
  };

  const statusText = {
    queued: 'Queued',
    processing: 'Processing',
    complete: 'Complete',
    error: 'Error',
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6 bg-gray-800 rounded-lg border border-gray-700">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-gray-100">
            {statusEmoji[status.status]} {statusText[status.status]}
          </h3>
          <span className="text-sm text-gray-400">{status.progress}%</span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-2.5 overflow-hidden">
          <div
            className="bg-gradient-to-r from-purple-600 to-pink-600 h-2.5 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${status.progress}%` }}
          />
        </div>
      </div>

      {status.status === 'processing' && (
        <div className="flex items-center text-sm text-gray-400">
          <svg
            className="animate-spin h-4 w-4 mr-2 text-purple-500"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          Generating your brainrot video...
        </div>
      )}
    </div>
  );
}
