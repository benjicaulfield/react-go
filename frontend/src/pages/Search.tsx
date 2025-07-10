import React, { useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  searchListings,
  setFilters,
  clearFilters,
  clearError,
  fetchGenreAutocomplete,
  fetchConditionAutocomplete,
  clearAutocomplete,
} from '../store/slices/searchSlice';
import type { SearchFilters } from '../types';
import type { SearchState } from '../store/slices/searchSlice';

const Search: React.FC = () => {
  const dispatch = useAppDispatch();
  const {
    listings,
    filters,
    loading,
    error,
    totalCount,
    hasNext,
    hasPrevious,
    genreSuggestions,
    conditionSuggestions,
  } = useAppSelector((state) => state.search) as SearchState;

  const [localFilters, setLocalFilters] = useState<SearchFilters>({});
  const [showGenreSuggestions, setShowGenreSuggestions] = useState(false);
  const [showConditionSuggestions, setShowConditionSuggestions] = useState(false);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleInputChange = (field: keyof SearchFilters, value: string) => {
    setLocalFilters(prev => ({ ...prev, [field]: value }));
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const searchFilters = { ...localFilters, page: 1 };
    dispatch(setFilters(searchFilters));
    dispatch(searchListings(searchFilters));
  };

  const handleClear = () => {
    setLocalFilters({});
    dispatch(clearFilters());
    dispatch(clearAutocomplete());
  };

  const handlePageChange = (page: number) => {
    const searchFilters = { ...filters, page };
    dispatch(setFilters(searchFilters));
    dispatch(searchListings(searchFilters));
  };

  const handleGenreInput = (value: string) => {
    handleInputChange('genre_style', value);
    if (value.length > 2) {
      dispatch(fetchGenreAutocomplete(value));
      setShowGenreSuggestions(true);
    } else {
      setShowGenreSuggestions(false);
    }
  };

  const handleConditionInput = (value: string) => {
    handleInputChange('condition', value);
    if (value.length > 1) {
      dispatch(fetchConditionAutocomplete(value));
      setShowConditionSuggestions(true);
    } else {
      setShowConditionSuggestions(false);
    }
  };


  return (
    <div className="max-w-7xl mx-auto p-5">
      <h1 className="text-3xl text-white mb-5">Advanced Search</h1>

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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Text Search */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Search (Artist, Title, Label)
            </label>
            <input
              type="text"
              value={localFilters.q || ''}
              onChange={(e) => handleInputChange('q', e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="Enter search terms..."
            />
          </div>

          {/* Genre/Style */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Genre/Style
            </label>
            <input
              type="text"
              value={localFilters.genre_style || ''}
              onChange={(e) => handleGenreInput(e.target.value)}
              onBlur={() => setTimeout(() => setShowGenreSuggestions(false), 200)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="Rock, Jazz, Electronic..."
            />
            {showGenreSuggestions && genreSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-gray-700 border border-gray-600 rounded shadow-lg">
                {genreSuggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="px-3 py-2 hover:bg-gray-600 cursor-pointer text-white"
                    onClick={() => {
                      handleInputChange('genre_style', suggestion);
                      setShowGenreSuggestions(false);
                    }}
                  >
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Year Range */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Min Year
              </label>
              <input
                type="number"
                value={localFilters.min_year || ''}
                onChange={(e) => handleInputChange('min_year', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
                placeholder="1960"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Year
              </label>
              <input
                type="number"
                value={localFilters.max_year || ''}
                onChange={(e) => handleInputChange('max_year', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
                placeholder="2024"
              />
            </div>
          </div>

          {/* Price Range */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Min Price ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={localFilters.min_price || ''}
                onChange={(e) => handleInputChange('min_price', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
                placeholder="0.00"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Max Price ($)
              </label>
              <input
                type="number"
                step="0.01"
                value={localFilters.max_price || ''}
                onChange={(e) => handleInputChange('max_price', e.target.value)}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
                placeholder="100.00"
              />
            </div>
          </div>

          {/* Condition */}
          <div className="relative">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Condition
            </label>
            <input
              type="text"
              value={localFilters.condition || ''}
              onChange={(e) => handleConditionInput(e.target.value)}
              onBlur={() => setTimeout(() => setShowConditionSuggestions(false), 200)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="Mint, Near Mint, VG+..."
            />
            {showConditionSuggestions && conditionSuggestions.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-gray-700 border border-gray-600 rounded shadow-lg">
                {conditionSuggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    className="px-3 py-2 hover:bg-gray-600 cursor-pointer text-white"
                    onClick={() => {
                      handleInputChange('condition', suggestion);
                      setShowConditionSuggestions(false);
                    }}
                  >
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Seller */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Seller
            </label>
            <input
              type="text"
              value={localFilters.seller || ''}
              onChange={(e) => handleInputChange('seller', e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="Seller name..."
            />
          </div>

          {/* Sort */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Sort By
            </label>
            <select
              value={localFilters.sort || 'score_desc'}
              onChange={(e) => handleInputChange('sort', e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            >
              <option value="score_desc">Score (High to Low)</option>
              <option value="price_asc">Price (Low to High)</option>
              <option value="price_desc">Price (High to Low)</option>
              <option value="year_asc">Year (Old to New)</option>
              <option value="year_desc">Year (New to Old)</option>
            </select>
          </div>
        </div>

        <div className="flex gap-4 mt-6">
          <button
            type="submit"
            disabled={loading}
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
      </form>

      {/* Results */}
      {totalCount > 0 && (
        <div className="mb-4">
          <p className="text-gray-400">Found {totalCount} results</p>
        </div>
      )}

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
                    <span className="text-gray-400 text-sm">Seller:</span>
                    <span className="text-white text-sm ml-1">{listing.seller.name}</span>
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
          ))}
        </div>
      )}

      {/* Pagination */}
      {(hasNext || hasPrevious) && (
        <div className="flex justify-center gap-4 mt-6">
          <button
            onClick={() => handlePageChange((filters.page || 1) - 1)}
            disabled={!hasPrevious || loading}
            className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white px-4 py-2 rounded transition-colors"
          >
            Previous
          </button>
          <span className="text-gray-400 px-4 py-2">
            Page {filters.page || 1}
          </span>
          <button
            onClick={() => handlePageChange((filters.page || 1) + 1)}
            disabled={!hasNext || loading}
            className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white px-4 py-2 rounded transition-colors"
          >
            Next
          </button>
        </div>
      )}

      {listings.length === 0 && !loading && totalCount === 0 && Object.keys(filters).length > 0 && (
        <div className="text-center text-gray-400 py-8">
          No results found. Try adjusting your search criteria.
        </div>
      )}
    </div>
  );
};

export default Search;
