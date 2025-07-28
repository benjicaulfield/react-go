import React, { useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  searchSellerListings,
  setCurrentSeller,
  clearError,
  clearListings,
  type SellerState,
} from '../store/slices/sellerSlice';

const BySeller: React.FC = () => {
  const dispatch = useAppDispatch();
  const seller = useAppSelector((state) => state.seller) as SellerState;
  const { listings, loading, error, currentSeller } = seller;

  const [sellerName, setSellerName] = useState('');

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (sellerName.trim()) {
      dispatch(setCurrentSeller(sellerName.trim()));
      dispatch(searchSellerListings(sellerName.trim()));
    }
  };

  const handleClear = () => {
    setSellerName('');
    dispatch(setCurrentSeller(null));
    dispatch(clearListings());
  };

  return (
    <div className="max-w-7xl mx-auto p-5">
      <h1 className="text-3xl text-white mb-5">Browse by Seller</h1>

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

      {/* Search Form */}
      <form onSubmit={handleSearch} className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-6">
        <div className="flex gap-4">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Seller Name
            </label>
            <input
              type="text"
              value={sellerName}
              onChange={(e) => setSellerName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="Enter seller name..."
              required
            />
          </div>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={loading || !sellerName.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-6 py-2 rounded font-medium transition-colors"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
            <button
              type="button"
              onClick={handleClear}
              className="bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded font-medium transition-colors"
            >
              Clear
            </button>
          </div>
        </div>
      </form>

      {/* Current Seller */}
      {currentSeller && (
        <div className="mb-4">
          <h2 className="text-xl text-white mb-2">
            Listings from: <span className="text-blue-400">{currentSeller}</span>
          </h2>
          <p className="text-gray-400">Found {listings.length} listings</p>
        </div>
      )}

      {/* Results */}
      {listings.length > 0 && (
        <div className="space-y-4">
          {listings.map((listing) => (
            <div key={listing.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-white mb-1">
                    {listing.record.artist} - {listing.record.title}
                  </h3>
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
                  <div className="mt-2">
                    <span className="text-gray-400 text-sm">Label:</span>
                    <span className="text-white text-sm ml-1">{listing.record.label}</span>
                  </div>
                  <div className="mt-1">
                    <span className="text-gray-400 text-sm">Format:</span>
                    <span className="text-white text-sm ml-1">{listing.record.format}</span>
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
                <div className="ml-4">
                  <div className="text-right">
                    <div className="text-sm text-gray-400">Wants/Haves</div>
                    <div className="text-white font-mono">
                      {listing.record.wants}/{listing.record.haves}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {listings.length === 0 && !loading && currentSeller && (
        <div className="text-center text-gray-400 py-8">
          No listings found for seller "{currentSeller}". 
          <br />
          Try triggering a scrape for this seller first.
        </div>
      )}

      {!currentSeller && (
        <div className="text-center text-gray-400 py-8">
          Enter a seller name to browse their listings.
        </div>
      )}
    </div>
  );
};

export default BySeller;
