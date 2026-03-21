"""
Content Quality Scoring System for Thoth

This module implements a comprehensive content quality scoring system that replaces
the binary accept/reject screening with a multi-dimensional scoring approach.
"""

import re
import json
from datetime import datetime, timedelta
import logging

from steem import Steem
from steem.account import Account
from steem.account import AccountDoesNotExistsException

from utils import get_rng, remove_formatting
from authorValidation import followersPerMonth, adjustedFollowersPerMonth, getMedianFollowerRep, hiveInactiveDays
from steemHelpers import get_resteem_count

logger = logging.getLogger(__name__)

class ContentScorer:
    """Main scoring engine for content quality assessment."""
    
    def __init__(self, steem_instance, config):
        """
        Initialize the content scorer.
        
        Args:
            steem_instance: Steem blockchain instance
            config: Configuration validator with loaded settings
        """
        self.steem = steem_instance
        self.config = config
        self.rng = get_rng()
        
        # Load scoring weights from configuration
        self.weights = self._load_scoring_weights()
        self.thresholds = self._load_scoring_thresholds()
        
        # Cache for expensive calculations
        self.median_rep_cache = {}
        
    def _load_scoring_weights(self):
        """Load scoring weights from configuration."""
        weights = {}
        
        # Author quality weights
        weights['author_reputation'] = self.config.get_float('AUTHOR', 'MIN_REPUTATION', 6.0) * 0.1
        weights['author_followers'] = self.config.get_int('AUTHOR', 'MIN_FOLLOWERS', 350) * 0.001
        weights['author_activity'] = self.config.get_int('AUTHOR', 'MAX_INACTIVITY_DAYS', 4000) * 0.001
        weights['author_median_rep'] = self.config.get_int('AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP', 40) * 0.1
        
        # Author max component scores
        weights['max_reputation_score'] = self.config.get_float('SCORING', 'MAX_REPUTATION_SCORE', 25.0)
        weights['max_followers_per_month_score'] = self.config.get_float('SCORING', 'MAX_FOLLOWERS_PER_MONTH_SCORE', 20.0)
        weights['max_adjusted_followers_score'] = self.config.get_float('SCORING', 'MAX_ADJUSTED_FOLLOWERS_SCORE', 25.0)
        weights['max_median_rep_score'] = self.config.get_float('SCORING', 'MAX_MEDIAN_REP_SCORE', 15.0)
        weights['max_age_score'] = self.config.get_float('SCORING', 'MAX_AGE_SCORE', 15.0)
        weights['max_activity_score'] = self.config.get_float('SCORING', 'MAX_ACTIVITY_SCORE', 15.0)
        weights['max_influence_score'] = self.config.get_float('SCORING', 'MAX_INFLUENCE_SCORE', 10.0)
        weights['max_hive_inactivity_score'] = self.config.get_float('SCORING', 'MAX_HIVE_INACTIVITY_SCORE', 10.0)

        # Content max component scores
        weights['max_length_score'] = self.config.get_float('SCORING', 'MAX_LENGTH_SCORE', 30.0)
        weights['max_title_score'] = self.config.get_float('SCORING', 'MAX_TITLE_SCORE', 10.0)
        weights['max_tag_score'] = self.config.get_float('SCORING', 'MAX_TAG_SCORE', 15.0)
        weights['max_language_score'] = self.config.get_float('SCORING', 'MAX_LANGUAGE_SCORE', 20.0)

        # Content quality weights
        weights['content_length'] = self.config.get_int('CONTENT', 'MIN_WORDS', 400) * 0.01
        weights['content_tags'] = self.config.get_int('CONTENT', 'MAX_TAG_COUNT', 10) * 0.5
        weights['content_language'] = 1.0  # Language filtering weight
        
        # Engagement weights
        weights['engagement_votes'] = self.config.get_float('ENGAGEMENT', 'VOTE_COUNT_WEIGHT', 1.0)
        weights['engagement_comments'] = self.config.get_float('ENGAGEMENT', 'COMMENT_WEIGHT', 2.0)
        weights['engagement_value'] = self.config.get_float('ENGAGEMENT', 'VALUE_WEIGHT', 1.0)
        
        # Additional engagement factors (currently not implemented but prepared)
        weights['engagement_resteems'] = self.config.get_float('ENGAGEMENT', 'RESTEEM_WEIGHT', 0.0)
        weights['engagement_feed_reach'] = 0.1  # Placeholder for future implementation
        weights['engagement_downvotes'] = 0.5   # Penalty weight for downvotes
        
        # Component weights (Total Score calculation)
        weights['component_author'] = self.config.get_float('SCORING', 'COMPONENT_AUTHOR_WEIGHT', 0.4)
        weights['component_content'] = self.config.get_float('SCORING', 'COMPONENT_CONTENT_WEIGHT', 0.35)
        weights['component_engagement'] = self.config.get_float('SCORING', 'COMPONENT_ENGAGEMENT_WEIGHT', 0.25)
        
        return weights
    
    def _load_scoring_thresholds(self):
        """Load scoring thresholds from configuration."""
        thresholds = {}
        
        # Quality tiers
        thresholds['excellent_min'] = self.config.get_float('SCORING', 'TIER_EXCELLENT_MIN', 85.0)
        thresholds['good_min'] = self.config.get_float('SCORING', 'TIER_GOOD_MIN', 70.0)
        thresholds['fair_min'] = self.config.get_float('SCORING', 'TIER_FAIR_MIN', 55.0)
        thresholds['poor_min'] = self.config.get_float('SCORING', 'TIER_POOR_MIN', 40.0)
        
        # Engagement thresholds
        thresholds['min_vote_count'] = self.config.get_int('ENGAGEMENT', 'VOTE_COUNT_MIN', 10)
        thresholds['max_vote_count'] = self.config.get_int('ENGAGEMENT', 'VOTE_COUNT_MAX', 200)
        thresholds['min_value'] = self.config.get_float('ENGAGEMENT', 'VALUE_MIN', 0.25)
        thresholds['max_value'] = self.config.get_float('ENGAGEMENT', 'VALUE_MAX', 100.0)
        
        thresholds['min_comment_count'] = self.config.get_int('ENGAGEMENT', 'COMMENT_MIN', -10)
        thresholds['max_comment_count'] = self.config.get_int('ENGAGEMENT', 'COMMENT_MAX', 20)
        thresholds['min_resteem_count'] = self.config.get_int('ENGAGEMENT', 'RESTEEM_MIN', 2)
        thresholds['max_resteem_count'] = self.config.get_int('ENGAGEMENT', 'RESTEEM_MAX', 20)
        
        return thresholds
    
    def _parse_steem_date(self, date_val):
        """Helper to safely parse Steem API dates into naive datetime objects."""
        if isinstance(date_val, datetime):
            return date_val.replace(tzinfo=None)
            
        if not isinstance(date_val, str) or not date_val:
            return datetime.utcnow() - timedelta(days=3650)
            
        try:
            return datetime.strptime(date_val.replace('Z', ''), '%Y-%m-%dT%H:%M:%S')
        except Exception:
            return datetime.utcnow() - timedelta(days=3650)

    def _extract_tags(self, post):
        """Safely extract tags from post metadata."""
        try:
            if post.get('json_metadata'):
                if isinstance(post['json_metadata'], dict):
                    return post['json_metadata'].get('tags', [])
                elif isinstance(post['json_metadata'], str):
                    metadata = json.loads(post['json_metadata'])
                    return metadata.get('tags', [])
        except Exception:
            pass
        return []

    def score_content(self, post_data, content_data=None):
        """
        Score a piece of content across multiple dimensions.
        
        Args:
            post_data: Dictionary containing post information from blockchain
            content_data: Optional dictionary containing detailed post data (to avoid re-fetching)
            
        Returns:
            Dictionary containing total score, component scores, and quality tier
        """
        try:
            # Get detailed post information
            if content_data:
                post = content_data
            else:
                post = self.steem.get_content(post_data['author'], post_data['permlink'])
            
            # Calculate component scores
            author_score = self._score_author(post['author'])
            content_score = self._score_content(post)
            engagement_score = self._score_engagement(post)
            
            # Calculate weighted total score
            total_score = (
                author_score * self.weights['component_author'] +
                content_score * self.weights['component_content'] +
                engagement_score * self.weights['component_engagement']
            )
            
            # Determine quality tier
            quality_tier = self._determine_quality_tier(total_score)
            
            return {
                'total_score': round(total_score, 2),
                'quality_tier': quality_tier,
                'components': {
                    'author': round(author_score, 2),
                    'content': round(content_score, 2),
                    'engagement': round(engagement_score, 2)
                },
                'details': {
                    'author_reputation': post['author_reputation'],
                    'net_votes': post['net_votes'],
                    'pending_payout_value': post['pending_payout_value'],
                    'total_payout_value': post['total_payout_value'],
                    'children': post['children'],
                    'created': post['created'],
                    'tags': self._extract_tags(post)
                }
            }
            
        except Exception as e:
            logger.error(f"Error scoring content {post_data['author']}/{post_data['permlink']}: {e}")
            return {
                'total_score': 0.0,
                'quality_tier': 'error',
                'components': {'author': 0.0, 'content': 0.0, 'engagement': 0.0},
                'details': {'error': str(e)}
            }
    
    def _score_author(self, author):
        """Score author quality based on reputation, followers, and activity."""
        try:
            account = Account(author, steemd_instance=self.steem)
            
            # Basic author metrics
            reputation = account.rep
            # Optimization: Use get_follow_count instead of fetching the list (which is very slow for large accounts)
            follow_counts = self.steem.get_follow_count(author)
            followers = follow_counts['follower_count']
            following = follow_counts['following_count']
            
            # Calculate influence ratio with Laplace smoothing (small account boost)
            smoothed_followers = followers + 50
            smoothed_following = following + 50
            influence_ratio = smoothed_followers / smoothed_following
            
            # Check account age
            created_date = self._parse_steem_date(account.get('created'))
            account_age_days = (datetime.utcnow() - created_date).days
            
            # Check last activity
            last_activity_date = max(
                self._parse_steem_date(account.get('last_vote_time')),
                self._parse_steem_date(account.get('last_post')),
                self._parse_steem_date(account.get('last_root_post'))
            )
            last_activity_days = (datetime.utcnow() - last_activity_date).days
            
            # Author score components
            # Reputation is typically 25-80. 
            # Normalize: (Rep - 25) / 2. Example: Rep 75 -> max pts. Rep 25 -> 0 pts.
            # Ensure we don't go below 0 or above max.
            max_rep_score = self.weights.get('max_reputation_score', 25.0)
            reputation_score = min(max(0, (reputation - 25) / 2.0), max_rep_score)
            
            # Advanced follower metrics from authorValidation.py
            # 1. Followers per month (normalized)
            max_fpm_score = self.weights.get('max_followers_per_month_score', 20.0)
            followers_per_month = followersPerMonth(account, {'author': author}, steem_instance=self.steem, cached_count=followers)
            followers_per_month_score = min(followers_per_month * 2.0, max_fpm_score)
            
            # 2. Adjusted followers per month (with half-life decay)
            max_adj_fpm_score = self.weights.get('max_adjusted_followers_score', 25.0)
            adjusted_followers_per_month = adjustedFollowersPerMonth(account, {'author': author}, steem_instance=self.steem, cached_count=followers)
            adjusted_followers_score = min(adjusted_followers_per_month * 2.5, max_adj_fpm_score)
            
            # 3. Median follower reputation
            median_rep_score = 0.0
            if self.config.get_boolean('AUTHOR', 'ENABLE_MEDIAN_REP_SCORING', fallback=False):
                if author not in self.median_rep_cache:
                    self.median_rep_cache[author] = getMedianFollowerRep(author, steem_instance=self.steem)
                    
                median_follower_rep = self.median_rep_cache[author]
                if median_follower_rep is not None:
                    # Normalize median rep (expected range 30-60)
                    max_median_rep_score = self.weights.get('max_median_rep_score', 15.0)
                    median_rep_score = min(max(0.0, ((median_follower_rep - 30.0) / 30.0) * max_median_rep_score), max_median_rep_score)
            
            # 4. Account age score (older accounts get more trust)
            max_age_score = self.weights.get('max_age_score', 15.0)
            age_score = min(account_age_days / 100.0, max_age_score)
            
            # 5. Activity score (penalty for inactivity)
            max_activity_score = self.weights.get('max_activity_score', 15.0)
            activity_score = max(0, max_activity_score - (last_activity_days / 50.0))
            
            # 6. Influence Ratio score
            # A ratio of 1.0 is neutral (0 points). Scales up to max points at a 3.0 ratio.
            max_influence_score = self.weights.get('max_influence_score', 10.0)
            influence_score = (influence_ratio - 1.0) * (max_influence_score / 2.0)
            influence_score = max(-max_influence_score, min(influence_score, max_influence_score))
            
            # 7. Hive Inactivity score
            max_hive_inactivity_score = self.weights.get('max_hive_inactivity_score', 10.0)
            hive_inactivity_days = hiveInactiveDays(author)
            if hive_inactivity_days is not None:
                target_hive_inactivity = self.config.get_int('AUTHOR', 'TARGET_HIVE_INACTIVITY_DAYS', 60)
                hive_inactivity_score = min((hive_inactivity_days / max(1, target_hive_inactivity)) * max_hive_inactivity_score, max_hive_inactivity_score)
            else:
                hive_inactivity_score = max_hive_inactivity_score
            
            # Combined author score (max 100)
            author_score = (
                reputation_score + 
                followers_per_month_score + 
                adjusted_followers_score + 
                median_rep_score + 
                age_score + 
                activity_score + 
                influence_score +
                hive_inactivity_score
            )
            
            return max(0.0, min(author_score, 100.0))
            
        except AccountDoesNotExistsException:
            logger.warning(f"Author account {author} does not exist")
            return 0.0
        except Exception as e:
            logger.error(f"Error scoring author {author}: {e}")
            return 0.0
    
    def _score_content(self, post):
        """Score content quality based on length, tags, language, and other factors."""
        try:
            # Content length score
            # Use word count instead of character count
            clean_body = remove_formatting(post['body'])
            words = clean_body.split()
            word_count = len(words)
            title_length = len(post['title'])
            
            # Length scoring with optimal ranges
            max_length_score = self.weights.get('max_length_score', 30.0)
            base_length_score = max_length_score * (10.0 / 30.0)
            bonus_length_score = max_length_score - base_length_score
            
            length_score = 0.0
            if word_count >= 400:
                length_score = base_length_score + min((word_count - 400) / 20.0, bonus_length_score)
            elif word_count >= 100:
                length_score = (word_count - 100) / (300.0 / base_length_score)
            
            # Title quality score
            max_title_score = self.weights.get('max_title_score', 10.0)
            title_score = min(title_length / 5.0, max_title_score)
            
            # Tag quality score
            tags = self._extract_tags(post)
            tag_count = len(tags)
            max_tag_score = self.weights.get('max_tag_score', 15.0)
            tag_score = max(0, max_tag_score - abs(tag_count - 3) * 2.0)  # Optimal around 3 tags
            
            # Language detection (simplified - just check for common language patterns)
            language_score = self._score_language(clean_body)
            
            # Combined content score
            content_score = length_score + title_score + tag_score + language_score
            
            return min(content_score, 100.0)
            
        except Exception as e:
            logger.error(f"Error scoring content: {e}")
            return 0.0
    
    def _score_language(self, text):
        """Basic language quality scoring."""
        # Simple language detection based on character sets
        if not text:
            return 0.0
            
        try:
            # Ensure text is properly encoded and handle potential encoding issues
            if isinstance(text, bytes):
                # If text is bytes, decode it with error handling
                text = text.decode('utf-8', errors='ignore')
            elif isinstance(text, str):
                # If text is string, ensure it's clean UTF-8
                text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            else:
                # Convert other types to string
                text = str(text)
            
            # Check for basic readability (avoid pure spam/emoji posts)
            text_clean = re.sub(r'[^\w\s]', '', text.lower())
            words = text_clean.split()
            
            min_words = self.config.get_int('CONTENT', 'MIN_WORDS', 400)
            if len(words) < min_words:
                return 0.0  # Too short to evaluate language quality effectively
            
            # Check for excessive repetition (potential spam indicator)
            unique_words = set(words)
            repetition_ratio = len(unique_words) / len(words) if words else 0
            
            if repetition_ratio < 0.3:
                return 0.0  # Likely spam
            
            # Basic readability score
            avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
            max_language_score = self.weights.get('max_language_score', 20.0)
            readability_score = min(avg_word_length * 2, max_language_score)
            
            return readability_score
        except UnicodeEncodeError as e:
            logger.error(f"Unicode encoding error in language scoring: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Error in language scoring: {e}")
            return 0.0

    def _scale(self, value, min_val, max_val):
        """Scale a value to a 0-100 range based on provided min and max."""
        if value <= min_val:
            return 0.0
        elif value >= max_val:
            return 100.0
        else:
            # Avoid division by zero if min_val and max_val are the same
            if max_val - min_val == 0:
                return 100.0
            score = 100.0 * (value - min_val) / (max_val - min_val)
            return score

    def _score_engagement(self, post):
        """Score post engagement based on votes, comments, and value."""
        try:
            # Basic engagement metrics
            author = post['author']
            permlink = post['permlink']
            net_votes = post['net_votes']
            children = post['children']
            pending_payout = float(post['pending_payout_value'].split()[0])
            total_payout = float(post['total_payout_value'].split()[0])
            total_value = pending_payout + total_payout

            # Load scaling params and weights from pre-loaded config
            vote_min = self.thresholds['min_vote_count']
            vote_max = self.thresholds['max_vote_count']
            vote_weight = self.weights['engagement_votes']

            comment_min = self.thresholds['min_comment_count']
            comment_max = self.thresholds['max_comment_count']
            comment_weight = self.weights['engagement_comments']

            value_min = self.thresholds['min_value']
            value_max = self.thresholds['max_value']
            value_weight = self.weights['engagement_value']

            resteem_min = self.thresholds['min_resteem_count']
            resteem_max = self.thresholds['max_resteem_count']
            resteem_weight = self.weights['engagement_resteems']

            # Calculate scaled scores (0-100 for each component)
            vote_score_scaled = self._scale(net_votes, vote_min, vote_max)
            comment_score_scaled = self._scale(children, comment_min, comment_max)
            value_scaled = self._scale(total_value, value_min, value_max)
            resteem_count = get_resteem_count(author, permlink)
            resteem_score_scaled = self._scale(resteem_count, resteem_min, resteem_max)

            # Calculate weighted average
            total_weighted_score = (
                vote_score_scaled * vote_weight +
                comment_score_scaled * comment_weight +
                value_scaled * value_weight +
                resteem_score_scaled * resteem_weight
            )

            total_weight = vote_weight + comment_weight + value_weight + resteem_weight

            if total_weight == 0:
                return 0.0

            engagement_score = total_weighted_score / total_weight

            return min(engagement_score, 100.0)

        except Exception as e:
            logger.error(f"Error scoring engagement: {e}")
            return 0.0
    
    def _determine_quality_tier(self, total_score):
        """Determine quality tier based on total score."""
        if total_score >= self.thresholds['excellent_min']:
            return 'excellent'
        elif total_score >= self.thresholds['good_min']:
            return 'good'
        elif total_score >= self.thresholds['fair_min']:
            return 'fair'
        elif total_score >= self.thresholds['poor_min']:
            return 'poor'
        else:
            return 'reject'
    
    def should_curate(self, score_result):
        """Determine if content should be curated based on score and configuration."""
        quality_tier = score_result['quality_tier']
        
        # Get curation thresholds from config
        min_tier = self.config.get('BLOG', 'MIN_CURATION_TIER', 'fair').lower()
        
        # Define tier hierarchy
        tier_hierarchy = ['reject', 'poor', 'fair', 'good', 'excellent']
        
        try:
            min_tier_index = tier_hierarchy.index(min_tier)
            current_tier_index = tier_hierarchy.index(quality_tier)
            
            return current_tier_index >= min_tier_index
        except ValueError:
            # Invalid tier configuration, default to fair
            return quality_tier in ['fair', 'good', 'excellent']
    
    def get_ai_analysis_intensity(self, score_result):
        """
        Determine AI analysis intensity based on content quality.
        
        Returns:
            'detailed' for excellent content
            'standard' for good content  
            'light' for fair content
            'none' for poor/reject content
        """
        quality_tier = score_result['quality_tier']
        
        if quality_tier == 'excellent':
            return 'detailed'
        elif quality_tier == 'good':
            return 'standard'
        elif quality_tier == 'fair':
            return 'light'
        else:
            return 'none'
