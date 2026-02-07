import { useState } from 'react';

interface TextInputProps {
  onSubmit: (text: string) => void;
  disabled?: boolean;
}

export default function TextInput({ onSubmit, disabled }: TextInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = () => {
    if (text.trim()) {
      onSubmit(text);
    }
  };

  return (
    <div className="w-full">
      <label htmlFor="text-input" className="block text-sm font-medium text-gray-300 mb-2">
        Paste Your Text
      </label>
      <textarea
        id="text-input"
        className="w-full h-48 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
        placeholder="Paste your text here... It can be a story, article, Reddit post, or anything you want to turn into a brainrot video."
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
      />
      <button
        onClick={handleSubmit}
        disabled={disabled || !text.trim()}
        className="mt-4 w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-lg hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
      >
        Generate Video
      </button>
    </div>
  );
}
