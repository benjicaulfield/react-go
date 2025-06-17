import React from 'react';
import { Link } from 'react-router-dom';

const Home: React.FC = () => {
  return (
    <div className="max-w-7xl mx-auto p-5">
      <h1 className="text-3xl text-white mb-8">LongPlaying</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Link
          to="/dashboard"
          className="bg-gray-800 p-6 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <h2 className="text-xl font-bold text-white mb-3">Dashboard</h2>
          <p className="text-gray-400">
            View your collection statistics, model performance, and today's thermodynamically selected record.
          </p>
        </Link>

        <Link
          to="/search"
          className="bg-gray-800 p-6 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <h2 className="text-xl font-bold text-white mb-3">Advanced Search</h2>
          <p className="text-gray-400">
            Search through your record listings with advanced filters for genre, price, condition, and more.
          </p>
        </Link>

        <Link
          to="/by-seller"
          className="bg-gray-800 p-6 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <h2 className="text-xl font-bold text-white mb-3">By Seller</h2>
          <p className="text-gray-400">
            Browse records organized by seller to find specific collections and inventories.
          </p>
        </Link>

        <Link
          to="/seller-trigger"
          className="bg-gray-800 p-6 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <h2 className="text-xl font-bold text-white mb-3">Seller Trigger</h2>
          <p className="text-gray-400">
            Trigger data collection from Discogs sellers to update your local inventory.
          </p>
        </Link>

        <Link
          to="/recommender"
          className="bg-gray-800 p-6 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
        >
          <h2 className="text-xl font-bold text-white mb-3">Recommender</h2>
          <p className="text-gray-400">
            Train the machine learning model by rating records and get personalized recommendations.
          </p>
        </Link>

        <div className="bg-gray-800 p-6 rounded-lg border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-3">About</h2>
          <p className="text-gray-400">
            A sophisticated record collection management system with machine learning recommendations 
            and thermodynamic selection algorithms.
          </p>
        </div>
      </div>

      <div className="mt-12 bg-gray-800 p-6 rounded-lg border border-gray-700">
        <h2 className="text-2xl font-bold text-white mb-4">Features</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">🤖 Machine Learning</h3>
            <p className="text-gray-400 text-sm">
              Advanced recommendation system that learns from your preferences to suggest records you'll love.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">🔬 Thermodynamic Selection</h3>
            <p className="text-gray-400 text-sm">
              Daily record selection using thermodynamic principles to balance exploitation and exploration.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">🔍 Advanced Search</h3>
            <p className="text-gray-400 text-sm">
              Powerful search capabilities with autocomplete and filtering across multiple dimensions.
            </p>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white mb-2">📊 Analytics</h3>
            <p className="text-gray-400 text-sm">
              Comprehensive analytics and performance metrics for your collection and model accuracy.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Home;
