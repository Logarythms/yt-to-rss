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
  const [migrationLoading, setMigrationLoading] = useState(false);
  const [migrationResult, setMigrationResult] = useState(null);
  const [showConfirm, setShowConfirm] = useState(false);

  const handleMigration = async (dryRun = false) => {
    setMigrationLoading(true);
    setMigrationResult(null);
    try {
      const result = await api.migrateImages(dryRun);
      setMigrationResult({ ...result, dryRun });
    } catch (err) {
      setMigrationResult({ error: err.message || 'Migration failed' });
    } finally {
      setMigrationLoading(false);
      setShowConfirm(false);
    }
  };

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

      {/* Maintenance */}
      <div className="mt-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Maintenance</h2>

        <div className="space-y-4">
          <div>
            <p className="text-sm text-gray-600 mb-3">
              Download missing episode thumbnails from YouTube, then make all feed artwork and thumbnails
              square (1:1 aspect ratio) by adding black letterboxing. This improves compatibility with podcast apps.
            </p>
            <p className="text-sm text-amber-600 mb-3">
              Warning: This permanently modifies image files. Original images cannot be restored.
            </p>

            <div className="flex gap-2">
              <button
                onClick={() => handleMigration(true)}
                disabled={migrationLoading}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
              >
                {migrationLoading ? 'Checking...' : 'Preview'}
              </button>

              {showConfirm ? (
                <>
                  <button
                    onClick={() => handleMigration(false)}
                    disabled={migrationLoading}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700 disabled:opacity-50"
                  >
                    Confirm
                  </button>
                  <button
                    onClick={() => setShowConfirm(false)}
                    disabled={migrationLoading}
                    className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  onClick={() => setShowConfirm(true)}
                  disabled={migrationLoading}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 disabled:opacity-50"
                >
                  Make Images Square
                </button>
              )}
            </div>
          </div>

          {migrationResult && (
            <div className={`p-4 rounded-md ${migrationResult.error ? 'bg-red-50' : 'bg-gray-50'}`}>
              {migrationResult.error ? (
                <p className="text-sm text-red-700">{migrationResult.error}</p>
              ) : (
                <div className="text-sm">
                  <p className="font-medium text-gray-900 mb-2">
                    {migrationResult.dryRun ? 'Preview Results' : 'Migration Complete'}
                  </p>
                  {(migrationResult.thumbnails_downloaded > 0 || migrationResult.thumbnails_failed > 0) && (
                    <div className="mb-3 pb-3 border-b border-gray-200">
                      <p className="font-medium text-gray-700 mb-1">Thumbnail Downloads</p>
                      <ul className="space-y-1 text-gray-600">
                        <li className="text-blue-600">
                          {migrationResult.dryRun ? 'Would download' : 'Downloaded'}: {migrationResult.thumbnails_downloaded}
                        </li>
                        {migrationResult.thumbnails_failed > 0 && (
                          <li className="text-red-600">Failed: {migrationResult.thumbnails_failed}</li>
                        )}
                      </ul>
                    </div>
                  )}
                  <p className="font-medium text-gray-700 mb-1">Letterboxing</p>
                  <ul className="space-y-1 text-gray-600">
                    <li>Total images: {migrationResult.total_images}</li>
                    <li className="text-green-600">
                      {migrationResult.dryRun ? 'Would process' : 'Processed'}: {migrationResult.processed}
                    </li>
                    <li>Already square (skipped): {migrationResult.skipped}</li>
                    {migrationResult.failed > 0 && (
                      <li className="text-red-600">Failed: {migrationResult.failed}</li>
                    )}
                  </ul>
                  {migrationResult.errors?.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-200">
                      <p className="text-xs text-red-600">
                        Errors: {migrationResult.errors.slice(0, 5).join(', ')}
                        {migrationResult.errors.length > 5 && ` and ${migrationResult.errors.length - 5} more`}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
