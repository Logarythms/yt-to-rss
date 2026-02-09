import { Routes, Route, Navigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Layout from './components/Layout';
import Login from './components/Login';
import Home from './pages/Home';
import CreateFeed from './pages/CreateFeed';
import EditFeed from './pages/EditFeed';
import Storage from './pages/Storage';
import { api } from './api';

function ProtectedRoute({ children }) {
  if (!api.isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    // Verify token on mount
    if (api.isAuthenticated()) {
      api.verify().catch(() => {
        api.logout();
      }).finally(() => {
        setIsChecking(false);
      });
    } else {
      setIsChecking(false);
    }
  }, []);

  if (isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500 dark:text-gray-400">Loading...</div>
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Home />} />
        <Route path="feeds/new" element={<CreateFeed />} />
        <Route path="feeds/:id" element={<EditFeed />} />
        <Route path="storage" element={<Storage />} />
      </Route>
    </Routes>
  );
}
