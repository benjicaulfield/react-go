import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import type { Listing, SearchFilters } from '../../types';
import { apiService } from '../../services/api';

export interface SearchState {
  listings: Listing[];
  filters: SearchFilters;
  loading: boolean;
  error: string | null;
  totalCount: number;
  currentPage: number;
  hasNext: boolean;
  hasPrevious: boolean;
  autocompleteLoading: boolean;
  genreSuggestions: string[];
  conditionSuggestions: string[];
  stylesSuggestions: string[];
}

const initialState: SearchState = {
  listings: [],
  filters: {},
  loading: false,
  error: null,
  totalCount: 0,
  currentPage: 1,
  hasNext: false,
  hasPrevious: false,
  autocompleteLoading: false,
  genreSuggestions: [],
  conditionSuggestions: [],
  stylesSuggestions: [],
};

// Async thunks
export const searchListings = createAsyncThunk(
  'search/searchListings',
  async (filters: SearchFilters) => {
    return await apiService.searchListings(filters);
  }
);

export const fetchGenreAutocomplete = createAsyncThunk(
  'search/fetchGenreAutocomplete',
  async (term: string) => {
    return await apiService.getGenreAutocomplete(term);
  }
);

export const fetchConditionAutocomplete = createAsyncThunk(
  'search/fetchConditionAutocomplete',
  async (term: string) => {
    return await apiService.getConditionAutocomplete(term);
  }
);

export const fetchStylesAutocomplete = createAsyncThunk(
  'search/fetchStylesAutocomplete',
  async (term: string) => {
    return await apiService.getStylesAutocomplete(term);
  }
);

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = {};
      state.listings = [];
      state.totalCount = 0;
      state.currentPage = 1;
      state.hasNext = false;
      state.hasPrevious = false;
    },
    clearError: (state) => {
      state.error = null;
    },
    clearAutocomplete: (state) => {
      state.genreSuggestions = [];
      state.conditionSuggestions = [];
      state.stylesSuggestions = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // Search listings
      .addCase(searchListings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(searchListings.fulfilled, (state, action) => {
        state.loading = false;
        state.listings = action.payload.results;
        state.totalCount = action.payload.count;
        state.hasNext = !!action.payload.next;
        state.hasPrevious = !!action.payload.previous;
      })
      .addCase(searchListings.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to search listings';
      })
      // Genre autocomplete
      .addCase(fetchGenreAutocomplete.pending, (state) => {
        state.autocompleteLoading = true;
      })
      .addCase(fetchGenreAutocomplete.fulfilled, (state, action) => {
        state.autocompleteLoading = false;
        state.genreSuggestions = action.payload;
      })
      .addCase(fetchGenreAutocomplete.rejected, (state) => {
        state.autocompleteLoading = false;
        state.genreSuggestions = [];
      })
      // Condition autocomplete
      .addCase(fetchConditionAutocomplete.pending, (state) => {
        state.autocompleteLoading = true;
      })
      .addCase(fetchConditionAutocomplete.fulfilled, (state, action) => {
        state.autocompleteLoading = false;
        state.conditionSuggestions = action.payload;
      })
      .addCase(fetchConditionAutocomplete.rejected, (state) => {
        state.autocompleteLoading = false;
        state.conditionSuggestions = [];
      })
      // Styles autocomplete
      .addCase(fetchStylesAutocomplete.pending, (state) => {
        state.autocompleteLoading = true;
      })
      .addCase(fetchStylesAutocomplete.fulfilled, (state, action) => {
        state.autocompleteLoading = false;
        state.stylesSuggestions = action.payload;
      })
      .addCase(fetchStylesAutocomplete.rejected, (state) => {
        state.autocompleteLoading = false;
        state.stylesSuggestions = [];
      });
  },
});

export const { setFilters, clearFilters, clearError, clearAutocomplete } = searchSlice.actions;
export default searchSlice.reducer;
