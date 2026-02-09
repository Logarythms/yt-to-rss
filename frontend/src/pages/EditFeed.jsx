import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import FeedForm from '../components/FeedForm';
import EpisodeList from '../components/EpisodeList';
import AddVideosModal from '../components/AddVideosModal';
import UploadAudioModal from '../components/UploadAudioModal';
import PlaylistSources from '../components/PlaylistSources';

export default function EditFeed() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showAddVideos, setShowAddVideos] = useState(false);
  const [showUploadAudio, setShowUploadAudio] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const loadFeed = useCallback(async () => {
    try {
      const data = await api.getFeed(id);
      setFeed(data);
    } catch (err) {
      setError(err.message || 'Failed to load feed');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadFeed();

    // Poll for updates every 5 seconds if there are pending/downloading episodes
    const interval = setInterval(() => {
      loadFeed();
    }, 5000);

    return () => clearInterval(interval);
  }, [loadFeed]);

  const handleUpdate = async ({ name, author, description, artwork }) => {
    await api.updateFeed(id, name, author, description, artwork);
    await loadFeed();
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this feed? This will also delete all episodes.')) {
      return;
    }

    setDeleting(true);
    try {
      await api.deleteFeed(id);
      navigate('/');
    } catch (err) {
      alert(err.message || 'Failed to delete feed');
      setDeleting(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.refreshFeed(id);
      await loadFeed();
    } catch (err) {
      alert(err.message || 'Failed to refresh playlists');
    } finally {
      setRefreshing(false);
    }
  };

  const handleVideosAdded = (result) => {
    loadFeed();
  };

  const handleAudioUploaded = (result) => {
    loadFeed();
  };

  const copyRssUrl = () => {
    // Fallback for non-HTTPS contexts
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(feed.rss_url);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = feed.rss_url;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    alert('RSS URL copied to clipboard!');
  };

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500">Loading feed...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600">{error}</div>
        <button
          onClick={() => navigate('/')}
          className="mt-4 text-indigo-600 hover:text-indigo-500"
        >
          Back to feeds
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{feed.name}</h1>
          <p className="mt-1 text-sm text-gray-500">
            {feed.episodes.length} episode{feed.episodes.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-red-600 hover:text-red-500 text-sm disabled:opacity-50"
        >
          {deleting ? 'Deleting...' : 'Delete Feed'}
        </button>
      </div>

      {/* RSS URL */}
      <div className="mb-8 bg-gray-50 rounded-lg p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              RSS Feed URL
            </label>
            <code className="block text-sm text-gray-600 truncate">
              {feed.rss_url}
            </code>
          </div>
          <button
            onClick={copyRssUrl}
            className="flex-shrink-0 px-4 py-2 bg-white border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Copy
          </button>
        </div>
      </div>

      {/* Feed Settings */}
      <div className="mb-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Feed Settings</h2>
        <FeedForm
          initialData={feed}
          onSubmit={handleUpdate}
          submitLabel="Save Changes"
        />
      </div>

      {/* Tracked Playlists */}
      {feed.playlist_sources && feed.playlist_sources.length > 0 && (
        <div className="mb-8 bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">
              Tracked Playlists
              <span className="ml-2 text-sm font-normal text-gray-500">
                ({feed.playlist_sources.length})
              </span>
            </h2>
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50 disabled:opacity-50"
            >
              {refreshing ? 'Refreshing...' : 'Refresh Now'}
            </button>
          </div>
          <PlaylistSources
            feedId={id}
            sources={feed.playlist_sources}
            onUpdate={loadFeed}
          />
        </div>
      )}

      {/* Episodes */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium text-gray-900">Episodes</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setShowUploadAudio(true)}
              className="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50"
            >
              Upload Audio
            </button>
            <button
              onClick={() => setShowAddVideos(true)}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700"
            >
              Add Videos
            </button>
          </div>
        </div>

        <EpisodeList
          feedId={id}
          episodes={feed.episodes}
          onUpdate={loadFeed}
        />
      </div>

      {showAddVideos && (
        <AddVideosModal
          feedId={id}
          onClose={() => setShowAddVideos(false)}
          onAdded={handleVideosAdded}
        />
      )}

      {showUploadAudio && (
        <UploadAudioModal
          feedId={id}
          onClose={() => setShowUploadAudio(false)}
          onUploaded={handleAudioUploaded}
        />
      )}
    </div>
  );
}
