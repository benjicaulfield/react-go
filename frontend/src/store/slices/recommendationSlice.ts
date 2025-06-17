import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { Listing, RecommendationPrediction } from '../../types';
import { apiService } from '../../services/api';

interface RecommendationState {
  listings: Listing[];
  predictions: RecommendationPrediction[];
  selectedKeepers: number[];
  loading: boolean;
  submitting: boolean;
  error: string | null;
  totalUnevaluated: number;
  modelStats: {
    accuracy: number;
    total_sessions: number;
    sessions: Array<{
      session_date: string;
      accuracy: number;
      precision: number;
      num_samples: number;
    }>;
  } | null;
}

const initialState: RecommendationState = {
  listings: [],
  predictions: [],
  selectedKeepers: [],
  loading: false,
  submitting: false,
  error: null,
  totalUnevaluated: 0,
  modelStats: null,
};

// Async thunks
export const fetchRecommendationPredictions = createAsyncThunk(
  'recommendation/fetchPredictions',
  async (listingIds: number[]) => {
    return await apiService.getRecommendationPredictions(listingIds);
  }
);

export const submitRecommendations = createAsyncThunk(
  'recommendation/submitRecommendations',
  async ({ listingIds, keeperIds }: { listingIds: number[]; keeperIds: number[] }) => {
    return await apiService.submitRecommendations(listingIds, keeperIds);
  }
);

export const fetchModelPerformanceStats = createAsyncThunk(
  'recommendation/fetchModelStats',
  async () => {
    return await apiService.getModelPerformanceStats();
  }
);

const recommendationSlice = createSlice({
  name: 'recommendation',
  initialState,
  reducers: {
    setListings: (state, action) => {
      state.listings = action.payload.listings;
      state.totalUnevaluated = action.payload.totalUnevaluated || 0;
    },
    toggleKeeper: (state, action) => {
      const listingId = action.payload;
      if (state.selectedKeepers.includes(listingId)) {
        state.selectedKeepers = state.selectedKeepers.filter(id => id !== listingId);
      } else {
        state.selectedKeepers.push(listingId);
      }
    },
    clearKeepers: (state) => {
      state.selectedKeepers = [];
    },
    clearError: (state) => {
      state.error = null;
    },
    resetSession: (state) => {
      state.listings = [];
      state.predictions = [];
      state.selectedKeepers = [];
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch predictions
      .addCase(fetchRecommendationPredictions.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecommendationPredictions.fulfilled, (state, action) => {
        state.loading = false;
        state.predictions = action.payload;
      })
      .addCase(fetchRecommendationPredictions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch predictions';
      })
      // Submit recommendations
      .addCase(submitRecommendations.pending, (state) => {
        state.submitting = true;
        state.error = null;
      })
      .addCase(submitRecommendations.fulfilled, (state) => {
        state.submitting = false;
        state.selectedKeepers = [];
        // Reset for next batch
        state.listings = [];
        state.predictions = [];
      })
      .addCase(submitRecommendations.rejected, (state, action) => {
        state.submitting = false;
        state.error = action.error.message || 'Failed to submit recommendations';
      })
      // Fetch model stats
      .addCase(fetchModelPerformanceStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchModelPerformanceStats.fulfilled, (state, action) => {
        state.loading = false;
        state.modelStats = action.payload;
      })
      .addCase(fetchModelPerformanceStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch model stats';
      });
  },
});

export const { 
  setListings, 
  toggleKeeper, 
  clearKeepers, 
  clearError, 
  resetSession 
} = recommendationSlice.actions;

export default recommendationSlice.reducer;
