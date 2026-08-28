// V2.3A consumer closeout -- Quick Interests (first-run declared preference).
//
// This is deliberately NOT V2.3B Personal Learning. It is the mobile-only,
// cold-start declared-preference capture from the first-run "What matters
// to you right now?" screen: a small, explicit, user-chosen set of category
// ids, stored locally and re-editable, never inferred from behavior and
// never fed into UserModelBuilder's `_fold_behavioral_evidence`/
// `_fold_exposure_evidence` (the inferred-interest path) on the backend.
//
// V2.3B INSERTION POINT (documented, not built tonight -- see the
// project's own V2.3B audit findings): the backend contract already has a
// real, unused slot for exactly this -- `Interest.source: "explicit"` in
// logan_core/user_model/model.py -- but no API route exists yet to let a
// client declare one; today explicit interests can only be seeded
// server-side via UserModelBuilder.seed(). When that route exists, this
// module's job becomes: on change, POST { categories } to it (in addition
// to, or instead of, this local SecureStore copy), and V2.3B's own learning
// engine reads `Interest.source == "explicit"` rows already knowing to
// treat them as ground truth, never overwritten by inferred folding. Until
// then, this stays entirely local -- no backend write, no Memory record,
// no personalization effect.
import * as SecureStore from "expo-secure-store";

export type InterestCategoryId =
  | "markets"
  | "sports_odds"
  | "trends_tech"
  | "world_politics"
  | "culture_media"
  | "other";

export interface DeclaredInterests {
  categories: InterestCategoryId[];
  selectedAt: string; // ISO 8601, set on every save
}

const DECLARED_INTERESTS_KEY = "stratus_declared_interests_v1";

export const INTEREST_CATEGORIES: {
  id: InterestCategoryId;
  label: string;
  description: string;
  icon: "trending-up-outline" | "trophy-outline" | "flash-outline" | "earth-outline" | "musical-notes-outline" | "add-circle-outline";
}[] = [
  { id: "markets", label: "Markets", description: "Stocks, crypto, and global markets", icon: "trending-up-outline" },
  { id: "sports_odds", label: "Sports & Odds", description: "Scores, odds, and real-time edge", icon: "trophy-outline" },
  { id: "trends_tech", label: "Trends & Tech", description: "AI, innovation, and what's next", icon: "flash-outline" },
  { id: "world_politics", label: "World & Politics", description: "Global events and policy shifts", icon: "earth-outline" },
  { id: "culture_media", label: "Culture & Media", description: "Music, movies, and pop culture", icon: "musical-notes-outline" },
  { id: "other", label: "Other", description: "Something else on your radar", icon: "add-circle-outline" },
];

/**
 * This device's saved declared interests, or `null` if the first-run
 * interests step has never been completed (distinct from "completed with
 * zero categories selected", which is a valid, saved empty array).
 */
export async function getDeclaredInterests(): Promise<DeclaredInterests | null> {
  const raw = await SecureStore.getItemAsync(DECLARED_INTERESTS_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as DeclaredInterests;
    return Array.isArray(parsed.categories) ? parsed : null;
  } catch {
    return null;
  }
}

export async function saveDeclaredInterests(categories: InterestCategoryId[]): Promise<void> {
  const value: DeclaredInterests = { categories, selectedAt: new Date().toISOString() };
  await SecureStore.setItemAsync(DECLARED_INTERESTS_KEY, JSON.stringify(value));
}
