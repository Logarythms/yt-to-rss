import { useState } from 'react';
import { api } from '../api';

function formatInterval(seconds) {
  if (!seconds) return 'Default';
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  return `${Math.round(seconds / 3600)} hr`;
}

function formatDate(dateString) {
  if (!dateString) return 'Never';
  return new Date(dateString).toLocaleString();
}

export default function PlaylistSources({ feedId, sources, onUpdate }) {
  const [removing, setRemoving] = useState(null);
  const [toggling, setToggling] = useState(null);

  const handleRemove = async (sourceId) => {
    if (!confirm('Stop tracking this playlist? Existing episodes will be kept.')) return;
    setRemoving(sourceId);
    try {
      await api.removePlaylistSource(feedId, sourceId);
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to remove playlist');
    } finally {
      setRemoving(null);
    }
  };

  const handleToggle = async (source) => {
    setToggling(source.id);
    try {
      await api.updatePlaylistSource(feedId, source.id, {
        enabled: !source.enabled,
      });
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to update playlist');
    } finally {
      setToggling(null);
    }
  };

  if (!sources || sources.length === 0) return null;

  return (
    <div className="divide-y divide-gray-200">
      {sources.map((source) => (
        <div key={source.id} className="py-3 flex items-center justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-gray-900 truncate">
              {source.name || source.playlist_id}
            </p>
            <p className="text-xs text-gray-500">
              Last refreshed: {formatDate(source.last_refreshed_at)}
              {' | '}
              Interval: {formatInterval(source.refresh_interval_override)}
            </p>
          </div>
          <div className="flex items-center gap-2 ml-4">
            <button
              onClick={() => handleToggle(source)}
              disabled={toggling === source.id}
              className={`text-xs px-2 py-1 rounded ${
                source.enabled
                  ? 'bg-green-100 text-green-800'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {source.enabled ? 'Enabled' : 'Disabled'}
            </button>
            <button
              onClick={() => handleRemove(source.id)}
              disabled={removing === source.id}
              className="text-xs text-red-600 hover:text-red-500 disabled:opacity-50"
            >
              {removing === source.id ? 'Removing...' : 'Remove'}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
