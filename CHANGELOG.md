# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added

## [0.1.7] - 2026-04-03
### Added
- Added `SKIP_ONCHAIN_HISTORY` configuration option in the `[HISTORY]` section to optionally disable saving the curation history linked list on the blockchain via `custom_json`.

### Changed
- Gemma4 uses \<thought\> tags instad of \<think\> tags.  Added code to strip them from the AI response.

## [0.1.6] - 2026-03-28
### Added
- Integrated `linkedListOnSteem` library to record Thoth's run history, state, and curated article metadata immutably on the Steem blockchain using `custom_json` transactions.

### Changed

### Fixed

## [0.1.5] - 2026-03-24
### Added
- Implemented dynamic screening for DMCA/copyright claims by automatically fetching and caching Steemit Condenser's official DMCA blocklist from GitHub once per run.
- Added a hard rejection rule for posts that have been replaced with frontend DMCA/takedown notices (e.g., "This post is not available due to a copyright claim.").
- Added a hard minimum reputation check (`MIN_REPUTATION`) to the hybrid screening rules that bypasses scoring entirely for low-reputation authors.
- Added a hard rejection rule for Steem inactivity to instantly reject posts if the author has been inactive for more than `MAX_INACTIVITY_DAYS`.

### Changed
- Updated the author activity scoring component to scale linearly from maximum points at 0 days of inactivity down to exactly 0 points at the `MAX_INACTIVITY_DAYS` limit.

### Fixed
- Fixed an issue where model switching would not trigger on `503` errors if the API provider returned non-JSON responses or differently formatted error messages. Thoth now robustly handles `500`, `502`, `503`, and `504` HTTP status codes as rate limits to properly activate fallback models.
- Fixed an issue where Thoth evaluated and logged the original, unedited version of posts. All screening, AI evaluation, and reporting now properly refer to the final updated state of the post.
- Fixed a silent configuration bug where the hard minimum word count check could temporarily default to 0 words. The check is now natively enforced within the hybrid screening sequence using globally verified configuration objects.
- Upgraded the `word_count` function to use regular expressions to count actual alphanumeric words, preventing Markdown formatting (like tables and URLs) from falsely inflating the length count and tricking the `MIN_WORDS_HARD` check.
- Updated the dynamic reputation scoring calculation to scale its baseline from the `MIN_REPUTATION` threshold rather than a hardcoded base of 25.

## [0.1.4] - 2026-03-21
### Changed
- Synchronized logging in `walletValidation.py` and `authorValidation.py` by replacing standard `print()` statements with the `logging` module to prevent asynchronous console buffering issues.

## [0.1.3] - 2026-03-21
### Added
- Implemented a two-tiered Hive inactivity screening system: a hard minimum cutoff (`MIN_HIVE_INACTIVITY_HARD`) for instant rejection, and a scaled scoring component (`TARGET_HIVE_INACTIVITY_DAYS`, `MAX_HIVE_INACTIVITY_SCORE`) for rewarding longer inactivity.
- Added automated truncation for post bodies to ~30,000 characters when using ArliAI to prevent exceeding their new 12K context limit.
- Added explicit start/finish log markers for the AI curation and intro generation processes to track progress.
- `DRY_RUN` configuration parameter in the `[STEEM]` section to skip blockchain posting, replying, and voting.
- `SKIP_AI_CURATION` configuration parameter in the `[LLM]` section to bypass LLM API calls and generate placeholder text instead.
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
- New `src/hybridScreening.py` module with HybridScreening class
- Comprehensive verification script `tools/verify_hybrid_implementation.py`
- Enhanced testing script `tools/test_enhanced_content_scoring.py`
- Rule-based early rejection for performance optimization
- Configurable maximum scores for all author and content evaluation components added to the `[SCORING]` section.
- `ENABLE_MEDIAN_REP_SCORING` configuration parameter added to optionally toggle the computationally expensive median follower reputation check.
- In-memory caching for `getMedianFollowerRep` across posts by the same author to minimize redundant API calls.
- Integrated `influence_ratio` metric (followers/following) into author scoring, complete with Laplace smoothing to provide a grace period for brand new authors.

### Changed
- Synchronized logging in `main.py` and `hybridScreening.py` by replacing standard `print()` statements with `logging.info()` to prevent async console buffering issues.
- Optimized AI prompt payloads for ArliAI's shift to `Qwen3.5-27B-Derestricted` models (removed `extra_body`, lowered repetition penalties to `0.3`, and standardized the early termination parameter to `"stop"`).
- Status changed from Beta to Stable for the 0.1.3 release.
- Renamed all `ARLIAI` configuration parameters to use a generic `LLM` prefix (e.g., `LLM_API_KEY`, `LLM_MODEL`) to better reflect support for multiple AI providers.
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
- Replaced hard-coded scoring discontinuities (e.g., word count length cliffs) with continuous formulas for smoother, fairer evaluations.
- Rescaled the Median Follower Reputation scoring to map dynamically between a reputation range of 30 and 60 (previously assumed 0-80).

### Fixed
- **Crash Fix**: Removed unsupported `extra_body` chat template arguments that were causing `502 Bad Gateway` crashes on the ArliAI API.
- **Crash Fix**: Added safe parsing for `null` JSON API responses when stop sequences trigger on the very first generated token (now correctly interprets as an implicit AI rejection).
- **Accuracy Issue**: The hard minimum word count check now correctly strips HTML and Markdown before counting words, preventing short posts with long URLs from sneaking past the filter.
- **Logging**: Missing author and permlink context in AI response warnings has been restored.
- **Major Performance Issue**: Made the `getMedianFollowerRep` calculation conditionally optional (default: False) to prevent extreme slowdowns and API spam.
- **Performance Issue**: Replaced inefficient `len(account.get_followers())` with the fast `get_follow_count` API call to get follower counts.
- **Performance Issue**: Eliminated a redundant `get_content` API call by passing the post object from the screening stage to the scoring stage.
- **Accuracy Issue**: Word count for scoring now correctly strips HTML and Markdown, leading to more accurate content length scores.
- **Accuracy Issue**: Tag extraction logic safely parses `json_metadata` when the Steem API returns it as a serialized JSON string rather than a dictionary.
- **Accuracy Issue**: Corrected median follower reputation calculation to utilize the API's pre-normalized values instead of inadvertently re-applying `log10` math.
- **Redundancy**: Streamlined date parsing in `contentScoring.py` into a robust `_parse_steem_date` helper method.
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