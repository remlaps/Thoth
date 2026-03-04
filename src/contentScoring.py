"""
Content Quality Scoring System for Thoth

This module implements a comprehensive content quality scoring system that replaces
the binary accept/reject screening with a multi-dimensional scoring approach.
"""

import re
import math
from datetime import datetime, timedelta
import logging

from steem import Steem
from steem.account import Account
from steem.post import Post
from steem.exceptions import AccountDoesNotExistsException

from configValidator import ConfigValidator
from utils import get_rng

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
        
    def _load_scoring_weights(self):
        """Load scoring weights from configuration."""
        weights = {}
        
        # Author quality weights
        weights['author_reputation'] = self.config.get_float('AUTHOR', 'MIN_REPUTATION', 6.0) * 0.1
        weights['author_followers'] = self.config.get_int('AUTHOR', 'MIN_FOLLOWERS', 350) * 0.001
        weights['author_activity'] = self.config.get_int('AUTHOR', 'MAX_INACTIVITY_DAYS', 4000) * 0.001
        weights['author_median_rep'] = self.config.get_int('AUTHOR', 'MIN_FOLLOWER_MEDIAN_REP', 40) * 0.1
        
        # Content quality weights
        weights['content_length'] = self.config.get_int('CONTENT', 'MIN_WORDS', 400) * 0.01
        weights['content_tags'] = self.config.get_int('CONTENT', 'MAX_TAG_COUNT', 10) * 0.5
        weights['content_language'] = 1.0  # Language filtering weight
        
        # Engagement weights
        weights['engagement_votes'] = self.config.get_float('ENGAGEMENT', 'VOTE_COUNT_WEIGHT', 1.0)
        weights['engagement_comments'] = self.config.get_float('ENGAGEMENT', 'COMMENT_WEIGHT', 2.0)
        weights['engagement_value'] = self.config.get_float('ENGAGEMENT', 'VALUE_WEIGHT', 1.0)
        
        # Additional engagement factors (currently not implemented but prepared)
        weights['engagement_resteeems'] = self.config.get_float('ENGAGEMENT', 'RESTEEM_WEIGHT', 0.0)
        weights['engagement_feed_reach'] = 0.1  # Placeholder for future implementation
        weights['engagement_downvotes'] = 0.5   # Penalty weight for downvotes
        
        return weights
    
    def _load_scoring_thresholds(self):
        """Load scoring thresholds from configuration."""
        thresholds = {}
        
        # Quality tiers
        thresholds['excellent_min'] = 85.0
        thresholds['good_min'] = 70.0
        thresholds['fair_min'] = 55.0
        thresholds['poor_min'] = 40.0
        
        # Engagement thresholds
        thresholds['min_vote_count'] = self.config.get_int('ENGAGEMENT', 'VOTE_COUNT_MIN', 10)
        thresholds['max_vote_count'] = self.config.get_int('ENGAGEMENT', 'VOTE_COUNT_MAX', 200)
        thresholds['min_value'] = self.config.get_float('ENGAGEMENT', 'VALUE_MIN', 0.25)
        thresholds['max_value'] = self.config.get_float('ENGAGEMENT', 'VALUE_MAX', 100.0)
        
        return thresholds
    
    def score_content(self, post_data):
        """
        Score a piece of content across multiple dimensions.
        
        Args:
            post_data: Dictionary containing post information from blockchain
            
        Returns:
            Dictionary containing total score, component scores, and quality tier
        """
        try:
            # Get detailed post information
            post = self.steem.get_content(post_data['author'], post_data['permlink'])
            
            # Calculate component scores
            author_score = self._score_author(post['author'])
            content_score = self._score_content(post)
            engagement_score = self._score_engagement(post)
            
            # Calculate weighted total score
            total_score = (
                author_score * 0.4 +    # 40% author quality
                content_score * 0.35 +  # 35% content quality  
                engagement_score * 0.25 # 25% engagement
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
                    'tags': post['json_metadata'].get('tags', []) if post['json_metadata'] else []
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
            followers = len(account.get_followers())
            following = len(account.get_following())
            
            # Calculate adjusted followers (followers - following to account for spam follows)
            adjusted_followers = max(0, followers - following)
            
            # Check account age
            created_date = account['created']
            account_age_days = (datetime.now() - created_date).days
            
            # Check last activity
            last_activity = max(
                account['last_vote_time'], 
                account['last_post'], 
                account['last_root_post']
            )
            last_activity_days = (datetime.now() - last_activity).days
            
            # Author score components
            reputation_score = min(reputation / 10.0, 25.0)  # Cap at 25 points
            
            # Followers score with diminishing returns
            followers_score = min(math.log10(max(adjusted_followers, 1)) * 5, 25.0)
            
            # Account age score (older accounts get more trust)
            age_score = min(account_age_days / 100.0, 20.0)
            
            # Activity score (penalty for inactivity)
            activity_score = max(0, 20.0 - (last_activity_days / 50.0))
            
            # Combined author score (max 100)
            author_score = reputation_score + followers_score + age_score + activity_score
            
            return min(author_score, 100.0)
            
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
            body_length = len(post['body'])
            title_length = len(post['title'])
            
            # Length scoring with optimal ranges
            length_score = 0.0
            if body_length >= 400:
                length_score = min(body_length / 40.0, 30.0)  # Max 30 points for length
            elif body_length >= 100:
                length_score = body_length / 80.0  # Partial credit for shorter posts
            
            # Title quality score
            title_score = min(title_length / 5.0, 10.0)
            
            # Tag quality score
            tags = post['json_metadata'].get('tags', []) if post['json_metadata'] else []
            tag_count = len(tags)
            tag_score = max(0, 15.0 - abs(tag_count - 3) * 2.0)  # Optimal around 3 tags
            
            # Language detection (simplified - just check for common language patterns)
            language_score = self._score_language(post['body'])
            
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
            
        # Check for basic readability (avoid pure spam/emoji posts)
        text_clean = re.sub(r'[^\w\s]', '', text.lower())
        words = text_clean.split()
        
        if len(words) < 50:
            return 0.0  # Too short
        
        # Check for excessive repetition (potential spam indicator)
        unique_words = set(words)
        repetition_ratio = len(unique_words) / len(words) if words else 0
        
        if repetition_ratio < 0.3:
            return 0.0  # Likely spam
        
        # Basic readability score
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0
        readability_score = min(avg_word_length * 2, 20.0)
        
        return readability_score
    
    def _score_engagement(self, post):
        """Score post engagement based on votes, comments, and value."""
        try:
            # Basic engagement metrics
            net_votes = post['net_votes']
            children = post['children']
            pending_payout = float(post['pending_payout_value'].split()[0])
            total_payout = float(post['total_payout_value'].split()[0])
            
            # Engagement score components
            vote_score = min(net_votes * 0.5, 30.0)  # Max 30 points from votes
            
            comment_score = min(children * 2.0, 20.0)  # Max 20 points from comments
            
            # Value score (combined pending + total payout)
            value_score = min((pending_payout + total_payout) * 2.0, 30.0)
            
            # Combined engagement score
            engagement_score = vote_score + comment_score + value_score
            
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
