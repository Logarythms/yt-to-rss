import { useState, useEffect } from 'react';
import { api } from '../api';
import FeedList from '../components/FeedList';

export default function Home() {
  const [feeds, setFeeds] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadFeeds = async () => {
    try {
      const data = await api.getFeeds();
      setFeeds(data.feeds);
    } catch (err) {
      setError(err.message || 'Failed to load feeds');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFeeds();
  }, []);

  if (loading) {
    return (
      <div className="text-center py-12">
        <div className="text-gray-500">Loading feeds...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600">{error}</div>
        <button
          onClick={loadFeeds}
          className="mt-4 text-indigo-600 hover:text-indigo-500"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Your Feeds</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your podcast feeds created from YouTube videos.
        </p>
      </div>

      <FeedList feeds={feeds} />
    </div>
  );
}
