# Django HTMX to React/TypeScript Conversion Guide

## Overview

This project has been successfully converted from an HTMX-driven Django frontend to a modern React/TypeScript frontend while maintaining the Django backend with DRF API endpoints.

## What Was Accomplished

### 1. Frontend Architecture
- **React 19** with TypeScript for type safety
- **Vite** as the build tool for fast development and optimized builds
- **Tailwind CSS** for consistent styling (matching original design)
- **Redux Toolkit** for global state management
- **React Router** for client-side navigation

### 2. Development Tools Setup
- **ESLint** for code linting with TypeScript support
- **Prettier** for code formatting
- **Babel** for JavaScript/TypeScript transpilation
- **Jest** with React Testing Library for unit testing
- **Husky** configuration for pre-commit hooks (requires git initialization)

### 3. Backend API Conversion
- Converted Django views to DRF API endpoints
- Added new API routes under `/api/` prefix
- Maintained backward compatibility with existing template views
- Enhanced serializers for proper JSON responses

### 4. State Management
- **Dashboard Slice**: Manages dashboard stats, record of the day, and voting
- **Search Slice**: Handles advanced search with filters and autocomplete
- **Recommendation Slice**: Manages ML model predictions and training
- **Seller Slice**: Handles seller-specific operations and scraping

### 5. Component Structure
```
frontend/src/
├── components/
│   └── Layout.tsx          # Main layout with navigation
├── pages/
│   ├── Home.tsx           # Landing page
│   ├── Dashboard.tsx      # Dashboard with metrics and record of the day
│   ├── Search.tsx         # Advanced search with filters
│   ├── BySeller.tsx       # Seller-specific listings
│   ├── SellerTrigger.tsx  # Trigger data scraping
│   └── Recommender.tsx    # ML recommendation interface
├── store/
│   ├── index.ts           # Redux store configuration
│   ├── hooks.ts           # Typed Redux hooks
│   └── slices/            # Redux slices for state management
├── services/
│   └── api.ts             # API service layer
├── types/
│   └── index.ts           # TypeScript type definitions
└── App.tsx                # Main app component with routing
```

## Current Status

### ✅ Completed
- React/TypeScript frontend setup
- Redux state management
- All major page components
- API service layer
- Django API endpoints
- Development tooling (ESLint, Prettier, Jest, Babel)
- Tailwind CSS styling matching original design

### ⚠️ Known Issues (TypeScript Errors)
The following TypeScript errors need to be resolved:

1. **Redux State Type Issues**: The `useAppSelector` hook is not properly inferring types from the store
2. **Implicit Any Types**: Some map functions have implicit `any` parameters
3. **Module Resolution**: Some import paths may need adjustment

### 🔧 Next Steps to Complete

1. **Fix TypeScript Issues**:
   ```bash
   cd frontend
   npm run lint:fix
   ```

2. **Initialize Git Repository** (for Husky pre-commit hooks):
   ```bash
   git init
   npm run prepare
   ```

3. **Test API Connectivity**:
   - Start Django backend: `python manage.py runserver`
   - Ensure CORS is properly configured
   - Test API endpoints from React frontend

4. **Update Django Settings**:
   Add React development server to CORS allowed origins:
   ```python
   CORS_ALLOWED_ORIGINS = [
       "http://localhost:3000",
       "http://localhost:5173",  # Vite dev server
   ]
   ```

## Running the Application

### Development Mode

1. **Start Django Backend**:
   ```bash
   python manage.py runserver
   ```

2. **Start React Frontend**:
   ```bash
   cd frontend
   npm run dev
   ```

3. **Access Applications**:
   - React Frontend: http://localhost:5173/
   - Django Backend: http://localhost:8000/
   - Django Admin: http://localhost:8000/admin/

### Production Build

1. **Build React Frontend**:
   ```bash
   cd frontend
   npm run build
   ```

2. **Serve Static Files**:
   Configure Django to serve the built React files from `frontend/dist/`

## Key Features Preserved

### 1. Dashboard
- Real-time metrics display
- Thermodynamic record selection
- Interactive voting system
- Performance analytics

### 2. Advanced Search
- Multi-field text search
- Genre/style autocomplete
- Price and year range filters
- Condition and seller filtering
- Pagination support

### 3. Recommendation System
- ML model training interface
- Prediction display
- Batch evaluation
- Performance tracking

### 4. Seller Management
- Inventory scraping
- Seller-specific browsing
- Progress tracking

## API Endpoints

### New API Routes (for React)
- `GET /api/dashboard/` - Dashboard statistics
- `GET /api/search/results/` - Search listings
- `POST /api/data/<seller>/` - Trigger seller scrape
- `GET /api/recommendation-predictions/` - Get ML predictions
- `POST /api/submit-scoring-selections/` - Submit training data
- `GET /api/model-performance-stats/` - Model performance metrics

### Legacy Routes (maintained for compatibility)
- All original Django template routes remain functional

## Styling

The React frontend maintains the original dark theme with:
- Black background (`bg-black`)
- Gray color palette for cards and borders
- Monospace font family
- Consistent spacing and layout
- Responsive design with Tailwind CSS

## Testing

Run tests with:
```bash
cd frontend
npm test                # Run tests once
npm run test:watch      # Run tests in watch mode
npm run test:coverage   # Run tests with coverage report
```

## Code Quality

Maintain code quality with:
```bash
cd frontend
npm run lint            # Check for linting errors
npm run lint:fix        # Fix auto-fixable linting errors
npm run format          # Format code with Prettier
npm run format:check    # Check if code is properly formatted
```

## Deployment Considerations

1. **Environment Variables**: Update API base URL for production
2. **Static File Serving**: Configure Django to serve React build files
3. **CORS Configuration**: Update allowed origins for production domain
4. **Build Optimization**: Ensure proper minification and chunking
5. **Error Handling**: Implement proper error boundaries and fallbacks

## Migration Benefits

- **Modern Development Experience**: Hot reloading, TypeScript, modern tooling
- **Better Performance**: Client-side routing, optimized bundles, code splitting
- **Improved Maintainability**: Type safety, component-based architecture
- **Enhanced User Experience**: Faster navigation, better interactivity
- **Scalability**: Easier to add new features and maintain codebase
