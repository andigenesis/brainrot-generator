interface VideoPlayerProps {
  videoUrl: string;
  onReset: () => void;
}

export default function VideoPlayer({ videoUrl, onReset }: VideoPlayerProps) {
  const handleDownload = () => {
    // Create a temporary link and trigger download
    const link = document.createElement('a');
    link.href = videoUrl;
    link.download = `brainrot-${Date.now()}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
        <div className="aspect-[9/16] bg-black flex items-center justify-center">
          <video
            src={videoUrl}
            controls
            className="w-full h-full"
            preload="metadata"
          >
            Your browser does not support the video tag.
          </video>
        </div>

        <div className="p-6 space-y-3">
          <button
            onClick={handleDownload}
            className="w-full px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white font-semibold rounded-lg hover:from-green-700 hover:to-emerald-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 focus:ring-offset-gray-900 transition-all duration-200 flex items-center justify-center"
          >
            <svg
              className="w-5 h-5 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Download Video
          </button>

          <button
            onClick={onReset}
            className="w-full px-6 py-3 bg-gray-700 text-gray-100 font-semibold rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 focus:ring-offset-gray-900 transition-all duration-200"
          >
            Generate Another Video
          </button>
        </div>
      </div>
    </div>
  );
}
