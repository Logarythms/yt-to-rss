import { Link } from 'react-router-dom';

function formatDate(dateString) {
  if (!dateString) return null;
  const date = new Date(dateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function FeedList({ feeds }) {
  if (feeds.length === 0) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium text-gray-900">No feeds yet</h3>
        <p className="mt-2 text-sm text-gray-500">
          Create your first podcast feed to get started.
        </p>
        <div className="mt-6">
          <Link
            to="/feeds/new"
            className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700"
          >
            Create Feed
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {feeds.map((feed) => (
        <Link
          key={feed.id}
          to={`/feeds/${feed.id}`}
          className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
        >
          <h3 className="text-lg font-medium text-gray-900 truncate">
            {feed.name}
          </h3>
          {feed.description && (
            <p className="mt-1 text-sm text-gray-500 line-clamp-2">
              {feed.description}
            </p>
          )}
          <div className="mt-4 flex items-center justify-between text-sm text-gray-500">
            <span>{feed.episode_count} episode{feed.episode_count !== 1 ? 's' : ''}</span>
            <span>
              {formatDate(feed.created_at)}
            </span>
          </div>
        </Link>
      ))}
    </div>
  );
}
