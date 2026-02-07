import { useState, useRef } from 'react';

interface FileUploadProps {
  onSubmit: (file: File) => void;
  disabled?: boolean;
}

export default function FileUpload({ onSubmit, disabled }: FileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (file: File) => {
    const validTypes = [
      'application/pdf',
      'text/plain',
      'audio/mpeg',
      'audio/wav',
      'audio/mp4',
      'audio/x-m4a',
    ];

    if (validTypes.includes(file.type) || file.name.match(/\.(pdf|txt|mp3|wav|m4a)$/i)) {
      setSelectedFile(file);
    } else {
      alert('Please upload a PDF, TXT, or audio file (MP3, WAV, M4A)');
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleSubmit = () => {
    if (selectedFile) {
      onSubmit(selectedFile);
    }
  };

  return (
    <div className="w-full">
      <label className="block text-sm font-medium text-gray-300 mb-2">
        Upload File or Audio
      </label>
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200 ${
          isDragging
            ? 'border-purple-500 bg-purple-500/10'
            : 'border-gray-700 bg-gray-800/50 hover:border-gray-600'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          accept=".pdf,.txt,.mp3,.wav,.m4a,audio/*,application/pdf,text/plain"
          onChange={handleFileInputChange}
          disabled={disabled}
        />

        <svg
          className="mx-auto h-12 w-12 text-gray-500 mb-4"
          stroke="currentColor"
          fill="none"
          viewBox="0 0 48 48"
          aria-hidden="true"
        >
          <path
            d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>

        <p className="text-gray-400 mb-2">
          {selectedFile ? (
            <span className="text-purple-400 font-medium">{selectedFile.name}</span>
          ) : (
            <>
              <span className="text-purple-400 font-medium">Click to upload</span> or drag and drop
            </>
          )}
        </p>
        <p className="text-sm text-gray-500">
          PDF, TXT, or audio files (MP3, WAV, M4A)
        </p>
      </div>

      {selectedFile && (
        <button
          onClick={handleSubmit}
          disabled={disabled}
          className="mt-4 w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
        >
          Generate Video
        </button>
      )}
    </div>
  );
}
