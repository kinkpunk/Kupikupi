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
  size_value?: string | null;
  size_system?: string | null;
  color?: string | null;
  target_price?: number | null;
  target_price_currency?: string | null;
};
