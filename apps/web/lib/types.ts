export type MatchStatus = "scheduled" | "live" | "finished" | "unknown";

export interface SportInfo {
  slug: string;
  name: string;
}

export interface Competition {
  sport: string;
  slug: string;
  name: string;
  source: string;
  supports_standings: boolean;
  supports_upcoming: boolean;
  notes: string | null;
  badge_url: string | null;
  country: string | null;
}

export interface Match {
  id: string;
  sport: string;
  competition_slug: string;
  competition_name: string;
  status: MatchStatus;
  kickoff: string | null;
  home: string | null;
  away: string | null;
  home_id: string | null;
  away_id: string | null;
  home_crest: string | null;
  away_crest: string | null;
  home_score: number | null;
  away_score: number | null;
  live_minute: string | null;
  title: string | null;
  summary: string | null;
  venue: string | null;
  source: string;
}

export interface FormResult {
  match_id: string;
  date: string | null;
  opponent: string;
  venue: "home" | "away";
  goals_for: number;
  goals_against: number;
  outcome: "W" | "D" | "L";
}

export interface ScorelineProbability {
  home_goals: number;
  away_goals: number;
  pct: number;
}

export interface HandicapLine {
  line: number;
  cover_pct: number;
}

export interface MarginBucket {
  label: string;
  margin: number;
  pct: number;
}

export interface MatchPrediction {
  method: string;
  confidence: "real_history" | "league_average";
  home_matches_used: number;
  away_matches_used: number;
  h2h_matches_considered: number;
  h2h_adjustment_pct: number;
  home_attack_rating: number;
  home_defense_rating: number;
  away_attack_rating: number;
  away_defense_rating: number;
  expected_goals_home: number;
  expected_goals_away: number;
  home_win_pct: number;
  draw_pct: number;
  away_win_pct: number;
  double_chance_1x_pct: number;
  double_chance_x2_pct: number;
  double_chance_12_pct: number;
  btts_yes_pct: number;
  btts_no_pct: number;
  over_1_5_pct: number;
  over_2_5_pct: number;
  over_3_5_pct: number;
  top_scorelines: ScorelineProbability[];
  scoreline_grid: ScorelineProbability[];
  asian_handicap: HandicapLine[];
  margin_distribution: MarginBucket[];
  recommended_pick_label: string;
  recommended_pick_pct: number;
  expected_corners_home: number;
  expected_corners_away: number;
  expected_corners_total: number;
  corners_over_8_5_pct: number;
  corners_over_9_5_pct: number;
  corners_favoured_side: "home" | "away" | "even";
  note: string;
}

export interface MatchStatLine {
  label: string;
  home_value: number;
  away_value: number;
}

export interface MatchStats {
  lines: MatchStatLine[];
}

export interface MatchAnalysis {
  match_id: string;
  prediction: MatchPrediction | null;
  home_form: FormResult[];
  away_form: FormResult[];
  head_to_head: FormResult[];
  stats: MatchStats | null;
  note: string | null;
}

export interface HighlightMatch {
  match: Match;
  prediction: MatchPrediction | null;
}

export interface PlatformTelemetry {
  leagues_connected: number;
  matches_loaded: number;
  predictions_computed: number;
  model_accuracy_pct: number | null;
  model_accuracy_sample: number;
}

export interface HomeHighlights {
  featured: HighlightMatch | null;
  ticker: HighlightMatch[];
  top_by_favorite: HighlightMatch[];
  top_over_2_5: HighlightMatch[];
  top_btts: HighlightMatch[];
  mini_standings: Record<string, StandingRow[]>;
  unavailable: string[];
  telemetry: PlatformTelemetry;
}

export interface TeamSummary {
  team_id: string;
  team_name: string;
  crest_url: string | null;
  competition_slug: string;
  competition_name: string;
  sport: string;
}

export interface TeamAggregateStats {
  matches_played: number;
  wins: number;
  draws: number;
  losses: number;
  goals_for_avg: number;
  goals_against_avg: number;
  over_1_5_pct: number;
  over_2_5_pct: number;
  over_3_5_pct: number;
  btts_pct: number;
}

export interface TeamHistory {
  team: TeamSummary;
  venue_filter: "all" | "home" | "away";
  matches: FormResult[];
  aggregate: TeamAggregateStats | null;
}

export interface StandingRow {
  rank: number;
  team: string;
  played: number | null;
  wins: number | null;
  draws: number | null;
  losses: number | null;
  points: number | null;
  crest_url: string | null;
}

export interface MatchesResponse {
  competition: Competition;
  matches: Match[];
}

export interface LiveResponse {
  live: Match[];
  upcoming_today: Match[];
}

export interface QuickPick {
  label: string;
  pct: number;
  home_win_pct: number;
  draw_pct: number;
  away_win_pct: number;
}

export type QuickPicksResponse = Record<string, QuickPick>;

export interface StandingsResponse {
  competition: Competition;
  standings: StandingRow[] | null;
}
