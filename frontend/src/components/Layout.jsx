import { useEffect } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { initTheme } from '../theme';
import ThemeToggle from './ThemeToggle';

export default function Layout() {
  const navigate = useNavigate();

  useEffect(() => {
    initTheme();
  }, []);

  const handleLogout = () => {
    api.logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <nav className="bg-white dark:bg-gray-900 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold text-indigo-600">
                yt-to-rss
              </Link>
            </div>
            <div className="flex items-center gap-4">
              <Link
                to="/storage"
                className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 text-sm font-medium"
              >
                Storage
              </Link>
              <Link
                to="/feeds/new"
                className="bg-indigo-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-indigo-700"
              >
                New Feed
              </Link>
              <ThemeToggle />
              <button
                onClick={handleLogout}
                className="text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 text-sm"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}
