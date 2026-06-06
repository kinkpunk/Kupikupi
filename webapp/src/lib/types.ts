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

export type ShoppingRequest = {
  id: string;
  raw_text: string;
  status: string;
  locale: string;
  display_currency?: string | null;
  budget_amount?: number | null;
  constraints?: ShoppingRequestConstraints | null;
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
  active: boolean;
  archived: boolean;
  model?: string | null;
  category?: string | null;
  size_value?: string | null;
  size_system?: string | null;
  color?: string | null;
  target_price?: number | null;
  target_price_currency?: string | null;
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
