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
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">No feeds yet</h3>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
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
          className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
        >
          <div className="flex gap-4">
            {feed.artwork_path ? (
              <img
                src={`/artwork/${feed.id}`}
                alt=""
                className="w-16 h-16 rounded-md object-cover flex-shrink-0"
              />
            ) : (
              <div className="w-16 h-16 rounded-md bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                <svg className="w-8 h-8 text-gray-400 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </div>
            )}
            <div className="min-w-0 flex-1">
              <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 truncate">
                {feed.name}
              </h3>
              {feed.description && (
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400 line-clamp-2">
                  {feed.description}
                </p>
              )}
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
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
