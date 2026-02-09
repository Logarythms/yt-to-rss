import { useState, useRef, useEffect } from 'react';
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
  const saveInProgressRef = useRef(false);
  const cancelledRef = useRef(false);

  // Edit panel state
  const [expandedEditId, setExpandedEditId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);
  const editPanelRef = useRef(null);

  // Scroll edit panel into view when opened
  useEffect(() => {
    if (expandedEditId && editPanelRef.current) {
      editPanelRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }, [expandedEditId]);

  const handleDateClick = (episode) => {
    cancelledRef.current = false;
    setEditingDateId(episode.id);
    setEditingDateValue(episode.published_at
      ? new Date(episode.published_at).toISOString().split('T')[0] : '');
  };

  const handleDateSave = async (episode) => {
    // Skip if already saving or if edit was cancelled
    if (saveInProgressRef.current || cancelledRef.current) {
      return;
    }
    saveInProgressRef.current = true;
    setSavingDate(episode.id);
    try {
      // Use noon UTC to avoid timezone day-shift issues
      const published_at = editingDateValue
        ? editingDateValue + 'T12:00:00Z' : null;
      await api.updateEpisode(feedId, episode.id, { published_at });
      setEditingDateId(null);
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to update date');
    } finally {
      setSavingDate(null);
      saveInProgressRef.current = false;
    }
  };

  const handleDateKeyDown = (e, episode) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleDateSave(episode);
    } else if (e.key === 'Escape') {
      cancelledRef.current = true;
      setEditingDateId(null);
    }
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

  const toggleEditPanel = (episode) => {
    if (expandedEditId === episode.id) {
      // Close panel
      setExpandedEditId(null);
    } else {
      // Open panel with current values
      setExpandedEditId(episode.id);
      setEditTitle(episode.title || '');
      setEditDescription(episode.description || '');
    }
  };

  const handleSaveEdit = async (episode) => {
    setSavingEdit(true);
    try {
      // Empty string means revert to original, non-empty means update
      // null means no change (but we always send both fields when saving)
      await api.updateEpisode(feedId, episode.id, {
        title: editTitle || '',  // empty string -> revert to original
        description: editDescription || '',  // empty string -> revert to original
      });
      setExpandedEditId(null);
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to update episode');
    } finally {
      setSavingEdit(false);
    }
  };

  const handleEditKeyDown = (e, episode) => {
    if (e.key === 'Escape') {
      setExpandedEditId(null);
    } else if (e.key === 'Enter' && !e.shiftKey) {
      // Allow Shift+Enter for newlines in description
      if (e.target.tagName !== 'TEXTAREA') {
        e.preventDefault();
        handleSaveEdit(episode);
      }
    }
  };

  if (episodes.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-gray-400">
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
    <div className="divide-y divide-gray-200 dark:divide-gray-700">
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
              <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                {episode.title}
              </h4>
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusColors[episode.status]}`}>
                {episode.status}
              </span>
            </div>
            {episode.description && (
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                {episode.description}
              </p>
            )}
            <div className="mt-2 flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              {episode.duration && (
                <span>
                  {Math.floor(episode.duration / 60)}:{String(episode.duration % 60).padStart(2, '0')}
                </span>
              )}
              {episode.file_size && (
                <span>{formatBytes(episode.file_size)}</span>
              )}
              {savingDate === episode.id ? (
                <span className="text-xs text-gray-400">Saving...</span>
              ) : editingDateId === episode.id ? (
                <input
                  type="date"
                  value={editingDateValue}
                  onChange={(e) => setEditingDateValue(e.target.value)}
                  onBlur={() => handleDateSave(episode)}
                  onKeyDown={(e) => handleDateKeyDown(e, episode)}
                  autoFocus
                  className="text-xs border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded px-1 py-0.5 w-32"
                />
              ) : (
                <span
                  onClick={() => handleDateClick(episode)}
                  className="cursor-pointer hover:text-indigo-600 group inline-flex items-center gap-1"
                  title="Click to edit date"
                >
                  {episode.published_at ? formatDate(episode.published_at) : 'No date'}
                  <svg className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                  </svg>
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
              <p className="mt-2 text-sm text-red-600 dark:text-red-400">
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
                onClick={() => toggleEditPanel(episode)}
                className="text-xs text-indigo-600 hover:text-indigo-500"
              >
                {expandedEditId === episode.id ? 'Cancel Edit' : 'Edit'}
              </button>
              <button
                onClick={() => handleDelete(episode.id)}
                disabled={deleting === episode.id}
                className="text-xs text-red-600 hover:text-red-500 disabled:opacity-50"
              >
                {deleting === episode.id ? 'Deleting...' : 'Delete'}
              </button>
            </div>

            {/* Expandable Edit Panel */}
            {expandedEditId === episode.id && (
              <div ref={editPanelRef} className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded border dark:border-gray-700">
                <div className="mb-3">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Title
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, episode)}
                      className="flex-1 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded px-2 py-1"
                      placeholder="Episode title"
                    />
                    <button
                      type="button"
                      onClick={() => setEditTitle('')}
                      className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 px-2"
                      title="Clear to revert to original"
                    >
                      Clear
                    </button>
                  </div>
                  {episode.original_title && editTitle !== episode.original_title && (
                    <p className="mt-1 text-xs text-gray-400">
                      Original: {episode.original_title}
                    </p>
                  )}
                </div>
                <div className="mb-3">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <div className="flex gap-2">
                    <textarea
                      value={editDescription}
                      onChange={(e) => setEditDescription(e.target.value)}
                      onKeyDown={(e) => handleEditKeyDown(e, episode)}
                      rows={4}
                      className="flex-1 text-sm border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded px-2 py-1"
                      placeholder="Episode description"
                    />
                    <button
                      type="button"
                      onClick={() => setEditDescription('')}
                      className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 px-2 self-start"
                      title="Clear to revert to original"
                    >
                      Clear
                    </button>
                  </div>
                  {episode.original_description && editDescription !== episode.original_description && (
                    <p className="mt-1 text-xs text-gray-400 line-clamp-2">
                      Original: {episode.original_description}
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => handleSaveEdit(episode)}
                    disabled={savingEdit}
                    className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-500 disabled:opacity-50"
                  >
                    {savingEdit ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => setExpandedEditId(null)}
                    className="px-3 py-1 text-sm bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
        );
      })}
    </div>
  );
}
