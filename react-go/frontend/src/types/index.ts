export interface Record {
  id: number;
  discogs_id: string;
  artist: string;
  title: string;
  format: string;
  label: string;
  catno: string | null;
  wants: number;
  haves: number;
  added: string;
  genres: string[];
  styles: string[];
  suggested_price: string;
  year: number | null;
}

export interface Seller {
  id: number;
  name: string;
  currency: string;
}

export interface Listing {
  id: number;
  seller: Seller;
  record: Record;
  record_price: string;
  media_condition: string;
  score: string;
  kept: boolean;
  evaluated: boolean;
  predicted_keeper: boolean;
}

export interface RecommendationModel {
  id: number;
  created_at: string;
  updated_at: string;
  last_accuracy: number;
  model_version: string;
}

export interface RecommendationMetrics {
  id: number;
  session_date: string;
  accuracy: number;
  precision: number;
  num_samples: number;
  notes: string;
}

export interface RecordOfTheDay {
  id: number;
  date: string;
  listing: Listing;
  created_at: string;
  model_score: number;
  entropy_measure: number;
  system_temperature: number;
  utility_term: number | null;
  entropy_term: number | null;
  free_energy: number | null;
  selection_probability: number | null;
  total_candidates: number | null;
  cluster_count: number | null;
  selection_method: string;
  desirability_votes: number[];
  novelty_votes: number[];
  average_desirability: number;
  average_novelty: number;
}

export interface DashboardStats {
  num_records: number;
  num_listings: number;
  accuracy: number;
  unevaluated: number;
  record_of_the_day: Listing | null;
  record_of_the_day_obj: RecordOfTheDay | null;
  breakdown: ThermodynamicBreakdown;
}

export interface ThermodynamicBreakdown {
  model_score?: number;
  entropy_measure?: number;
  system_temperature?: number;
  utility_term?: number;
  entropy_term?: number;
  free_energy?: number;
  selection_probability?: number;
  total_candidates?: number;
  cluster_count?: number;
  selection_method?: string;
  error?: string;
}

export interface SearchFilters {
  q?: string;
  genre_style?: string;
  min_year?: string;
  max_year?: string;
  min_price?: string;
  max_price?: string;
  condition?: string;
  seller?: string;
  sort?: string;
  page?: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface RecommendationPrediction {
  id: number;
  prediction: boolean;
  probability: number;
}

export interface ApiError {
  error: string;
  details?: string;
}
