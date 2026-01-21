import { useState, useRef } from 'react';
import { api } from '../api';

const ALLOWED_AUDIO_TYPES = ['.mp3', '.m4a', '.wav', '.flac', '.ogg'];
const ALLOWED_IMAGE_TYPES = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500MB

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

export default function UploadAudioModal({ feedId, onClose, onUploaded }) {
  const [audioFile, setAudioFile] = useState(null);
  const [thumbnailFile, setThumbnailFile] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const audioInputRef = useRef(null);
  const thumbnailInputRef = useRef(null);

  const handleAudioChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_AUDIO_TYPES.includes(ext)) {
      setError(`Invalid audio format. Allowed: ${ALLOWED_AUDIO_TYPES.join(', ')}`);
      return;
    }

    // Check MIME type if available (additional client-side validation)
    if (file.type && !file.type.startsWith('audio/')) {
      setError(`File does not appear to be an audio file. MIME type: ${file.type}`);
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setError(`File too large. Maximum size: ${formatBytes(MAX_FILE_SIZE)}`);
      return;
    }

    setAudioFile(file);
    setError('');

    // Default title to filename without extension
    if (!title) {
      setTitle(file.name.replace(/\.[^/.]+$/, ''));
    }
  };

  const handleThumbnailChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!ALLOWED_IMAGE_TYPES.includes(ext)) {
      setError(`Invalid image format. Allowed: ${ALLOWED_IMAGE_TYPES.join(', ')}`);
      return;
    }

    setThumbnailFile(file);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!audioFile) {
      setError('Please select an audio file');
      return;
    }

    setLoading(true);
    setError('');
    setProgress(0);

    try {
      const result = await api.uploadAudio(
        feedId,
        audioFile,
        thumbnailFile,
        title || null,
        description || null,
        setProgress
      );
      onUploaded(result);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to upload audio');
      setLoading(false);
      setProgress(0);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">Upload Audio</h3>
          <button
            onClick={onClose}
            disabled={loading}
            className="text-gray-400 hover:text-gray-500 disabled:opacity-50"
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {error && (
            <div className="mb-4 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded-md text-sm">
              {error}
            </div>
          )}

          {/* Audio File */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Audio File *
            </label>
            <input
              ref={audioInputRef}
              type="file"
              accept={ALLOWED_AUDIO_TYPES.join(',')}
              onChange={handleAudioChange}
              className="hidden"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => audioInputRef.current?.click()}
                disabled={loading}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Choose File
              </button>
              {audioFile && (
                <span className="text-sm text-gray-600 truncate flex-1">
                  {audioFile.name} ({formatBytes(audioFile.size)})
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-gray-500">
              Supported: {ALLOWED_AUDIO_TYPES.join(', ')} (max {formatBytes(MAX_FILE_SIZE)})
            </p>
          </div>

          {/* Title */}
          <div className="mb-4">
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Title
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={loading}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2 border text-sm disabled:opacity-50"
              placeholder="Episode title (defaults to filename)"
            />
          </div>

          {/* Description */}
          <div className="mb-4">
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <textarea
              id="description"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={loading}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 px-3 py-2 border text-sm disabled:opacity-50"
              placeholder="Optional description"
            />
          </div>

          {/* Thumbnail */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Thumbnail (optional)
            </label>
            <input
              ref={thumbnailInputRef}
              type="file"
              accept={ALLOWED_IMAGE_TYPES.join(',')}
              onChange={handleThumbnailChange}
              className="hidden"
            />
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => thumbnailInputRef.current?.click()}
                disabled={loading}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              >
                Choose Image
              </button>
              {thumbnailFile && (
                <span className="text-sm text-gray-600 truncate flex-1">
                  {thumbnailFile.name}
                </span>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          {loading && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600">Uploading...</span>
                <span className="text-sm text-gray-600">{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-500 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !audioFile}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {loading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
