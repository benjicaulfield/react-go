import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  setListings,
  toggleKeeper,
  clearKeepers,
  clearError,
  resetSession,
  fetchRecommendationPredictions,
  submitRecommendations,
  fetchModelPerformanceStats,
} from '../store/slices/recommendationSlice';

const Recommender: React.FC = () => {
  const dispatch = useAppDispatch();
  const {
    listings,
    predictions,
    selectedKeepers,
    loading,
    submitting,
    error,
    totalUnevaluated,
    modelStats,
  } = useAppSelector((state) => state.recommendation);

  const [showPredictions, setShowPredictions] = useState(false);

  useEffect(() => {
    dispatch(fetchModelPerformanceStats());
    // In a real app, you'd fetch unevaluated listings here
    // For now, we'll simulate with empty data
    dispatch(setListings({ listings: [], totalUnevaluated: 0 }));
  }, [dispatch]);

  const handleGetPredictions = () => {
    if (listings.length > 0) {
      const listingIds = listings.map(listing => listing.id);
      dispatch(fetchRecommendationPredictions(listingIds));
      setShowPredictions(true);
    }
  };

  const handleSubmit = () => {
    if (listings.length > 0) {
      const listingIds = listings.map(listing => listing.id);
      dispatch(submitRecommendations({ listingIds, keeperIds: selectedKeepers }))
        .then(() => {
          // Reset for next batch
          dispatch(resetSession());
          setShowPredictions(false);
          // Fetch new batch of listings here
        });
    }
  };

  const handleToggleKeeper = (listingId: number) => {
    dispatch(toggleKeeper(listingId));
  };

  const getPredictionForListing = (listingId: number) => {
    return predictions.find(p => p.id === listingId);
  };

  return (
    <div className="max-w-7xl mx-auto p-5">
      <h1 className="text-3xl text-white mb-5">Recommendation System</h1>

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

      {/* Model Performance Stats */}
      {modelStats && (
        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-6">
          <h2 className="text-xl font-bold text-white mb-4">Model Performance</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="metric-card">
              <h3 className="font-bold">Current Accuracy</h3>
              <p>{(modelStats.accuracy * 100).toFixed(1)}%</p>
            </div>
            <div className="metric-card">
              <h3 className="font-bold">Training Sessions</h3>
              <p>{modelStats.total_sessions}</p>
            </div>
            <div className="metric-card">
              <h3 className="font-bold">Unevaluated Remaining</h3>
              <p>{totalUnevaluated}</p>
            </div>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-6">
        <h2 className="text-xl font-bold text-white mb-4">How it works</h2>
        <div className="space-y-3 text-gray-300">
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">1.</span>
            <p>Review the records below and select which ones you would want to keep (purchase).</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">2.</span>
            <p>Optionally, get AI predictions to see what the model thinks you'll like.</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">3.</span>
            <p>Submit your selections to train the machine learning model.</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">4.</span>
            <p>The model learns from your preferences and improves future recommendations.</p>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      {listings.length > 0 && (
        <div className="flex gap-4 mb-6">
          <button
            onClick={handleGetPredictions}
            disabled={loading || showPredictions}
            className="bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            {loading ? 'Getting Predictions...' : 'Get AI Predictions'}
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || listings.length === 0}
            className="bg-green-600 hover:bg-green-700 disabled:bg-green-800 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            {submitting ? 'Submitting...' : `Submit Selections (${selectedKeepers.length} selected)`}
          </button>
          <button
            onClick={() => dispatch(clearKeepers())}
            className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            Clear Selections
          </button>
        </div>
      )}

      {/* Listings */}
      {listings.length > 0 ? (
        <div className="space-y-4">
          {listings.map((listing) => {
            const prediction = getPredictionForListing(listing.id);
            const isSelected = selectedKeepers.includes(listing.id);
            
            return (
              <div
                key={listing.id}
                className={`bg-gray-800 p-4 rounded-lg border transition-colors ${
                  isSelected ? 'border-green-500 bg-gray-750' : 'border-gray-700'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="text-lg font-bold text-white">
                        {listing.record.artist} - {listing.record.title}
                      </h3>
                      <div className="flex items-center gap-4">
                        {showPredictions && prediction && (
                          <div className="text-right">
                            <div className="text-sm text-gray-400">AI Prediction</div>
                            <div className={`font-semibold ${
                              prediction.prediction ? 'text-green-400' : 'text-red-400'
                            }`}>
                              {prediction.prediction ? 'Keep' : 'Skip'} ({(prediction.probability * 100).toFixed(0)}%)
                            </div>
                          </div>
                        )}
                        <button
                          onClick={() => handleToggleKeeper(listing.id)}
                          className={`px-4 py-2 rounded font-medium transition-colors ${
                            isSelected
                              ? 'bg-green-600 hover:bg-green-700 text-white'
                              : 'bg-gray-600 hover:bg-gray-700 text-white'
                          }`}
                        >
                          {isSelected ? 'Selected' : 'Select'}
                        </button>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">Price:</span>
                        <span className="text-green-400 font-semibold ml-1">
                          ${listing.record_price}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Score:</span>
                        <span className="text-blue-400 font-semibold ml-1">
                          {parseFloat(listing.score).toFixed(2)}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Year:</span>
                        <span className="text-white ml-1">
                          {listing.record.year || 'N/A'}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-400">Condition:</span>
                        <span className="text-white ml-1">
                          {listing.media_condition}
                        </span>
                      </div>
                    </div>
                    
                    <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-400">Label:</span>
                        <span className="text-white ml-1">{listing.record.label}</span>
                      </div>
                      <div>
                        <span className="text-gray-400">Wants/Haves:</span>
                        <span className="text-white ml-1 font-mono">
                          {listing.record.wants}/{listing.record.haves}
                        </span>
                      </div>
                    </div>
                    
                    {listing.record.genres && listing.record.genres.length > 0 && (
                      <div className="mt-2">
                        {listing.record.genres.map((genre, index) => (
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
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="text-center text-gray-400 py-12">
          <h3 className="text-xl font-semibold mb-2">No listings available for evaluation</h3>
          <p className="mb-4">
            All listings have been evaluated, or no data has been collected yet.
          </p>
          <p className="text-sm">
            Try triggering a seller scrape to get new data for evaluation.
          </p>
        </div>
      )}

      {/* Recent Sessions */}
      {modelStats && modelStats.sessions.length > 0 && (
        <div className="mt-8 bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-4">Recent Training Sessions</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left text-gray-400 pb-2">Date</th>
                  <th className="text-left text-gray-400 pb-2">Accuracy</th>
                  <th className="text-left text-gray-400 pb-2">Precision</th>
                  <th className="text-left text-gray-400 pb-2">Samples</th>
                </tr>
              </thead>
              <tbody>
                {modelStats.sessions.slice(0, 5).map((session, index) => (
                  <tr key={index} className="border-b border-gray-700">
                    <td className="py-2 text-white">
                      {new Date(session.session_date).toLocaleDateString()}
                    </td>
                    <td className="py-2 text-white">
                      {(session.accuracy * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 text-white">
                      {(session.precision * 100).toFixed(1)}%
                    </td>
                    <td className="py-2 text-white">
                      {session.num_samples}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Recommender;
