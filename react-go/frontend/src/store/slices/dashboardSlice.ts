import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { DashboardStats, Listing } from '../../types';
import { apiService } from '../../services/api';

interface DashboardState {
  stats: DashboardStats | null;
  listings: Listing[];
  loading: boolean;
  error: string | null;
  refreshingRecord: boolean;
}

const initialState: DashboardState = {
  stats: null,
  listings: [],
  loading: false,
  error: null,
  refreshingRecord: false,
};

// Async thunks
export const fetchDashboardStats = createAsyncThunk(
  'dashboard/fetchStats',
  async () => {
    return await apiService.getDashboardStats();
  }
);

export const fetchDashboardListings = createAsyncThunk(
  'dashboard/fetchListings',
  async () => {
    return await apiService.getDashboardListings();
  }
);

export const refreshRecordOfTheDay = createAsyncThunk(
  'dashboard/refreshRecord',
  async () => {
    return await apiService.refreshRecordOfTheDay();
  }
);

export const voteRecordOfTheDay = createAsyncThunk(
  'dashboard/voteRecord',
  async ({ recordId, desirability, novelty }: { recordId: number; desirability: number; novelty: number }) => {
    return await apiService.voteRecordOfTheDay(recordId, desirability, novelty);
  }
);

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch stats
      .addCase(fetchDashboardStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardStats.fulfilled, (state, action) => {
        state.loading = false;
        state.stats = action.payload;
      })
      .addCase(fetchDashboardStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch dashboard stats';
      })
      // Fetch listings
      .addCase(fetchDashboardListings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardListings.fulfilled, (state, action) => {
        state.loading = false;
        state.listings = action.payload;
      })
      .addCase(fetchDashboardListings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch dashboard listings';
      })
      // Refresh record of the day
      .addCase(refreshRecordOfTheDay.pending, (state) => {
        state.refreshingRecord = true;
        state.error = null;
      })
      .addCase(refreshRecordOfTheDay.fulfilled, (state) => {
        state.refreshingRecord = false;
      })
      .addCase(refreshRecordOfTheDay.rejected, (state, action) => {
        state.refreshingRecord = false;
        state.error = action.error.message || 'Failed to refresh record of the day';
      })
      // Vote record of the day
      .addCase(voteRecordOfTheDay.pending, (state) => {
        state.error = null;
      })
      .addCase(voteRecordOfTheDay.fulfilled, () => {
        // Vote submitted successfully - could update UI state here if needed
      })
      .addCase(voteRecordOfTheDay.rejected, (state, action) => {
        state.error = action.error.message || 'Failed to submit vote';
      });
  },
});

export const { clearError } = dashboardSlice.actions;
export default dashboardSlice.reducer;
