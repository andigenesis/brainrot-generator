import { useState, useRef, useCallback, useEffect } from 'react';

interface VoiceInputProps {
  onSubmit: (text: string) => void;
  onSubmitAudio: (audio: Blob) => void;
  disabled?: boolean;
}

type RecordingState = 'idle' | 'recording' | 'transcribing';

// Check if Web Speech API is available
const SpeechRecognition =
  (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

export default function VoiceInput({ onSubmit, onSubmitAudio, disabled }: VoiceInputProps) {
  const [recordingState, setRecordingState] = useState<RecordingState>('idle');
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [duration, setDuration] = useState(0);
  const [useServerTranscription, setUseServerTranscription] = useState(!SpeechRecognition);

  const recognitionRef = useRef<any>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopRecording();
    };
  }, []);

  const startTimer = useCallback(() => {
    setDuration(0);
    timerRef.current = window.setInterval(() => {
      setDuration((d) => d + 1);
    }, 1000);
  }, []);

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const formatDuration = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Always record audio (for server-side fallback or direct upload)
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
          ? 'audio/webm;codecs=opus'
          : 'audio/webm',
      });
      audioChunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250); // Collect chunks every 250ms

      // Use Web Speech API for live transcription if available and not in server mode
      if (SpeechRecognition && !useServerTranscription) {
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = 'en-US';

        recognition.onresult = (event: any) => {
          let final = '';
          let interim = '';
          for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript + ' ';
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          setTranscript(final.trim());
          setInterimTranscript(interim);
        };

        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          // Fall back to server transcription on error
          if (event.error === 'not-allowed' || event.error === 'service-not-available') {
            setUseServerTranscription(true);
          }
        };

        recognition.start();
        recognitionRef.current = recognition;
      }

      setRecordingState('recording');
      startTimer();
    } catch (err) {
      console.error('Failed to start recording:', err);
      alert('Microphone access is required for voice input. Please allow microphone access and try again.');
    }
  };

  const stopRecording = useCallback(() => {
    stopTimer();

    // Stop speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    // Stop media recorder
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }

    // Stop audio stream tracks
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    setRecordingState('idle');
    setInterimTranscript('');
  }, [stopTimer]);

  const handleSubmitText = () => {
    const finalText = transcript.trim();
    if (finalText) {
      onSubmit(finalText);
      setTranscript('');
    }
  };

  const handleSubmitAudio = () => {
    if (audioChunksRef.current.length > 0) {
      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
      onSubmitAudio(audioBlob);
      setTranscript('');
      audioChunksRef.current = [];
    }
  };

  const handleStop = () => {
    stopRecording();
  };

  const displayText = transcript + (interimTranscript ? ' ' + interimTranscript : '');
  const hasTranscript = transcript.trim().length > 0;
  const hasAudio = audioChunksRef.current.length > 0;

  return (
    <div className="w-full">
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Speak Your Content
      </label>

      {/* Recording area */}
      <div className="relative bg-gray-800 border border-gray-700 rounded-lg overflow-hidden">
        {/* Transcript display */}
        <div className="min-h-[12rem] max-h-[20rem] overflow-y-auto p-4">
          {displayText ? (
            <p className="text-gray-100 leading-relaxed">
              {transcript}
              {interimTranscript && (
                <span className="text-gray-500 italic">{' ' + interimTranscript}</span>
              )}
            </p>
          ) : (
            <p className="text-gray-500 italic">
              {recordingState === 'recording'
                ? useServerTranscription
                  ? 'Recording audio... Speak now.'
                  : 'Listening... Start speaking.'
                : 'Click the microphone to start recording. Your speech will be transcribed in real-time.'}
            </p>
          )}
        </div>

        {/* Recording controls bar */}
        <div className="flex items-center justify-between border-t border-gray-700 px-4 py-3 bg-gray-800/80">
          {/* Duration */}
          <div className="text-sm text-gray-400 w-16">
            {recordingState === 'recording' && (
              <span className="tabular-nums">{formatDuration(duration)}</span>
            )}
          </div>

          {/* Mic button */}
          <button
            onClick={recordingState === 'recording' ? handleStop : startRecording}
            disabled={disabled}
            className={`relative w-16 h-16 rounded-full flex items-center justify-center transition-all duration-300 ${
              recordingState === 'recording'
                ? 'bg-red-600 hover:bg-red-700 shadow-lg shadow-red-600/30'
                : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 shadow-lg shadow-purple-600/20'
            } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {recordingState === 'recording' ? (
              // Stop icon (square)
              <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="6" width="12" height="12" rx="2" />
              </svg>
            ) : (
              // Microphone icon
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4M12 15a3 3 0 003-3V5a3 3 0 00-6 0v7a3 3 0 003 3z"
                />
              </svg>
            )}

            {/* Pulsing ring when recording */}
            {recordingState === 'recording' && (
              <span className="absolute inset-0 rounded-full animate-ping bg-red-600 opacity-20" />
            )}
          </button>

          {/* Recording indicator */}
          <div className="w-16 flex justify-end">
            {recordingState === 'recording' && (
              <span className="flex items-center text-sm text-red-400">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse mr-1.5" />
                REC
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Server transcription toggle */}
      {SpeechRecognition && (
        <div className="mt-3 flex items-center">
          <label className="flex items-center text-sm text-gray-500 cursor-pointer">
            <input
              type="checkbox"
              checked={useServerTranscription}
              onChange={(e) => setUseServerTranscription(e.target.checked)}
              disabled={recordingState === 'recording'}
              className="mr-2 rounded border-gray-600 bg-gray-700 text-purple-500 focus:ring-purple-500 focus:ring-offset-gray-900"
            />
            Use server-side transcription (Whisper — better accuracy for technical content)
          </label>
        </div>
      )}

      {/* Submit buttons */}
      {recordingState === 'idle' && (hasTranscript || hasAudio) && (
        <div className="mt-4 space-y-2">
          {hasTranscript && !useServerTranscription && (
            <button
              onClick={handleSubmitText}
              disabled={disabled}
              className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              Generate Video from Transcript
            </button>
          )}
          {(useServerTranscription || !hasTranscript) && hasAudio && (
            <button
              onClick={handleSubmitAudio}
              disabled={disabled}
              className="w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              Generate Video (Server Transcription)
            </button>
          )}
        </div>
      )}
    </div>
  );
}
