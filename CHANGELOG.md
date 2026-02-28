# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 
### Added

### Changed

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