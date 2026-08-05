# Logan Intelligence — TriggerEvent Registry: Culture Domain
**Version:** 3.1.3
*New in v3.1.2. No prior version.*
*Authoritative source for all Culture domain trigger codes. Global index: `TRIGGER_REGISTRY_GLOBAL.md`.*

---

## Domain: `culture`

This registry defines every trigger code that may be emitted by the Culture Domain Receptor when operating on music streaming, video platform, social trend, and entertainment industry signals.

**Culture domain signals** include: music chart movements (Spotify, Apple Music), video platform virality (YouTube), social trend emergence, artist/creator momentum, and entertainment event anticipation.

**What Culture domain intelligence surfaces:** Logan uses Culture signals to identify opportunities in culture-adjacent investment domains (prediction markets on music/entertainment outcomes, stocks of entertainment companies, etc.) AND to surface cultural intelligence for users with direct interest in culture/entertainment (e.g., users who follow music, film, or gaming).

---

## CULTURE_CHART_VELOCITY_SURGE

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_CHART_VELOCITY_SURGE` |
| **Status** | ACTIVE |
| **Description** | A song or album's chart position is rising with unusual velocity — faster than typical for its genre or release age. Suggests unexpected breakout momentum. |
| **Fire condition** | Chart position improvement rate ≥ 3× typical for track/artist category AND sustained ≥ 48 hours |
| **Confidence contribution** | +0.16 |

**Context shape:**
```json
{
  "entity": "track_title_or_artist",
  "platform": "spotify",
  "chart": "Global Top 50",
  "current_position": 8,
  "prior_position_48h": 42,
  "velocity_vs_typical": 3.8,
  "stream_velocity": 4200000,
  "stream_velocity_vs_avg": 3.2
}
```

---

## CULTURE_CHART_ENTRY_NEW

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_CHART_ENTRY_NEW` |
| **Status** | ACTIVE |
| **Description** | An entity enters a major chart at a notable position, indicating a breakout debut. |
| **Fire condition** | New chart entry at position ≤ 10 on a top-100 chart |
| **Confidence contribution** | +0.14 |

**Context shape:**
```json
{
  "entity": "artist_or_track",
  "platform": "apple_music",
  "chart": "US Top 100",
  "entry_position": 6,
  "is_debut": true,
  "prior_chart_presence": false
}
```

---

## CULTURE_VIDEO_VIEW_VELOCITY

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_VIDEO_VIEW_VELOCITY` |
| **Status** | ACTIVE |
| **Description** | A YouTube video is accumulating views at a rate significantly above expected for its category and channel size. Indicates viral momentum. |
| **Fire condition** | View rate in most recent 6-hour window ≥ 4× expected rate for that channel's size and content category |
| **Confidence contribution** | +0.14 |

**Context shape:**
```json
{
  "video_id": "yt_video_id",
  "channel": "channel_name",
  "category": "music",
  "views_6h": 8400000,
  "expected_views_6h": 1800000,
  "velocity_vs_expected": 4.7,
  "total_views": 24000000,
  "publish_age_hours": 18
}
```

---

## CULTURE_SOCIAL_SEARCH_SURGE

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_SOCIAL_SEARCH_SURGE` |
| **Status** | ACTIVE |
| **Description** | Search volume for an entity spikes significantly above its recent baseline, indicating a surge in public attention that may precede broader mainstream discovery. |
| **Fire condition** | Search volume ≥ 4× 30-day average AND sustained ≥ 12 hours |
| **Confidence contribution** | +0.10 |

**Context shape:**
```json
{
  "entity": "artist_name",
  "search_volume_current": 840000,
  "search_volume_30d_avg": 180000,
  "volume_vs_avg": 4.7,
  "sustained_hours": 18,
  "related_queries": ["tour", "new album", "collab"]
}
```

---

## CULTURE_CROSS_PLATFORM_CONVERGENCE

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_CROSS_PLATFORM_CONVERGENCE` |
| **Status** | ACTIVE |
| **Description** | An entity is trending simultaneously on 3 or more major platforms (Spotify, YouTube, Apple Music, social search, Reddit, etc.). Cross-platform convergence indicates genuine breakout momentum, not platform-specific noise. |
| **Fire condition** | Entity registers above-baseline activity on ≥ 3 distinct platforms within a 24-hour window |
| **Confidence contribution** | +0.22 |

**Context shape:**
```json
{
  "entity": "artist_or_track",
  "platform_count": 4,
  "platforms": ["spotify", "youtube", "apple_music", "social_search"],
  "convergence_window_hours": 18,
  "convergence_strength": 0.78
}
```

---

## CULTURE_ARTIST_ANNOUNCEMENT

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_ARTIST_ANNOUNCEMENT` |
| **Status** | ACTIVE |
| **Description** | A significant artist announcement is detected: new album/single release, tour announcement, major collaboration, or industry award/nomination. |
| **Fire condition** | Official announcement detected via artist/label social accounts or entertainment news sources above confidence threshold |
| **Confidence contribution** | +0.18 |

**Context shape:**
```json
{
  "artist": "artist_name",
  "announcement_type": "album_release",
  "announcement_detail": "New album 'Title' releasing Sept 15",
  "source": "official_instagram",
  "detected_at": "2026-08-03T14:22:00Z"
}
```

---

## CULTURE_VIRAL_MOMENT

| Field | Value |
|-------|-------|
| **Code** | `CULTURE_VIRAL_MOMENT` |
| **Status** | ACTIVE |
| **Description** | A clip, meme, or cultural moment is spreading virally, independent of the entity's scheduled release or marketing activity. Often a catalyst for broader discovery. |
| **Fire condition** | Content engagement rate ≥ 10× typical for source AND spreads to ≥ 3 platforms within 6 hours |
| **Confidence contribution** | +0.16 |

**Context shape:**
```json
{
  "entity": "artist_or_content",
  "moment_description": "Clip from live performance going viral on short-form video",
  "originating_platform": "tiktok",
  "spread_to_platforms": ["twitter", "instagram", "youtube"],
  "spread_hours": 4,
  "engagement_vs_typical": 12.3
}
```

---

*Logan Intelligence TriggerEvent Registry: Culture — v3.1.2 | 2026-08-03*
*New in v3.1.2. 7 codes registered.*
