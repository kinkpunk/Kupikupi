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
