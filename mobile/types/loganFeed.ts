// Mirrors backend/app/logan_feed.py's DemoFeedResponse/FeedItem.

export type DeliveredItem = {
  event_id: string;
  surface: "wheel" | "feed_card" | "alert" | "digest" | "background";
  headline: string;
  what_happened: string;
  why_it_matters: string;
  why_it_matters_to_me: string;
  why_now: string;
  confidence_label: "High" | "Moderate" | "Low" | "Speculative";
  confidence_score: number;
  connected_items: string[];
  required_disclaimers: string[];
  delivered_at: string;
};

export type FeedItem = {
  event_id: string;
  entity_id: string;
  display_name: string;
  category: string;
  ticker: string | null;
  domain: string;
  delivered_item: DeliveredItem;
  // 1-indexed position in this response's already-sorted order (1 = most
  // important). The backend's internal ranking score is never exposed here
  // (ADR-029) -- `rank` is the correct public-facing ordering signal.
  rank: number;
  confidence_score: number;
  confidence_label: "High" | "Moderate" | "Low" | "Speculative";
  connected_event_ids: string[];
};

export type DemoFeedResponse = {
  items: FeedItem[];
  generated_at: string;
};
