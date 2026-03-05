# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 
### Added
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
  - Median follower reputation (audience quality, 0-15 points)
- New `src/hybridScreening.py` module with HybridScreening class
- Comprehensive verification script `tools/verify_hybrid_implementation.py`
- Enhanced testing script `tools/test_enhanced_content_scoring.py`
- Rule-based early rejection for performance optimization

### Changed
- Content scoring system now uses sophisticated follower metrics from authorValidation.py
- Main curation loop updated to use HybridScreening instead of ContentScorer
- Author scoring rebalanced to incorporate growth and quality metrics
- Configuration values dynamically loaded (no hard-coded thresholds)
- Enhanced logging with detailed screening reasons and rule types

### Fixed
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