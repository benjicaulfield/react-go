import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { Listing, Record } from '../../types';
import { apiService } from '../../services/api';

export interface SellerState {
  listings: Listing[];
  records: Record[];
  loading: boolean;
  scraping: boolean;
  error: string | null;
  currentSeller: string | null;
  scrapeMessage: string | null;
}

const initialState: SellerState = {
  listings: [],
  records: [],
  loading: false,
  scraping: false,
  error: null,
  currentSeller: null,
  scrapeMessage: null,
};

// Async thunks
export const searchSellerListings = createAsyncThunk(
  'seller/searchListings',
  async (sellerName: string) => {
    return await apiService.searchSellerListings(sellerName);
  }
);

export const triggerSellerScrape = createAsyncThunk(
  'seller/triggerScrape',
  async (sellerName: string) => {
    return await apiService.triggerSellerScrape(sellerName);
  }
);

export const fetchRecordsBySeller = createAsyncThunk(
  'seller/fetchRecords',
  async (sellerName: string) => {
    return await apiService.getRecordsBySeller(sellerName);
  }
);

export const getTuneScoringListings = createAsyncThunk(
  'seller/getTuneScoringListings',
  async (sellerName: string) => {
    return await apiService.getTuneScoringListings(sellerName);
  }
);

const sellerSlice = createSlice({
  name: 'seller',
  initialState,
  reducers: {
    setCurrentSeller: (state, action) => {
      state.currentSeller = action.payload;
    },
    clearListings: (state) => {
      state.listings = [];
    },
    clearRecords: (state) => {
      state.records = [];
    },
    clearError: (state) => {
      state.error = null;
    },
    clearScrapeMessage: (state) => {
      state.scrapeMessage = null;
    },
    resetSeller: (state) => {
      state.listings = [];
      state.records = [];
      state.currentSeller = null;
      state.error = null;
      state.scrapeMessage = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Search seller listings
      .addCase(searchSellerListings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(searchSellerListings.fulfilled, (state, action) => {
        state.loading = false;
        state.listings = action.payload;
      })
      .addCase(searchSellerListings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to search seller listings';
      })
      // Trigger seller scrape
      .addCase(triggerSellerScrape.pending, (state) => {
        state.scraping = true;
        state.error = null;
        state.scrapeMessage = null;
      })
      .addCase(triggerSellerScrape.fulfilled, (state, action) => {
        state.scraping = false;
        state.scrapeMessage = action.payload.message;
      })
      .addCase(triggerSellerScrape.rejected, (state, action) => {
        state.scraping = false;
        state.error = action.error.message || 'Failed to trigger seller scrape';
      })
      // Fetch records by seller
      .addCase(fetchRecordsBySeller.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecordsBySeller.fulfilled, (state, action) => {
        state.loading = false;
        state.records = action.payload;
      })
      .addCase(fetchRecordsBySeller.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch records by seller';
      })
      // Get tune scoring listings
      .addCase(getTuneScoringListings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(getTuneScoringListings.fulfilled, (state, action) => {
        state.loading = false;
        state.listings = action.payload;
      })
      .addCase(getTuneScoringListings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch tune scoring listings';
      });
  },
});

export const {
  setCurrentSeller,
  clearListings,
  clearRecords,
  clearError,
  clearScrapeMessage,
  resetSeller,
} = sellerSlice.actions;

export default sellerSlice.reducer;
