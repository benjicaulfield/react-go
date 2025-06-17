import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  fetchDashboardStats,
  refreshRecordOfTheDay,
  voteRecordOfTheDay,
  clearError,
} from '../store/slices/dashboardSlice';

const Dashboard: React.FC = () => {
  const dispatch = useAppDispatch();
  const { stats, loading, error, refreshingRecord } = useAppSelector(
    (state) => state.dashboard
  );

  const [desirabilityRating, setDesirabilityRating] = useState<number | null>(null);
  const [noveltyRating, setNoveltyRating] = useState<number | null>(null);
  const [voteMessage, setVoteMessage] = useState<string>('');

  useEffect(() => {
    dispatch(fetchDashboardStats());
  }, [dispatch]);

  const handleRefreshRecord = () => {
    dispatch(refreshRecordOfTheDay()).then(() => {
      // Refresh stats to get the new record
      dispatch(fetchDashboardStats());
    });
  };

  const handleVoteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (desirabilityRating && noveltyRating && stats?.record_of_the_day_obj) {
      dispatch(
        voteRecordOfTheDay({
          recordId: stats.record_of_the_day_obj.id,
          desirability: desirabilityRating,
          novelty: noveltyRating,
        })
      ).then(() => {
        setVoteMessage('Vote submitted! Thanks for your feedback.');
        setDesirabilityRating(null);
        setNoveltyRating(null);
      });
    }
  };

  if (loading && !stats) {
    return (
      <div className="max-w-7xl mx-auto p-5">
        <div className="text-center text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-5">
      <h1 className="text-3xl text-white mb-5">Dashboard</h1>

      {error && (
        <div className="bg-red-900 border border-red-700 text-red-100 px-4 py-3 rounded mb-4">
          {error}
          <button
            onClick={() => dispatch(clearError())}
            className="ml-2 text-red-300 hover:text-red-100"
          >
            ×
          </button>
        </div>
      )}

      {/* Metrics Section */}
      <div className="flex justify-between gap-4 mb-8">
        <div className="metric-card">
          <h3 className="font-bold">Number of Records</h3>
          <p>{stats?.num_records || 0}</p>
        </div>
        <div className="metric-card">
          <h3 className="font-bold">Number of Listings</h3>
          <p>{stats?.num_listings || 0}</p>
        </div>
        <div className="metric-card">
          <h3 className="font-bold">Model Prediction Accuracy</h3>
          <p>{stats?.accuracy || 0}%</p>
        </div>
        <div className="metric-card">
          <h3 className="font-bold">Unevaluated Listings Remaining</h3>
          <p>{stats?.unevaluated || 0}</p>
        </div>
      </div>

      {/* Record of the Day */}
      <div className="mb-8">
        <div className="flex justify-between items-center mb-3">
          <h2 className="text-2xl text-white">Record of the Day</h2>
          <button
            onClick={handleRefreshRecord}
            disabled={refreshingRecord}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
          >
            {refreshingRecord ? 'Refreshing...' : 'Refresh Selection'}
          </button>
        </div>
        <p className="text-sm text-gray-400 mb-4">
          Selected using thermodynamic computing principles that balance exploitation (high scores) with exploration (novelty)
        </p>

        {stats?.record_of_the_day ? (
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            {/* Main Record Info */}
            <div className="mb-4">
              <h3 className="text-xl font-bold text-white mb-2">
                {stats.record_of_the_day.record.artist} - {stats.record_of_the_day.record.title}
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Price:</span>
                  <span className="text-green-400 font-semibold ml-1">
                    ${stats.record_of_the_day.record_price}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Score:</span>
                  <span className="text-blue-400 font-semibold ml-1">
                    {parseFloat(stats.record_of_the_day.score).toFixed(2)}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Year:</span>
                  <span className="text-white ml-1">
                    {stats.record_of_the_day.record.year || 'N/A'}
                  </span>
                </div>
                <div>
                  <span className="text-gray-400">Condition:</span>
                  <span className="text-white ml-1">
                    {stats.record_of_the_day.media_condition}
                  </span>
                </div>
              </div>
              {stats.record_of_the_day.record.genres && stats.record_of_the_day.record.genres.length > 0 && (
                <div className="mt-2">
                  <span className="text-gray-400 text-sm">Genres:</span>
                  {stats.record_of_the_day.record.genres.map((genre, index) => (
                    <span
                      key={index}
                      className="inline-block bg-gray-700 text-xs px-2 py-1 rounded mr-1 mt-1"
                    >
                      {genre}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Thermodynamic Analysis Breakdown */}
            {stats.breakdown && (
              <div className="border-t border-gray-700 pt-4">
                <h4 className="text-lg font-semibold text-white mb-3">
                  🔬 Thermodynamic Selection Analysis
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  {/* Key Metrics */}
                  <div className="bg-gray-900 rounded p-3">
                    <h5 className="font-semibold text-purple-300 mb-2">Key Metrics</h5>
                    <div className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Novelty (Entropy):</span>
                        <span className="text-white font-mono">
                          {stats.breakdown.entropy_measure?.toFixed(3) || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Desirability (Temperature):</span>
                        <span className="text-white font-mono">
                          {stats.breakdown.system_temperature?.toFixed(3) || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Model Score:</span>
                        <span className="text-white font-mono">
                          {stats.breakdown.model_score?.toFixed(3) || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Formula Explanation */}
                  <div className="bg-gray-900 rounded p-3">
                    <h5 className="font-semibold text-blue-300 mb-2">How It Works</h5>
                    <div className="text-xs text-gray-400">
                      <p>This system uses thermodynamic principles to balance between:</p>
                      <ul className="list-disc pl-4 mt-1 space-y-1">
                        <li>
                          <strong>Exploitation:</strong> Selecting high-scoring records
                        </li>
                        <li>
                          <strong>Exploration:</strong> Discovering novel, surprising records
                        </li>
                      </ul>
                      <p className="mt-1">Higher temperature = more exploration</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Rate This Selection */}
            <div className="mt-6 border-t border-gray-700 pt-4">
              <h4 className="text-lg font-semibold text-white mb-3">Rate This Selection</h4>
              <p className="text-sm text-gray-400 mb-3">
                Your feedback helps improve future recommendations
              </p>

              <form onSubmit={handleVoteSubmit}>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Desirability Rating */}
                  <div className="bg-gray-900 rounded p-3">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Desirability
                    </label>
                    <p className="text-xs text-gray-500 mb-2">How much do you like this record?</p>
                    <div className="flex space-x-2">
                      {[1, 2, 3, 4, 5].map((rating) => (
                        <label key={rating} className="rating-label">
                          <input
                            type="radio"
                            name="desirability"
                            value={rating}
                            checked={desirabilityRating === rating}
                            onChange={(e) => setDesirabilityRating(parseInt(e.target.value))}
                            className="sr-only peer"
                          />
                          <span className="w-8 h-8 flex items-center justify-center rounded border border-gray-600 peer-checked:bg-blue-600 peer-checked:border-blue-500 cursor-pointer hover:bg-gray-800">
                            {rating}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>

                  {/* Novelty Rating */}
                  <div className="bg-gray-900 rounded p-3">
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Novelty/Surprise
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                      How surprising or novel is this selection?
                    </p>
                    <div className="flex space-x-2">
                      {[1, 2, 3, 4, 5].map((rating) => (
                        <label key={rating} className="rating-label">
                          <input
                            type="radio"
                            name="novelty"
                            value={rating}
                            checked={noveltyRating === rating}
                            onChange={(e) => setNoveltyRating(parseInt(e.target.value))}
                            className="sr-only peer"
                          />
                          <span className="w-8 h-8 flex items-center justify-center rounded border border-gray-600 peer-checked:bg-purple-600 peer-checked:border-purple-500 cursor-pointer hover:bg-gray-800">
                            {rating}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>

                <div className="mt-4 text-center">
                  <button
                    type="submit"
                    disabled={!desirabilityRating || !noveltyRating}
                    className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
                  >
                    Submit Feedback
                  </button>
                </div>
              </form>

              {voteMessage && (
                <div className="mt-2 text-center text-green-400 text-sm">{voteMessage}</div>
              )}
            </div>
          </div>
        ) : (
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <p className="text-gray-400">
              No records available yet. Add some listings to see thermodynamic selection in action!
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
