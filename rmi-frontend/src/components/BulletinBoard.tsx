/**
 * BulletinBoard - Community Bulletin Board
 * =========================================
 * View and create bulletin posts with upvote/downvote functionality.
 * Connected to /api/v1/bulletin endpoints.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bell, MessageSquare, ThumbsUp, ThumbsDown, Clock,
  Plus, Search, Filter, Tag, User, ChevronUp, ChevronDown,
  Loader2, AlertCircle, CheckCircle,
} from 'lucide-react';
import { useAppStore } from '../store/appStore';
import api from '../services/api';

const CATEGORIES = [
  { id: 'all', label: 'All', color: 'gray' },
  { id: 'announcement', label: 'Announcements', color: 'blue' },
  { id: 'alert', label: 'Alerts', color: 'red' },
  { id: 'update', label: 'Updates', color: 'green' },
  { id: 'community', label: 'Community', color: 'purple' },
];

const CHAINS = [
  { id: 'all', label: 'All Chains' },
  { id: 'solana', label: 'Solana' },
  { id: 'ethereum', label: 'Ethereum' },
  { id: 'base', label: 'Base' },
  { id: 'bsc', label: 'BSC' },
  { id: 'arbitrum', label: 'Arbitrum' },
];

interface BulletinPost {
  id: string;
  title: string;
  content: string;
  category: string;
  chain: string;
  author_id?: string;
  author_name?: string;
  upvotes: number;
  downvotes: number;
  created_at: string;
  updated_at?: string;
}

export default function BulletinBoard() {
  const [activeCategory, setActiveCategory] = useState('all');
  const [activeChain, setActiveChain] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newPost, setNewPost] = useState({
    title: '',
    content: '',
    category: 'announcement',
    chain: 'solana',
  });

  const user = useAppStore((state) => state.user);
  const queryClient = useQueryClient();

  const { data: bulletinsData, isLoading } = useQuery({
    queryKey: ['bulletin', activeCategory, activeChain],
    queryFn: () => api.getBulletins(
      activeCategory === 'all' ? undefined : activeCategory,
      activeChain === 'all' ? undefined : activeChain
    ),
    refetchInterval: 15000,
  });

  const createPost = useMutation({
    mutationFn: (post: { title: string; content: string; category: string; chain: string }) =>
      api.createBulletin(post),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bulletin'] });
      setShowCreateModal(false);
      setNewPost({ title: '', content: '', category: 'announcement', chain: 'solana' });
    },
  });

  const upvotePost = useMutation({
    mutationFn: (postId: string) => api.upvoteBulletin(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bulletin'] });
    },
  });

  const downvotePost = useMutation({
    mutationFn: (postId: string) => api.downvoteBulletin(postId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bulletin'] });
    },
  });

  const bulletins: BulletinPost[] = bulletinsData?.posts || [];

  const filteredPosts = bulletins.filter((post) => {
    if (searchQuery && !post.title.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !post.content.toLowerCase().includes(searchQuery.toLowerCase())) {
      return false;
    }
    return true;
  });

  const getCategoryColor = (categoryId: string) => {
    const colors: Record<string, string> = {
      announcement: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      alert: 'bg-red-500/20 text-red-400 border-red-500/30',
      update: 'bg-green-500/20 text-green-400 border-green-500/30',
      community: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    };
    return colors[categoryId] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  };

  const formatTime = (dateStr: string) => {
    const d = new Date(dateStr);
    const now = new Date();
    const diff = (now.getTime() - d.getTime()) / 1000;
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPost.title.trim() || !newPost.content.trim()) return;
    createPost.mutate(newPost);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-purple-600/20 rounded-xl">
            <Bell size={28} className="text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Bulletin Board</h1>
            <p className="text-gray-400 text-sm">Community announcements and alerts</p>
          </div>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-4 py-2.5 rounded-lg font-medium transition-colors"
        >
          <Plus size={18} />
          New Post
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search bulletins..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-gray-800 text-white pl-10 pr-4 py-2.5 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setActiveCategory(cat.id)}
              className={`px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
                activeCategory === cat.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
        <select
          value={activeChain}
          onChange={(e) => setActiveChain(e.target.value)}
          className="bg-gray-800 text-white px-4 py-2 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
        >
          {CHAINS.map((chain) => (
            <option key={chain.id} value={chain.id}>{chain.label}</option>
          ))}
        </select>
      </div>

      {/* Posts List */}
      <div className="space-y-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={32} className="text-purple-400 animate-spin" />
            <span className="ml-3 text-gray-400">Loading bulletins...</span>
          </div>
        ) : filteredPosts.length === 0 ? (
          <div className="text-center py-12 bg-gray-800/50 rounded-xl border border-gray-700">
            <Bell size={48} className="mx-auto text-gray-600 mb-4" />
            <h3 className="text-lg font-medium text-gray-300 mb-2">No bulletins yet</h3>
            <p className="text-gray-500 mb-4">Be the first to post an announcement or alert!</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="bg-purple-600 hover:bg-purple-500 text-white px-6 py-2 rounded-lg font-medium"
            >
              Create Post
            </button>
          </div>
        ) : (
          filteredPosts.map((post) => (
            <div
              key={post.id}
              className="bg-gray-800 rounded-xl p-5 border border-gray-700 hover:border-purple-500/30 transition-colors"
            >
              <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium border ${getCategoryColor(post.category)}`}>
                      {post.category}
                    </span>
                    {post.chain && post.chain !== 'all' && (
                      <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-gray-700 text-gray-300">
                        {post.chain}
                      </span>
                    )}
                  </div>
                  <h3 className="text-lg font-semibold text-white mb-1">{post.title}</h3>
                  <p className="text-gray-400 text-sm line-clamp-2">{post.content}</p>
                </div>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-gray-700">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => upvotePost.mutate(post.id)}
                      className="flex items-center gap-1 text-gray-400 hover:text-emerald-400 transition-colors"
                    >
                      <ChevronUp size={18} />
                      <span className="text-sm font-medium">{post.upvotes}</span>
                    </button>
                    <button
                      onClick={() => downvotePost.mutate(post.id)}
                      className="flex items-center gap-1 text-gray-400 hover:text-red-400 transition-colors ml-2"
                    >
                      <ChevronDown size={18} />
                      <span className="text-sm font-medium">{post.downvotes}</span>
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3 text-gray-500 text-sm">
                  <Clock size={14} />
                  <span>{formatTime(post.created_at)}</span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Post Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-2xl p-6 max-w-lg w-full border border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-white">Create Bulletin Post</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Title</label>
                <input
                  type="text"
                  value={newPost.title}
                  onChange={(e) => setNewPost({ ...newPost, title: e.target.value })}
                  placeholder="Enter post title..."
                  className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Category</label>
                  <select
                    value={newPost.category}
                    onChange={(e) => setNewPost({ ...newPost, category: e.target.value })}
                    className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                  >
                    {CATEGORIES.filter(c => c.id !== 'all').map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Chain</label>
                  <select
                    value={newPost.chain}
                    onChange={(e) => setNewPost({ ...newPost, chain: e.target.value })}
                    className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
                  >
                    {CHAINS.filter(c => c.id !== 'all').map((chain) => (
                      <option key={chain.id} value={chain.id}>{chain.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Content</label>
                <textarea
                  value={newPost.content}
                  onChange={(e) => setNewPost({ ...newPost, content: e.target.value })}
                  placeholder="Write your bulletin content..."
                  rows={5}
                  className="w-full bg-gray-800 text-white px-4 py-3 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none resize-none"
                  required
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 bg-gray-800 hover:bg-gray-700 text-white px-4 py-3 rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createPost.isPending}
                  className="flex-1 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
                >
                  {createPost.isPending && <Loader2 size={18} className="animate-spin" />}
                  {createPost.isPending ? 'Posting...' : 'Create Post'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
