export type ShoppingRequestConstraints = {
  category?: string | null;
  use_case?: string | null;
  size_value?: string | null;
  size_system?: string | null;
  preferred_brand?: string | null;
  color?: string | null;
  max_price?: number | null;
  max_price_currency?: string | null;
  attributes?: Record<string, unknown> | null;
};

export type ShoppingRequestConstraintDraft = {
  category: string;
  use_case: string;
  size_value: string;
  size_system: string;
  preferred_brand: string;
  color: string;
  max_price: string;
  max_price_currency: string;
};

export type ShoppingRequest = {
  id: string;
  raw_text: string;
  status: string;
  locale: string;
  display_currency?: string | null;
  budget_amount?: number | null;
  constraints?: ShoppingRequestConstraints | null;
  editable: boolean;
  created_at: string;
};

export type Category = {
  id: string;
  parent_id?: string | null;
  slug: string;
  name: string;
};

export type Product = {
  id: string;
  brand_id?: string | null;
  category_id: string;
  model?: string | null;
  name: string;
  sku?: string | null;
  image_url?: string | null;
  attributes?: Record<string, unknown> | null;
};

export type Recommendation = {
  id: string;
  product: Product;
  best_offer_id?: string | null;
  score: number;
  reason: string;
  created_at: string;
};

export type OfferAvailability = {
  id: string;
  variant_id?: string | null;
  size_value?: string | null;
  size_system?: string | null;
  color?: string | null;
  in_stock: boolean;
  stock_count?: number | null;
};

export type Offer = {
  id: string;
  product_id: string;
  store_id: string;
  external_id?: string | null;
  product_url: string;
  source_price: number;
  source_old_price?: number | null;
  source_currency: string;
  eur_price: number;
  eur_old_price?: number | null;
  fx_rate_to_eur?: number | null;
  discount_percent?: number | null;
  availability: string;
  last_seen_at: string;
  availability_items: OfferAvailability[];
  is_historical_min: boolean;
  is_lowest_10_percent_365d: boolean;
};

export type PriceAnalytics = {
  eur_min_30d?: number | null;
  eur_min_90d?: number | null;
  eur_min_180d?: number | null;
  eur_min_365d?: number | null;
  eur_min_all_time?: number | null;
  eur_avg_365d?: number | null;
  eur_lowest_10pct_365d_threshold?: number | null;
  calculated_at?: string | null;
};

export type PricePoint = {
  captured_at: string;
  source_price: number;
  source_old_price?: number | null;
  source_currency: string;
  eur_price: number;
  eur_old_price?: number | null;
  fx_rate_to_eur?: number | null;
  discount_percent?: number | null;
  availability: string;
  store_id: string;
};

export type PriceHistory = {
  product_id: string;
  period: string;
  points: PricePoint[];
  analytics?: PriceAnalytics | null;
};

export type Notification = {
  id: string;
  user_id: string;
  watchlist_id?: string | null;
  shopping_request_id?: string | null;
  offer_id?: string | null;
  type: string;
  status: string;
  message: string;
  dedupe_key: string;
  sent_at?: string | null;
  created_at: string;
};

export type Watchlist = {
  id: string;
  type: string;
  source_request_id?: string | null;
  active: boolean;
  archived: boolean;
  model?: string | null;
  category?: string | null;
  brand?: string | null;
  use_case?: string | null;
  size_value?: string | null;
  size_system?: string | null;
  color?: string | null;
  target_price?: number | null;
  target_price_currency?: string | null;
  created_at: string;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
};

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type AuthResponse = {
  tokens: TokenPair;
  user: {
    id: string;
    telegram_id: number;
    username?: string | null;
    first_name?: string | null;
    last_name?: string | null;
  };
};

export type ProductDuplicateCandidate = {
  product_id: string;
  name: string;
  model?: string | null;
  sku?: string | null;
};

export type ProductDuplicateCandidateGroup = {
  category_id: string;
  brand_id?: string | null;
  normalized_identity: string;
  products: ProductDuplicateCandidate[];
};

export type ProductMergeResult = {
  source_product_id: string;
  target_product_id: string;
  offers_moved: number;
  price_analytics_moved: number;
  recommendations_moved: number;
  watchlists_moved: number;
  variants_deleted: number;
  mappings_moved: number;
  sync_run_items_moved: number;
  source_product_deleted: boolean;
};

export type Store = {
  id: string;
  name: string;
  country: string;
  url: string;
  active: boolean;
  delivers_to_cz: boolean;
  created_at: string;
};

export type SourceConfig = {
  id: string;
  store_id: string;
  source_type: string;
  endpoint_url?: string | null;
  active: boolean;
  sync_interval_minutes?: number | null;
  last_sync_at?: string | null;
  next_sync_at?: string | null;
  settings?: Record<string, unknown> | null;
};

export type SourceConfigCreatePayload = {
  source_type: string;
  endpoint_url?: string | null;
  active: boolean;
  sync_interval_minutes?: number | null;
  settings?: Record<string, unknown> | null;
};

export type SourceConfigUpdatePayload = {
  endpoint_url?: string | null;
  active?: boolean | null;
  sync_interval_minutes?: number | null;
  settings?: Record<string, unknown> | null;
};

export type SyncRun = {
  id: string;
  store_id?: string | null;
  source_config_id?: string | null;
  source_type: string;
  status: string;
  products_seen: number;
  offers_seen: number;
  failed_offers: number;
  error_message?: string | null;
  started_at: string;
  finished_at?: string | null;
};

export type SyncRunItem = {
  id: string;
  sync_run_id: string;
  external_id?: string | null;
  status: string;
  product_id?: string | null;
  offer_id?: string | null;
  error_message?: string | null;
  raw_data?: Record<string, unknown> | null;
  created_at: string;
};
