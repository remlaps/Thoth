# Hybrid Screening Implementation Summary

## Overview

This implementation adds a hybrid screening system to Thoth that combines rule-based screening with score-based content evaluation. Rule-based screening takes absolute precedence over content scores for specific hard constraints.

## Key Features Implemented

### 1. Rule-Based Screening (Hard Constraints)

The following 7 rules take precedence over content scores:

1. **Word Count**: Must exceed the hard minimum (`MIN_WORDS_HARD`) - *Optimized to run first.*
2. **Blacklisted Authors**: Must be excluded regardless of content quality
3. **Whitelisted Authors**: Should be included unless below hard minimum word count
4. **Hive Inactivity**: Must be higher than the specified days (`LAST_HIVE_ACTIVITY_AGE`)
5. **Delegation Screening**: Author must not delegate too much to screened accounts (`MAX_SCREENED_DELEGATION_PCT`)
6. **Language Validation**: Post language must be in the allowed list (`LANGUAGE`)
7. **Blacklisted Tags**: Posts containing blacklisted tags are rejected (`EXCLUDE_TAGS`)

### 2. Additional Rule-Based Checks

- **Edited Posts**: Edited posts are rejected (typically not curated)
- **Blacklisted Tags**: Posts containing blacklisted tags are rejected
- **Required Tags**: Posts missing required tags are rejected

### 3. Score-Based Evaluation (Conditional)

Content scoring is only applied to posts that pass all rule-based checks:
- **Enhanced Author Quality Scoring**:
  - Reputation scoring (normalized 0-25 points)
  - **Followers per month** (normalized growth rate, 0-20 points)
  - **Adjusted followers per month** (with half-life decay, 0-25 points)
  - **Median follower reputation** (Disabled for performance optimization)
  - Account age and activity scoring
- Content quality scoring (length, tags, language)
- Engagement scoring (votes, comments, value, **resteems**)
- Quality tier determination (excellent, good, fair, poor, reject)
- AI analysis intensity based on quality

## Implementation Details

### New Files Created

1. **`src/hybridScreening.py`**: Main hybrid screening system
   - `HybridScreening` class that combines rule-based and score-based screening
   - `_apply_rule_based_screening()` method implements the 5 hard constraints
   - Early return logic ensures rules take precedence over scores

2. **`src/statsTracker.py`**: Statistics tracking system
   - Tracks evaluation counts, rejection reasons, and acceptance rates
   - Generates detailed reports at the end of each run

3. **`tools/verify_hybrid_implementation.py`**: Verification script
   - Confirms all components are properly integrated
   - Validates rule precedence logic
   - Checks configuration usage

### Modified Files

1. **`src/main.py`**: Updated to use hybrid screening
   - Replaced `ContentScorer` with `HybridScreening`
   - Updated main curation loop to use `screen_content()` method
   - Enhanced logging to show screening status and reasons
   - Maintained backward compatibility for score tracking
   - Integrated `StatsTracker` for run-time statistics

## Configuration Settings Used

The implementation uses existing configuration settings:

```ini
[CONTENT]
MIN_WORDS_HARD = 100  # Hard minimum word count

[AUTHOR]
LAST_HIVE_ACTIVITY_AGE = 60  # Minimum days since Hive activity

[SCORING]
# All existing scoring thresholds and weights are preserved
```

## How It Works

### Screening Flow

1. **Rule-Based Screening First**:
   - Check word count → REJECT if below minimum
   - Check if author is blacklisted → REJECT (no scoring)
   - Check if author is whitelisted → ACCEPT (unless below word count)
   - Check Hive inactivity → REJECT if too recent
   - Check delegation screening → REJECT if exceeds threshold
   - Check language validation → REJECT if not in allowed list
   - Check blacklisted tags → REJECT if contains excluded tags
   - Check other rule-based constraints

2. **Score-Based Evaluation (Conditional)**:
   - Only applied if all rule-based checks pass
   - Calculate content score across author, content, and engagement
   - Determine quality tier and AI analysis intensity
   - Apply score-based curation thresholds

3. **Final Decision**:
   - Rule-based rejections are final (no appeal via scoring)
   - Score-based decisions only apply to rule-compliant content

### Return Values

The `screen_content()` method returns a comprehensive result:

```python
{
    'status': 'accepted|rejected|score_rejected|error',
    'reason': 'detailed_reason',
    'rule_type': 'blacklist|whitelist|hive_inactivity|word_count|hybrid|rules_passed',
    'score_result': {...},  # Only if scoring was performed
    'quality_tier': 'excellent|good|fair|poor|reject',
    'ai_intensity': 'detailed|standard|light|none',
    'total_score': 85.5  # Only if scoring was performed
}
```

## Benefits

1. **Rule Precedence**: Critical constraints (blacklists, whitelists, minimum quality) cannot be overridden by high scores
2. **Performance**: Avoids expensive scoring calculations for rule-violating content
3. **Flexibility**: Maintains sophisticated scoring for compliant content
4. **Backward Compatibility**: Existing scoring logic and configurations are preserved
5. **Clear Logging**: Enhanced debugging with detailed screening reasons

## Testing

The implementation includes comprehensive verification:
- All 8 required rules are implemented and tested
- Rule precedence logic verified
- Configuration integration confirmed
- Main integration validated

## Usage

The hybrid screening system is now active in the main curation loop. No configuration changes are required - it uses existing settings and adds the rule-based constraints on top of the existing scoring system.

To verify the implementation is working, run:
```bash
python tools/verify_hybrid_implementation.py
```

This will confirm all components are properly integrated and the rule precedence logic is functioning correctly.