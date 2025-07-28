import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="bg-black font-mono text-gray-300 text-lg min-h-screen">
      <header className="w-full px-5 py-3 bg-white text-black fixed top-0 left-0 flex justify-between items-center z-50">
        <div className="flex gap-4">
          <Link to="/" className="text-black font-bold">
            YOUR NAME HERE
          </Link>
        </div>
      </header>
      
      <nav className="bg-gray-800 p-4 mt-12">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <Link to="/" className="text-white text-lg font-bold">
            Home
          </Link>
          <div className="flex space-x-4">
            <Link
              to="/dashboard"
              className={`${
                isActive('/dashboard')
                  ? 'text-white'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              Dashboard
            </Link>
            <Link
              to="/by-seller"
              className={`${
                isActive('/by-seller')
                  ? 'text-white'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              By Seller
            </Link>
            <Link
              to="/seller-trigger"
              className={`${
                isActive('/seller-trigger')
                  ? 'text-white'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              Trigger
            </Link>
            <Link
              to="/search"
              className={`${
                isActive('/search')
                  ? 'text-white'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              Search
            </Link>
            <Link
              to="/recommender"
              className={`${
                isActive('/recommender')
                  ? 'text-white'
                  : 'text-gray-300 hover:text-white'
              }`}
            >
              Recommender
            </Link>
          </div>
        </div>
      </nav>
      
      <main className="max-w-7xl mx-auto px-4 pt-20">
        {children}
      </main>
    </div>
  );
};

export default Layout;
