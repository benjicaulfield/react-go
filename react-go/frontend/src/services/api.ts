import type {
  Listing,
  Record,
  SearchFilters,
  DashboardStats,
  RecommendationPrediction,
  PaginatedResponse,
} from '../types';

const API_BASE_URL = 'http://localhost:8000';

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Dashboard endpoints
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>('/dashboard/');
  }

  async getDashboardListings(): Promise<Listing[]> {
    return this.request<Listing[]>('/api/dashboard/listings/');
  }

  async refreshRecordOfTheDay(): Promise<{ message: string }> {
    return this.request<{ message: string }>('/api/refresh-record-of-the-day/', {
      method: 'POST',
    });
  }

  // Search endpoints
  async searchListings(filters: SearchFilters): Promise<PaginatedResponse<Listing>> {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        params.append(key, value.toString());
      }
    });

    return this.request<PaginatedResponse<Listing>>(`/search/results/?${params}`);
  }

  async getGenreAutocomplete(term: string): Promise<string[]> {
    return this.request<string[]>(`/autocomplete/genre/?term=${encodeURIComponent(term)}`);
  }

  async getConditionAutocomplete(term: string): Promise<string[]> {
    return this.request<string[]>(`/autocomplete/condition/?term=${encodeURIComponent(term)}`);
  }

  async getStylesAutocomplete(term: string): Promise<string[]> {
    return this.request<string[]>(`/autocomplete/styles/?term=${encodeURIComponent(term)}`);
  }

  // Seller endpoints
  async searchSellerListings(sellerName: string): Promise<Listing[]> {
    return this.request<Listing[]>('/by-seller/search/', {
      method: 'POST',
      body: JSON.stringify({ seller: sellerName }),
    });
  }

  async triggerSellerScrape(sellerName: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/data/${sellerName}`, {
      method: 'POST',
    });
  }

  async getRecordsBySeller(sellerName: string): Promise<Record[]> {
    return this.request<Record[]>(`/records/seller/${sellerName}/`);
  }

  // Recommendation endpoints
  async getRecommendationPredictions(listingIds: number[]): Promise<RecommendationPrediction[]> {
    const params = new URLSearchParams();
    listingIds.forEach(id => params.append('listing_ids', id.toString()));
    
    return this.request<RecommendationPrediction[]>(`/recommendation-predictions/?${params}`);
  }

  async submitRecommendations(listingIds: number[], keeperIds: number[]): Promise<{ success: boolean }> {
    const formData = new FormData();
    listingIds.forEach(id => formData.append('listing_ids', id.toString()));
    keeperIds.forEach(id => formData.append('keeper_ids', id.toString()));

    return this.request<{ success: boolean }>('/submit-scoring-selections/', {
      method: 'POST',
      headers: {}, // Remove Content-Type to let browser set it for FormData
      body: formData,
    });
  }

  async getModelPerformanceStats(): Promise<{
    accuracy: number;
    total_sessions: number;
    sessions: Array<{
      session_date: string;
      accuracy: number;
      precision: number;
      num_samples: number;
    }>;
  }> {
    return this.request('/model-performance-stats/');
  }

  // Scoring endpoints
  async getTuneScoringListings(sellerName: string): Promise<Listing[]> {
    return this.request<Listing[]>('/tune-scoring', {
      method: 'POST',
      body: JSON.stringify({ seller: sellerName }),
    });
  }

  // Export endpoints
  async exportListingsCsv(): Promise<Blob> {
    const response = await fetch(`${API_BASE_URL}/export-listings`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return response.blob();
  }

  // Wantlist endpoints
  async addToWantlist(recordId: string): Promise<{ message: string }> {
    const formData = new FormData();
    formData.append('record_id', recordId);

    return this.request<{ message: string }>('/add-to-wantlist/', {
      method: 'POST',
      headers: {}, // Remove Content-Type for FormData
      body: formData,
    });
  }

  // Record of the Day voting
  async voteRecordOfTheDay(
    recordId: number,
    desirability: number,
    novelty: number
  ): Promise<{ message: string }> {
    const formData = new FormData();
    formData.append('desirability', desirability.toString());
    formData.append('novelty', novelty.toString());

    return this.request<{ message: string }>(`/vote-record-of-the-day/${recordId}/`, {
      method: 'POST',
      headers: {}, // Remove Content-Type for FormData
      body: formData,
    });
  }
}

export const apiService = new ApiService();
