"""
Hybrid Screening System for Thoth

This module implements a hybrid screening system that combines rule-based screening
with score-based content evaluation. Rule-based screening takes absolute precedence
over content scores for specific hard constraints.
"""

import logging
from contentScoring import ContentScorer
from authorValidation import isBlacklisted, isAuthorWhitelisted, isHiveActivityTooRecent
from contentValidation import isTooShortHard, isEdit, hasBlacklistedTag, hasRequiredTag
from walletValidation import walletScreened
from utils import detect_language
from configValidator import ConfigValidator

logger = logging.getLogger(__name__)

class HybridScreening:
    """Hybrid screening system that applies rule-based constraints before content scoring."""
    
    def __init__(self, steem_instance, config):
        """
        Initialize the hybrid screening system.
        
        Args:
            steem_instance: Steem blockchain instance
            config: Configuration validator with loaded settings
        """
        self.steem = steem_instance
        self.config = config
        self.content_scorer = ContentScorer(steem_instance, config)
        
    def screen_content(self, post_data, latest_content=None):
        """
        Screen content using hybrid approach: rule-based first, then score-based.
        
        Args:
            post_data: Dictionary containing post information from blockchain
            latest_content: Optional latest content data to avoid re-fetching
            
        Returns:
            Dictionary containing screening result with status and details
        """
        try:
            # Get detailed post information if not provided
            if latest_content is None:
                post = self.steem.get_content(post_data['author'], post_data['permlink'])
            else:
                post = latest_content
            
            # Apply rule-based screening (hard constraints)
            rule_result = self._apply_rule_based_screening(post_data, post)
            
            if not rule_result['passed']:
                return {
                    'status': 'rejected',
                    'reason': rule_result['reason'],
                    'rule_type': rule_result['rule_type'],
                    'score_result': None,
                    'quality_tier': None,
                    'ai_intensity': None
                }
            
            # If passed rule-based screening, apply content scoring
            score_result = self.content_scorer.score_content(post_data)
            quality_tier = score_result['quality_tier']
            ai_intensity = self.content_scorer.get_ai_analysis_intensity(score_result)
            should_curate = self.content_scorer.should_curate(score_result)
            
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
    
    def _apply_rule_based_screening(self, post_data, post):
        """
        Apply rule-based screening with hard constraints that override scores.
        
        Args:
            post_data: Dictionary containing post information from blockchain
            post: Detailed post information from Steem API
            
        Returns:
            Dictionary with screening result
        """
        author = post_data['author']
        permlink = post_data['permlink']
        body = post['body']
        title = post['title']
        
        # Rule 1: Blacklisted authors must be excluded (absolute rule)
        if isBlacklisted(author, steem_instance=self.steem):
            logger.info(f"Rule-based rejection: {author}/{permlink} is blacklisted")
            return {
                'passed': False,
                'reason': f'blacklisted_author: {author}',
                'rule_type': 'blacklist'
            }
        
        # Rule 2: Whitelisted authors should be included unless below hard minimum word count
        if isAuthorWhitelisted(author):
            word_count = len(body.split())
            min_words_hard = self.config.get_int('CONTENT', 'MIN_WORDS_HARD', 0)
            
            if min_words_hard > 0 and word_count < min_words_hard:
                logger.info(f"Rule-based rejection: {author}/{permlink} is whitelisted but below hard minimum word count ({word_count} < {min_words_hard})")
                return {
                    'passed': False,
                    'reason': f'whitelisted_below_minimum_words: {word_count} < {min_words_hard}',
                    'rule_type': 'whitelist_minimum'
                }
            else:
                logger.info(f"Rule-based acceptance: {author}/{permlink} is whitelisted and meets word count requirements")
                return {
                    'passed': True,
                    'reason': f'whitelisted_author: {author}',
                    'rule_type': 'whitelist'
                }
        
        # Rule 3: Hive inactivity must be higher than specified days
        if isHiveActivityTooRecent(author):
            hive_inactivity_days = self.config.get_int('AUTHOR', 'LAST_HIVE_ACTIVITY_AGE', 60)
            logger.info(f"Rule-based rejection: {author}/{permlink} has recent Hive activity (below {hive_inactivity_days} days)")
            return {
                'passed': False,
                'reason': f'recent_hive_activity: author has been active on Hive recently',
                'rule_type': 'hive_inactivity'
            }
        
        # Rule 4: Author must not delegate too much to screened accounts
        if walletScreened(author, steem_instance=self.steem):
            max_screened_delegation_pct = self.config.get_float('WALLET', 'MAX_SCREENED_DELEGATION_PCT', 15.0)
            logger.info(f"Rule-based rejection: {author}/{permlink} delegates too much to screened accounts (exceeds {max_screened_delegation_pct}%)")
            return {
                'passed': False,
                'reason': f'excessive_screened_delegations: author delegates too much to screened accounts',
                'rule_type': 'delegation_screening'
            }
        
        # Rule 5: Language must be in the allowed list
        try:
            target_languages = [lang.strip() for lang in self.config.get('CONTENT', 'LANGUAGE').split(',') if lang.strip()]
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
        
        # Rule 6: Blacklisted tags must be rejected
        if hasBlacklistedTag(post_data):
            logger.info(f"Rule-based rejection: {author}/{permlink} contains blacklisted tags")
            return {
                'passed': False,
                'reason': 'blacklisted_tags: post contains excluded tags',
                'rule_type': 'tag_filter'
            }
        
        # Rule 7: Word count must exceed the hard minimum
        if isTooShortHard(body):
            min_words_hard = self.config.get_int('CONTENT', 'MIN_WORDS_HARD', 0)
            word_count = len(body.split())
            logger.info(f"Rule-based rejection: {author}/{permlink} below hard minimum word count ({word_count} < {min_words_hard})")
            return {
                'passed': False,
                'reason': f'below_minimum_words: {word_count} < {min_words_hard}',
                'rule_type': 'word_count'
            }
        
        # Additional rule-based checks that should also take precedence
        # Check for edits (edited posts are typically not curated)
        if isEdit(post_data, steem_instance=self.steem, latest_content=post):
            logger.info(f"Rule-based rejection: {author}/{permlink} appears to be an edited post")
            return {
                'passed': False,
                'reason': 'edited_post: post appears to have been edited',
                'rule_type': 'edit_check'
            }
        
        # Check for required tags (if configured)
        if not hasRequiredTag(post_data):
            logger.info(f"Rule-based rejection: {author}/{permlink} missing required tags")
            return {
                'passed': False,
                'reason': 'missing_required_tags: post does not contain required tags',
                'rule_type': 'tag_filter'
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