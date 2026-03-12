# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 
### Added
- `StatsTracker` system (`src/statsTracker.py`) to collect and report detailed run statistics, including rejection reasons and score distributions.
- Resteems are now included in the engagement score calculation.
- End-of-run statistical report is now printed to the console and appended to `output.html`.
- Hybrid screening system combining rule-based and score-based evaluation
- 7 hard constraint rules that take precedence over content scores:
  - Blacklisted authors (absolute exclusion regardless of score)
  - Whitelisted authors (conditional acceptance unless below word count)
  - Hive inactivity screening (LAST_HIVE_ACTIVITY_AGE configuration)
  - Delegation screening (MAX_SCREENED_DELEGATION_PCT configuration)
  - Language validation (LANGUAGE configuration)
  - Blacklisted tags screening (EXCLUDE_TAGS configuration)
  - Word count minimum enforcement (MIN_WORDS_HARD configuration)
- Enhanced author quality scoring with advanced follower metrics:
  - Followers per month (normalized growth rate, 0-20 points)
  - Adjusted followers per month (with half-life decay, 0-25 points)
  - ~~Median follower reputation (audience quality, 0-15 points)~~ (Disabled for performance)
- New `src/hybridScreening.py` module with HybridScreening class
- Comprehensive verification script `tools/verify_hybrid_implementation.py`
- Enhanced testing script `tools/test_enhanced_content_scoring.py`
- Rule-based early rejection for performance optimization

### Changed
- The hard minimum word count check is now the first rule executed in the screening process for significant performance improvement.
- The engagement scoring logic in `contentScoring.py` was refactored to use a configurable weighted-average model based on settings in `config.ini`.
- The `_score_language` check now correctly references the soft minimum word count (`MIN_WORDS`) from the configuration.
- Updated `HYBRID_SCREENING_IMPLEMENTATION.md` to reflect the new rule order and other scoring enhancements.
- Content scoring system now uses sophisticated follower metrics from authorValidation.py
- Main curation loop updated to use HybridScreening instead of ContentScorer
- Author scoring rebalanced to incorporate growth and quality metrics
- Configuration values dynamically loaded (no hard-coded thresholds)
- Enhanced logging with detailed screening reasons and rule types
- Optimized rule-based screening order in `hybridScreening.py` to implement a "Fail-Fast" strategy: cheap local checks (word count, language, tags) now run before expensive network checks (blacklist, wallet, history).
- Updated `verify_hybrid_implementation.py` to verify the exact execution order of screening rules.
- Refactored `test_hybrid_screening.py` to use extensive Mocking, ensuring unit tests verify specific logic in isolation regardless of the new optimization order.

### Fixed
- **Major Performance Issue**: Disabled the `getMedianFollowerRep` calculation, which was causing extreme slowdowns and API spam by fetching all followers of an author.
- **Performance Issue**: Replaced inefficient `len(account.get_followers())` with the fast `get_follow_count` API call to get follower counts.
- **Performance Issue**: Eliminated a redundant `get_content` API call by passing the post object from the screening stage to the scoring stage.
- **Accuracy Issue**: Word count for scoring now correctly strips HTML and Markdown, leading to more accurate content length scores.
- Performance issues by avoiding scoring calculations for rule-violating content
- Inconsistent author quality assessment with basic follower counts
- Rule precedence logic to ensure hard constraints override scores

## [0.1.1] - 2026-02-28
### Addded
- Version info
- Changelog

### Changed
- Performance improvements:
   - get accounts in batches, instead of one at a time
   - Add a hard limit for minimum word count
   - Eliminate redundant Steem API calls

## [0.1.0] - 2025-02-24
### Added
- Initial Beta release.
- Core curation loop with Steem blockchain integration.
- LLM-based content evaluation using ArliAI/Gemini.
- Automatic model switching for API rate limit resilience.
- Configurable beneficiary reward structure ("Thoth's Flywheel").
- `src/version.py` for centralized version tracking.
- Configuration validation logic to prevent runtime errors.

### Changed
- Updated `main.py` to display version information on startup.