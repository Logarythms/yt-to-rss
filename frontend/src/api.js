const API_BASE = '/api';

function getToken() {
  return localStorage.getItem('token');
}

function setToken(token) {
  localStorage.setItem('token', token);
}

function clearToken() {
  localStorage.removeItem('token');
}

async function request(path, options = {}) {
  const token = getToken();
  const headers = {
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Don't set Content-Type for FormData
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearToken();
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }

  return response.json();
}

export const api = {
  // Auth
  login: async (password) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
    setToken(data.access_token);
    return data;
  },

  logout: () => {
    clearToken();
  },

  verify: () => request('/auth/verify'),

  isAuthenticated: () => !!getToken(),

  // Feeds
  getFeeds: () => request('/feeds'),

  getFeed: (id) => request(`/feeds/${id}`),

  createFeed: async (name, author, description, artwork) => {
    const formData = new FormData();
    formData.append('name', name);
    if (author) formData.append('author', author);
    if (description) formData.append('description', description);
    if (artwork) formData.append('artwork', artwork);

    return request('/feeds', {
      method: 'POST',
      body: formData,
    });
  },

  updateFeed: async (id, name, author, description, artwork) => {
    const formData = new FormData();
    if (name) formData.append('name', name);
    if (author !== undefined) formData.append('author', author || '');
    if (description !== undefined) formData.append('description', description || '');
    if (artwork) formData.append('artwork', artwork);

    return request(`/feeds/${id}`, {
      method: 'PUT',
      body: formData,
    });
  },

  deleteFeed: (id) => request(`/feeds/${id}`, { method: 'DELETE' }),

  addVideos: (feedId, urls) => request(`/feeds/${feedId}/add-videos`, {
    method: 'POST',
    body: JSON.stringify({ urls }),
  }),

  deleteEpisode: (feedId, episodeId) => request(`/feeds/${feedId}/episodes/${episodeId}`, {
    method: 'DELETE',
  }),

  retryEpisode: (feedId, episodeId) => request(`/feeds/${feedId}/episodes/${episodeId}/retry`, {
    method: 'POST',
  }),

  updateEpisode: (feedId, episodeId, data) => request(`/feeds/${feedId}/episodes/${episodeId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  uploadAudio: (feedId, audio, thumbnail, title, description, onProgress) => {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('audio', audio);
      if (thumbnail) formData.append('thumbnail', thumbnail);
      if (title) formData.append('title', title);
      if (description) formData.append('description', description);

      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${API_BASE}/feeds/${feedId}/upload-audio`);

      const token = getToken();
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && onProgress) {
          const percent = Math.round((event.loaded / event.total) * 100);
          onProgress(percent);
        }
      };

      xhr.onload = () => {
        if (xhr.status === 200 || xhr.status === 201) {
          resolve(JSON.parse(xhr.responseText));
        } else if (xhr.status === 401) {
          clearToken();
          window.location.href = '/login';
          reject(new Error('Unauthorized'));
        } else {
          try {
            const error = JSON.parse(xhr.responseText);
            reject(new Error(error.detail || 'Upload failed'));
          } catch {
            reject(new Error('Upload failed'));
          }
        }
      };

      xhr.onerror = () => reject(new Error('Network error'));
      xhr.send(formData);
    });
  },

  // Playlist Sources
  refreshFeed: (feedId) => request(`/feeds/${feedId}/refresh`, {
    method: 'POST',
  }),

  removePlaylistSource: (feedId, sourceId) => request(`/feeds/${feedId}/playlist-sources/${sourceId}`, {
    method: 'DELETE',
  }),

  updatePlaylistSource: (feedId, sourceId, data) => request(`/feeds/${feedId}/playlist-sources/${sourceId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }),

  // Storage
  getStorage: () => request('/feeds/storage/info'),

  // Admin
  migrateImages: (dryRun = false) => request('/admin/migrate-images', {
    method: 'POST',
    body: JSON.stringify({ dry_run: dryRun }),
  }),
};
