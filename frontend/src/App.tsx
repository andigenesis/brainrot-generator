import { useState } from 'react';
import TextInput from './components/TextInput';
import FileUpload from './components/FileUpload';
import JobProgress from './components/JobProgress';
import VideoPlayer from './components/VideoPlayer';
import { submitText, submitFile } from './api';

type AppState =
  | { stage: 'input' }
  | { stage: 'processing'; jobId: string }
  | { stage: 'complete'; videoUrl: string };

function App() {
  const [state, setState] = useState<AppState>({ stage: 'input' });
  const [inputMode, setInputMode] = useState<'text' | 'file'>('text');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleTextSubmit = async (text: string) => {
    setIsSubmitting(true);
    try {
      const response = await submitText(text);
      setState({ stage: 'processing', jobId: response.job_id });
    } catch (error) {
      console.error('Error submitting text:', error);
      alert('Failed to submit text. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileSubmit = async (file: File) => {
    setIsSubmitting(true);
    try {
      const response = await submitFile(file);
      setState({ stage: 'processing', jobId: response.job_id });
    } catch (error) {
      console.error('Error submitting file:', error);
      alert('Failed to submit file. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleJobComplete = (videoUrl: string) => {
    setState({ stage: 'complete', videoUrl });
  };

  const handleReset = () => {
    setState({ stage: 'input' });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-center">
            <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-400 via-pink-400 to-purple-400 bg-clip-text text-transparent">
              🧠 Brainrot Generator
            </h1>
          </div>
          <p className="text-center text-gray-400 mt-2">
            Turn your text into TikTok-style brainrot videos
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {state.stage === 'input' && (
          <div className="max-w-2xl mx-auto">
            {/* Input Mode Tabs */}
            <div className="flex gap-2 mb-8 bg-gray-800 p-1 rounded-lg">
              <button
                onClick={() => setInputMode('text')}
                className={`flex-1 py-3 px-4 rounded-md font-medium transition-all duration-200 ${
                  inputMode === 'text'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                📝 Text Input
              </button>
              <button
                onClick={() => setInputMode('file')}
                className={`flex-1 py-3 px-4 rounded-md font-medium transition-all duration-200 ${
                  inputMode === 'file'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-lg'
                    : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                📁 File Upload
              </button>
            </div>

            {/* Input Components */}
            <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-8 shadow-2xl border border-gray-700">
              {inputMode === 'text' ? (
                <TextInput onSubmit={handleTextSubmit} disabled={isSubmitting} />
              ) : (
                <FileUpload onSubmit={handleFileSubmit} disabled={isSubmitting} />
              )}
            </div>

            {/* Info Section */}
            <div className="mt-8 bg-gray-800/30 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
              <h2 className="text-lg font-semibold text-gray-200 mb-3">How it works</h2>
              <ul className="space-y-2 text-gray-400 text-sm">
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">1.</span>
                  <span>Paste text or upload a PDF/TXT/audio file</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">2.</span>
                  <span>AI converts your content into engaging narration</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">3.</span>
                  <span>Video is generated with gameplay background and captions</span>
                </li>
                <li className="flex items-start">
                  <span className="text-purple-400 mr-2">4.</span>
                  <span>Download your vertical (9:16) brainrot video</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        {state.stage === 'processing' && (
          <JobProgress jobId={state.jobId} onComplete={handleJobComplete} />
        )}

        {state.stage === 'complete' && (
          <VideoPlayer videoUrl={state.videoUrl} onReset={handleReset} />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 mt-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-gray-500 text-sm">
            Made with 🧠 and ✨ by AndI
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
