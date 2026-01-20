import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function ProgressBar({ used, total, className = '' }) {
  const percentage = total > 0 ? Math.min((used / total) * 100, 100) : 0;
  const color = percentage > 90 ? 'bg-red-500' : percentage > 70 ? 'bg-yellow-500' : 'bg-green-500';

  return (
    <div className={`w-full bg-gray-200 rounded-full h-2.5 ${className}`}>
      <div
        className={`h-2.5 rounded-full ${color}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

export default function Storage() {
  const [storage, setStorage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const loadStorage = async () => {
      try {
        const data = await api.getStorage();
        setStorage(data);
      } catch (err) {
        setError(err.message || 'Failed to load storage info');
      } finally {
        setLoading(false);
      }
    };
    loadStorage();
  }, []);

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500">Loading storage info...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600">{error}</div>
      </div>
    );
  }

  const usedPercentage = storage.total_capacity > 0
    ? ((storage.total_used / storage.total_capacity) * 100).toFixed(1)
    : 0;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Storage</h1>
        <p className="mt-1 text-sm text-gray-500">
          Monitor storage usage across your podcast feeds.
        </p>
      </div>

      {/* Overall Storage */}
      <div className="mb-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Disk Usage</h2>

        <div className="space-y-4">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-600">Used by podcasts</span>
              <span className="font-medium">{formatBytes(storage.total_used)}</span>
            </div>
            <ProgressBar used={storage.total_used} total={storage.total_capacity} />
          </div>

          <div className="grid grid-cols-3 gap-4 pt-4 border-t">
            <div>
              <div className="text-sm text-gray-500">Total Used</div>
              <div className="text-lg font-semibold text-gray-900">
                {formatBytes(storage.total_used)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Free Space</div>
              <div className="text-lg font-semibold text-gray-900">
                {formatBytes(storage.total_free)}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Total Capacity</div>
              <div className="text-lg font-semibold text-gray-900">
                {formatBytes(storage.total_capacity)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Feed Storage */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Storage by Feed</h2>

        {storage.feeds.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No feeds yet.</p>
        ) : (
          <div className="space-y-4">
            {storage.feeds
              .sort((a, b) => b.total_size - a.total_size)
              .map((feed) => (
                <div key={feed.id} className="flex items-center justify-between py-2 border-b last:border-0">
                  <div className="min-w-0 flex-1">
                    <Link
                      to={`/feeds/${feed.id}`}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-500 truncate block"
                    >
                      {feed.name}
                    </Link>
                    <div className="text-xs text-gray-500">
                      {feed.episode_count} episode{feed.episode_count !== 1 ? 's' : ''}
                    </div>
                  </div>
                  <div className="ml-4 text-right">
                    <div className="text-sm font-medium text-gray-900">
                      {formatBytes(feed.total_size)}
                    </div>
                    {storage.total_used > 0 && (
                      <div className="text-xs text-gray-500">
                        {((feed.total_size / storage.total_used) * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>
    </div>
  );
}
