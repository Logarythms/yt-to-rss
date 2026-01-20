import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import FeedForm from '../components/FeedForm';

export default function CreateFeed() {
  const navigate = useNavigate();

  const handleSubmit = async ({ name, author, description, artwork }) => {
    const feed = await api.createFeed(name, author, description, artwork);
    navigate(`/feeds/${feed.id}`);
  };

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create New Feed</h1>
        <p className="mt-1 text-sm text-gray-500">
          Create a new podcast feed to add YouTube videos to.
        </p>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <FeedForm onSubmit={handleSubmit} submitLabel="Create Feed" />
      </div>
    </div>
  );
}
