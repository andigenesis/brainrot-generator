# Brainrot Generator - Frontend

React + TypeScript + Vite frontend for the Brainrot Video Generator.

## Features

- 📝 Text input for pasting content
- 📁 File upload for PDF, TXT, and audio files
- ⚙️ Real-time job progress tracking with polling
- 🎥 Video player with download functionality
- 🌙 Modern dark-themed UI with Tailwind CSS
- 🎨 Gradient accents and smooth animations

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **@tailwindcss/forms** - Form styling

## Getting Started

### Prerequisites

- Node.js 18+ or npm/yarn/pnpm
- Backend server running on http://localhost:8000

### Installation

```bash
# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend will be available at http://localhost:5173

### Build for Production

```bash
npm run build
npm run preview
```

## Project Structure

```
src/
├── components/
│   ├── TextInput.tsx      # Text input with generate button
│   ├── FileUpload.tsx     # Drag-and-drop file upload
│   ├── JobProgress.tsx    # Progress bar with polling
│   └── VideoPlayer.tsx    # Video playback and download
├── api.ts                 # API client functions
├── App.tsx                # Main app component
├── main.tsx               # Entry point
└── index.css              # Tailwind directives
```

## API Integration

The frontend proxies all `/api` requests to the backend server (configured in `vite.config.ts`).

### Endpoints Used

- `POST /api/generate` - Submit text or file for video generation
- `GET /api/jobs/{job_id}` - Poll job status (every 2 seconds)
- `GET /api/videos/{video_id}` - Download generated video

## User Flow

1. User selects input mode (text or file)
2. User enters text or uploads PDF/TXT/audio file
3. User clicks "Generate Video"
4. Frontend polls job status every 2 seconds
5. Progress bar updates in real-time
6. When complete, video player appears
7. User can watch/download video or generate another

## Development

```bash
# Run dev server with hot reload
npm run dev

# Type check
npm run build

# Lint
npm run lint
```
