"""
Hybrid Screening System for Thoth

This module implements a hybrid screening system that combines rule-based screening
with score-based content evaluation. Rule-based screening takes absolute precedence
over content scores for specific hard constraints.
"""

import logging
from contentScoring import ContentScorer
from authorValidation import isBlacklisted, isAuthorWhitelisted, isHiveActivityTooRecent, isAuthorPostLimitReached
from contentValidation import isTooShortHard, isEdit, hasBlacklistedTag, hasRequiredTag
from walletValidation import walletScreened
from utils import detect_language
from configValidator import ConfigValidator

logger = logging.getLogger(__name__)

class HybridScreening:
    """Hybrid screening system that applies rule-based constraints before content scoring."""
    
    def __init__(self, steem_instance, config, stats_tracker=None):
        """
        Initialize the hybrid screening system.
        
        Args:
            steem_instance: Steem blockchain instance
            config: Configuration validator with loaded settings
            stats_tracker: Optional StatsTracker instance
        """
        self.steem = steem_instance
        self.config = config
        self.stats_tracker = stats_tracker
        self.content_scorer = ContentScorer(steem_instance, config)
        
    def screen_content(self, post_data, latest_content=None, included_posts=None):
        """
        Screen content using hybrid approach: rule-based first, then score-based.
        
        Args:
            post_data: Dictionary containing post information from blockchain
            latest_content: Optional latest content data to avoid re-fetching
            included_posts: Optional list of already included posts for post limit checking
            
        Returns:
            Dictionary containing screening result with status and details
        """
        try:
            if self.stats_tracker:
                self.stats_tracker.track_evaluation()

            # Get detailed post information if not provided
            if latest_content is None:
                post = self.steem.get_content(post_data['author'], post_data['permlink'])
            else:
                post = latest_content
            
            # Apply rule-based screening (hard constraints)
            rule_result = self._apply_rule_based_screening(post_data, post, included_posts)
            
            if not rule_result['passed']:
                if self.stats_tracker:
                    self.stats_tracker.track_rejection(rule_result['rule_type'])

                return {
                    'status': 'rejected',
                    'reason': rule_result['reason'],
                    'rule_type': rule_result['rule_type'],
                    'score_result': None,
                    'quality_tier': None,
                    'ai_intensity': None
                }
            
            # If a rule forces acceptance (e.g., whitelist), bypass scoring.
            if rule_result['rule_type'] == 'whitelist':
                if self.stats_tracker:
                    # Track as accepted, with a placeholder tier
                    self.stats_tracker.track_acceptance(100.0, 'whitelisted')
                return {
                    'status': 'accepted',
                    'reason': rule_result['reason'],
                    'rule_type': rule_result['rule_type'],
                    'score_result': None, # No scoring performed
                    'quality_tier': 'whitelisted',
                    'ai_intensity': 'detailed', # Give whitelisted authors detailed analysis
                    'total_score': None
                }

            # If passed rule-based screening, apply content scoring
            score_result = self.content_scorer.score_content(post_data, content_data=post)
            quality_tier = score_result['quality_tier']
            ai_intensity = self.content_scorer.get_ai_analysis_intensity(score_result)
            should_curate = self.content_scorer.should_curate(score_result)
            
            if self.stats_tracker:
                if should_curate:
                    self.stats_tracker.track_acceptance(score_result['total_score'], quality_tier)
                else:
                    # This is a score-based rejection
                    self.stats_tracker.track_rejection('score_rejected', score=score_result['total_score'])

            return {
                'status': 'accepted' if should_curate else 'score_rejected',
                'reason': 'passed_rule_screening' if should_curate else 'below_score_threshold',
                'rule_type': 'hybrid',
                'score_result': score_result,
                'quality_tier': quality_tier,
                'ai_intensity': ai_intensity,
                'total_score': score_result['total_score']
            }
            
        except Exception as e:
            logger.error(f"Error in hybrid screening for {post_data['author']}/{post_data['permlink']}: {e}")
            return {
                'status': 'error',
                'reason': f'screening_error: {str(e)}',
                'rule_type': 'hybrid',
                'score_result': None,
                'quality_tier': None,
                'ai_intensity': None
            }
    
    def _apply_rule_based_screening(self, post_data, post, included_posts=None):
        """
        Apply rule-based screening with hard constraints that override scores.
        The order of checks is optimized to fail fast on cheap checks first, based on
        observed rejection statistics.
        
        Args:
            post_data: Dictionary containing post information from blockchain
            post: Detailed post information from Steem API
            included_posts: Optional list of already included posts for post limit checking

        Returns:
            Dictionary with screening result
        """
        author = post_data['author']
        permlink = post_data['permlink']
        body = post['body']
        title = post['title']

        # --- FAST, LOCAL CHECKS (ordered by rejection rate) ---

        # Rule 1: Word count must exceed the hard minimum (fastest check, highest rejection rate)
        if isTooShortHard(body):
            min_words_hard = self.config.get_int('CONTENT', 'MIN_WORDS_HARD', 0)
            # The body is likely to contain HTML, but for this hard check, a simple split is fast and sufficient.
            word_count = len(body.split())
            logger.info(f"Rule-based rejection: {author}/{permlink} below hard minimum word count ({word_count} < {min_words_hard})")
            return {
                'passed': False,
                'reason': f'below_minimum_words: {word_count} < {min_words_hard}',
                'rule_type': 'word_count'
            }

        # Rule 2: Language must be in the allowed list (local check, high rejection rate)
        try:
            target_languages = [lang.strip() for lang in self.config.get('CONTENT', 'LANGUAGE').split(',') if lang.strip()]
            if target_languages:  # Only perform check if languages are configured
                body_language = detect_language(body)
                title_language = detect_language(title)

                if body_language not in target_languages or title_language not in target_languages:
                    logger.info(f"Rule-based rejection: {author}/{permlink} language not in target list (body: {body_language}, title: {title_language}, allowed: {target_languages})")
                    return {
                        'passed': False,
                        'reason': f'invalid_language: body={body_language}, title={title_language}, allowed={target_languages}',
                        'rule_type': 'language_filter'
                    }
        except Exception as e:
            logger.warning(f"Language detection failed for {author}/{permlink}: {e}")
            # If language detection fails, we could either reject or allow
            # For now, we'll allow it to proceed to scoring
            pass

        # Rule 3: Check for edits (fast check, moderate rejection rate)
        if isEdit(post_data, steem_instance=self.steem, latest_content=post):
            logger.info(f"Rule-based rejection: {author}/{permlink} appears to be an edited post")
            return {
                'passed': False,
                'reason': 'edited_post: post appears to have been edited',
                'rule_type': 'edit_check'
            }

        # Rule 4: Blacklisted tags must be rejected (fast check)
        if hasBlacklistedTag(post_data):
            logger.info(f"Rule-based rejection: {author}/{permlink} contains blacklisted tags")
            return {
                'passed': False,
                'reason': 'blacklisted_tags: post contains excluded tags',
                'rule_type': 'tag_filter'
            }

        # Rule 5: Check for required tags (fast check)
        if not hasRequiredTag(post_data):
            logger.info(f"Rule-based rejection: {author}/{permlink} missing required tags")
            return {
                'passed': False,
                'reason': 'missing_required_tags: post does not contain required tags',
                'rule_type': 'tag_filter'
            }

        # Rule 6: Check if author has reached the maximum number of included posts (very fast in-memory check)
        if isAuthorPostLimitReached(post_data, included_posts):
            logger.info(f"Rule-based rejection: {author}/{permlink} author has reached maximum included posts limit")
            return {
                'passed': False,
                'reason': 'max_posts_per_author_reached: author has reached the maximum number of included posts',
                'rule_type': 'author_post_limit'
            }

        # --- FUNDAMENTAL AUTHOR STATUS CHECKS (Whitelist is a "pass", so check blacklist first) ---

        # Rule 7: Blacklisted authors must be excluded (absolute rule, first network call)
        if isBlacklisted(author, steem_instance=self.steem):
            logger.info(f"Rule-based rejection: {author}/{permlink} is blacklisted")
            return {
                'passed': False,
                'reason': f'blacklisted_author: {author}',
                'rule_type': 'blacklist'
            }

        # Rule 8: Whitelisted authors bypass all other checks (word count already checked)
        if isAuthorWhitelisted(author):
            logger.info(f"Rule-based acceptance: {author}/{permlink} is whitelisted and passed all prior hard checks")
            return {
                'passed': True,
                'reason': f'whitelisted_author: {author}',
                'rule_type': 'whitelist'
            }

        # --- SLOW, NETWORK-INTENSIVE CHECKS (for non-whitelisted authors) ---

        # Rule 9: Hive inactivity must be higher than specified days (network call)
        if isHiveActivityTooRecent(author):
            hive_inactivity_days = self.config.get_int('AUTHOR', 'LAST_HIVE_ACTIVITY_AGE', 60)
            logger.info(f"Rule-based rejection: {author}/{permlink} has recent Hive activity (below {hive_inactivity_days} days)")
            return {
                'passed': False,
                'reason': f'recent_hive_activity: author has been active on Hive recently',
                'rule_type': 'hive_inactivity'
            }

        # Rule 10: Wallet screening (slowest check, do last)
        if walletScreened(author, steem_instance=self.steem):
            logger.info(f"Rule-based rejection: {author}/{permlink} wallet flagged by screening")
            return {
                'passed': False,
                'reason': 'wallet_screened: author wallet flagged by screening',
                'rule_type': 'wallet_screened'
            }

        # If all rule-based checks pass, content can proceed to scoring
        return {
            'passed': True,
            'reason': 'passed_all_rule_checks',
            'rule_type': 'rules_passed'
        }
    
    def should_curate(self, screening_result):
        """Determine if content should be curated based on screening result."""
        if screening_result['status'] == 'accepted':
            return True
        return False
    
    def get_ai_analysis_intensity(self, screening_result):
        """Get AI analysis intensity from screening result."""
        return screening_result.get('ai_intensity', 'none')
    
    def get_quality_tier(self, screening_result):
        """Get quality tier from screening result."""
        return screening_result.get('quality_tier', 'reject')
    
    def get_total_score(self, screening_result):
        """Get total score from screening result."""
        return screening_result.get('total_score', 0.0)