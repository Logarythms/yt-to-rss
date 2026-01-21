import { useState } from 'react';
import { api } from '../api';

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',
  downloading: 'bg-blue-100 text-blue-800',
  ready: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
};

function formatBytes(bytes) {
  if (!bytes) return null;
  const units = ['B', 'KB', 'MB', 'GB'];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function formatDate(dateString) {
  if (!dateString) return null;
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function EpisodeList({ feedId, episodes, onUpdate }) {
  const [deleting, setDeleting] = useState(null);
  const [retrying, setRetrying] = useState(null);
  const [editingDateId, setEditingDateId] = useState(null);
  const [editingDateValue, setEditingDateValue] = useState('');
  const [savingDate, setSavingDate] = useState(null);

  const handleDateClick = (episode) => {
    setEditingDateId(episode.id);
    setEditingDateValue(episode.published_at
      ? new Date(episode.published_at).toISOString().split('T')[0] : '');
  };

  const handleDateSave = async (episode) => {
    setSavingDate(episode.id);
    try {
      const published_at = editingDateValue
        ? new Date(editingDateValue + 'T00:00:00').toISOString() : null;
      await api.updateEpisode(feedId, episode.id, { published_at });
      setEditingDateId(null);
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to update date');
    } finally {
      setSavingDate(null);
    }
  };

  const handleDateKeyDown = (e, episode) => {
    if (e.key === 'Enter') { e.preventDefault(); handleDateSave(episode); }
    else if (e.key === 'Escape') { setEditingDateId(null); }
  };

  const handleDelete = async (episodeId) => {
    if (!confirm('Are you sure you want to delete this episode?')) return;

    setDeleting(episodeId);
    try {
      await api.deleteEpisode(feedId, episodeId);
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to delete episode');
    } finally {
      setDeleting(null);
    }
  };

  const handleRetry = async (episodeId) => {
    setRetrying(episodeId);
    try {
      await api.retryEpisode(feedId, episodeId);
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to retry episode');
    } finally {
      setRetrying(null);
    }
  };

  if (episodes.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No episodes yet. Add some videos to get started.
      </div>
    );
  }

  // Get thumbnail URL - prefer local thumbnail_path, fallback to YouTube thumbnail_url
  const getThumbnailUrl = (episode) => {
    if (episode.thumbnail_path) {
      return `/episode-thumbnail/${episode.id}.jpg`;
    }
    return episode.thumbnail_url;
  };

  // Sort episodes by published_at (newest first), with null dates at the end
  const sortedEpisodes = [...episodes].sort((a, b) => {
    if (!a.published_at && !b.published_at) return 0;
    if (!a.published_at) return 1;
    if (!b.published_at) return -1;
    return new Date(b.published_at) - new Date(a.published_at);
  });

  return (
    <div className="divide-y divide-gray-200">
      {sortedEpisodes.map((episode) => {
        const thumbnailUrl = getThumbnailUrl(episode);
        const isUploaded = episode.source_type === 'upload';

        return (
        <div key={episode.id} className="py-4 flex items-start gap-4">
          {thumbnailUrl && (
            <img
              src={thumbnailUrl}
              alt=""
              className="w-32 h-20 object-cover rounded flex-shrink-0"
            />
          )}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h4 className="text-sm font-medium text-gray-900 truncate">
                {episode.title}
              </h4>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[episode.status]}`}>
                {episode.status}
              </span>
            </div>
            {episode.description && (
              <p className="mt-1 text-sm text-gray-500 line-clamp-2">
                {episode.description}
              </p>
            )}
            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
              {episode.duration && (
                <span>
                  {Math.floor(episode.duration / 60)}:{String(episode.duration % 60).padStart(2, '0')}
                </span>
              )}
              {episode.file_size && (
                <span>{formatBytes(episode.file_size)}</span>
              )}
              {editingDateId === episode.id ? (
                <input
                  type="date"
                  value={editingDateValue}
                  onChange={(e) => setEditingDateValue(e.target.value)}
                  onBlur={() => handleDateSave(episode)}
                  onKeyDown={(e) => handleDateKeyDown(e, episode)}
                  disabled={savingDate === episode.id}
                  autoFocus
                  className="text-xs border border-gray-300 rounded px-1 py-0.5 w-32"
                />
              ) : (
                <span
                  onClick={() => handleDateClick(episode)}
                  className="cursor-pointer hover:text-indigo-600 hover:underline"
                  title="Click to edit date"
                >
                  {episode.published_at ? formatDate(episode.published_at) : 'No date'}
                </span>
              )}
              {isUploaded ? (
                <span className="text-purple-600 font-medium">Uploaded</span>
              ) : episode.youtube_id ? (
                <a
                  href={`https://www.youtube.com/watch?v=${episode.youtube_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-600 hover:text-indigo-500"
                >
                  YouTube
                </a>
              ) : null}
            </div>
            {episode.error_message && (
              <p className="mt-2 text-sm text-red-600">
                Error: {episode.error_message}
              </p>
            )}
            <div className="mt-2 flex gap-2">
              {episode.status === 'failed' && (
                <button
                  onClick={() => handleRetry(episode.id)}
                  disabled={retrying === episode.id}
                  className="text-xs text-indigo-600 hover:text-indigo-500 disabled:opacity-50"
                >
                  {retrying === episode.id ? 'Retrying...' : 'Retry'}
                </button>
              )}
              <button
                onClick={() => handleDelete(episode.id)}
                disabled={deleting === episode.id}
                className="text-xs text-red-600 hover:text-red-500 disabled:opacity-50"
              >
                {deleting === episode.id ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
        );
      })}
    </div>
  );
}
