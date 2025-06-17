import { configureStore } from '@reduxjs/toolkit';
import dashboardReducer from './slices/dashboardSlice.ts';
import searchReducer from './slices/searchSlice.ts';
import recommendationReducer from './slices/recommendationSlice.ts';
import sellerReducer from './slices/sellerSlice.ts';

export const store = configureStore({
  reducer: {
    dashboard: dashboardReducer,
    search: searchReducer,
    recommendation: recommendationReducer,
    seller: sellerReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
