import { useState } from 'react';
import { api } from '../api';

const INTERVAL_OPTIONS = [
  { value: '', label: 'Default' },
  { value: '1800', label: '30 min' },
  { value: '3600', label: '1 hr' },
  { value: '7200', label: '2 hr' },
  { value: '21600', label: '6 hr' },
  { value: '43200', label: '12 hr' },
  { value: '86400', label: '24 hr' },
];

function formatInterval(seconds) {
  if (!seconds) return 'Default';
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  return `${Math.round(seconds / 3600)} hr`;
}

function formatDate(dateString) {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 0 || diffMs >= 86400000) {
    return date.toLocaleString();
  }
  if (diffSec < 60) return 'just now';
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} min ago`;
  const diffHr = Math.floor(diffMin / 60);
  return `${diffHr} hr ago`;
}

export default function PlaylistSources({ feedId, sources, onUpdate }) {
  const [removing, setRemoving] = useState(null);
  const [toggling, setToggling] = useState(null);
  const [updatingInterval, setUpdatingInterval] = useState(null);

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

  const handleIntervalChange = async (source, value) => {
    setUpdatingInterval(source.id);
    try {
      await api.updatePlaylistSource(feedId, source.id, {
        refresh_interval_override: value === '' ? null : parseInt(value, 10),
      });
      onUpdate();
    } catch (err) {
      alert(err.message || 'Failed to update interval');
    } finally {
      setUpdatingInterval(null);
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
            </p>
          </div>
          <div className="flex items-center gap-2 ml-4">
            <select
              value={source.refresh_interval_override || ''}
              onChange={(e) => handleIntervalChange(source, e.target.value)}
              disabled={updatingInterval === source.id}
              className="text-xs border border-gray-300 rounded px-1.5 py-1 text-gray-700 bg-white disabled:opacity-50"
            >
              {INTERVAL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
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
