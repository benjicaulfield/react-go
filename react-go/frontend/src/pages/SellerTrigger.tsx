import React, { useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  triggerSellerScrape,
  clearError,
  clearScrapeMessage,
} from '../store/slices/sellerSlice';

const SellerTrigger: React.FC = () => {
  const dispatch = useAppDispatch();
  const { scraping, error, scrapeMessage } = useAppSelector(
    (state) => state.seller
  );

  const [sellerName, setSellerName] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (sellerName.trim()) {
      dispatch(triggerSellerScrape(sellerName.trim()));
    }
  };

  const handleClear = () => {
    setSellerName('');
    dispatch(clearScrapeMessage());
    dispatch(clearError());
  };

  return (
    <div className="max-w-4xl mx-auto p-5">
      <h1 className="text-3xl text-white mb-5">Seller Data Trigger</h1>
      
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-6">
        <p className="text-gray-300 mb-4">
          Use this tool to trigger data collection from Discogs sellers. This will scrape the seller's 
          inventory and add it to your local database for analysis and recommendations.
        </p>
        
        <div className="bg-yellow-900 border border-yellow-700 text-yellow-100 px-4 py-3 rounded mb-4">
          <p className="text-sm">
            <strong>Note:</strong> This process may take several minutes depending on the size of the seller's inventory. 
            Please be patient and avoid triggering multiple scrapes simultaneously.
          </p>
        </div>
      </div>

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

      {scrapeMessage && (
        <div className="bg-green-900 border border-green-700 text-green-100 px-4 py-3 rounded mb-4">
          {scrapeMessage}
          <button
            onClick={() => dispatch(clearScrapeMessage())}
            className="ml-2 text-green-300 hover:text-green-100"
          >
            ×
          </button>
        </div>
      )}

      {/* Trigger Form */}
      <form onSubmit={handleSubmit} className="bg-gray-800 p-6 rounded-lg border border-gray-700 mb-6">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Seller Name
          </label>
          <input
            type="text"
            value={sellerName}
            onChange={(e) => setSellerName(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            placeholder="Enter Discogs seller username..."
            required
            disabled={scraping}
          />
          <p className="text-xs text-gray-400 mt-1">
            Enter the exact Discogs username of the seller you want to scrape.
          </p>
        </div>

        <div className="flex gap-4">
          <button
            type="submit"
            disabled={scraping || !sellerName.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            {scraping ? 'Scraping...' : 'Trigger Scrape'}
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={scraping}
            className="bg-gray-600 hover:bg-gray-700 disabled:bg-gray-800 text-white px-6 py-2 rounded font-medium transition-colors"
          >
            Clear
          </button>
        </div>
      </form>

      {/* Instructions */}
      <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h2 className="text-xl font-bold text-white mb-4">How it works</h2>
        <div className="space-y-3 text-gray-300">
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">1.</span>
            <p>Enter the Discogs username of the seller you want to analyze.</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">2.</span>
            <p>The system will connect to Discogs and retrieve the seller's current inventory.</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">3.</span>
            <p>Each record will be processed and scored based on various factors including wants/haves ratio, price, and condition.</p>
          </div>
          <div className="flex items-start">
            <span className="text-blue-400 font-bold mr-3">4.</span>
            <p>The data will be stored in your local database for searching, analysis, and machine learning recommendations.</p>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-700">
          <h3 className="text-lg font-semibold text-white mb-2">After scraping:</h3>
          <ul className="text-gray-300 space-y-1">
            <li>• Use the "By Seller" page to browse the collected listings</li>
            <li>• Use the "Search" page to find specific records with advanced filters</li>
            <li>• Use the "Recommender" to train the ML model on the new data</li>
            <li>• Check the "Dashboard" for updated statistics and recommendations</li>
          </ul>
        </div>
      </div>

      {scraping && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-6 rounded-lg border border-gray-700 max-w-md">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <h3 className="text-lg font-semibold text-white mb-2">Scraping in Progress</h3>
              <p className="text-gray-300">
                Collecting data from seller "{sellerName}". This may take several minutes...
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SellerTrigger;
