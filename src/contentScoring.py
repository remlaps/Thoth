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
from steem.account import AccountDoesNotExistsException

from configValidator import ConfigValidator
from utils import get_rng
from authorValidation import followersPerMonth, adjustedFollowersPerMonth, getMedianFollowerRep

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
                    'tags': post['json_metadata'].get('tags', []) if post['json_metadata'] and isinstance(post['json_metadata'], dict) else []
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
            # created_date may be returned as a string from the Steem API
            if isinstance(created_date, str):
                try:
                    # Accept ISO formats with or without trailing Z
                    if created_date.endswith('Z'):
                        created_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    else:
                        created_date = datetime.fromisoformat(created_date)
                except (ValueError, TypeError):
                    # Fallback to older strptime pattern
                    try:
                        created_date = datetime.strptime(created_date, '%Y-%m-%dT%H:%M:%S')
                    except Exception:
                        # If parsing fails entirely, treat as very old account
                        created_date = datetime.now() - timedelta(days=3650)
            account_age_days = (datetime.now() - created_date).days
            
            # Check last activity
            last_activity = max(
                account['last_vote_time'], 
                account['last_post'], 
                account['last_root_post']
            )
            
            # Ensure last_activity is a datetime object
            if isinstance(last_activity, str):
                try:
                    # Handle different timestamp formats from Steem API
                    # Format: "2026-03-04T12:25:13" or "2026-03-04T12:25:13Z"
                    if last_activity.endswith('Z'):
                        last_activity = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    else:
                        last_activity = datetime.fromisoformat(last_activity)
                except (ValueError, TypeError):
                    # If parsing fails, use a default old date to indicate inactivity
                    last_activity = datetime.now() - timedelta(days=3650)  # 10 years ago
            elif hasattr(last_activity, 'replace'):  # Already a datetime object
                pass
            else:
                # Fallback for unexpected types
                last_activity = datetime.now() - timedelta(days=3650)
            
            # Handle timezone-aware vs timezone-naive datetime comparison
            now = datetime.now()
            if hasattr(last_activity, 'tzinfo') and last_activity.tzinfo is not None:
                # If last_activity is timezone-aware, make now timezone-aware too
                from datetime import timezone
                now = datetime.now(timezone.utc)
            
            last_activity_days = (now - last_activity).days
            
            # Author score components
            # Reputation is typically 25-80. 
            # Normalize: (Rep - 25) / 2. Example: Rep 75 -> 25 pts. Rep 25 -> 0 pts.
            # Ensure we don't go below 0 or above 25.
            reputation_score = min(max(0, (reputation - 25) / 2.0), 25.0)
            
            # Advanced follower metrics from authorValidation.py
            # 1. Followers per month (normalized)
            followers_per_month = followersPerMonth(account, {'author': author}, steem_instance=self.steem)
            followers_per_month_score = min(followers_per_month * 2.0, 20.0)  # Max 20 points
            
            # 2. Adjusted followers per month (with half-life decay)
            adjusted_followers_per_month = adjustedFollowersPerMonth(account, {'author': author}, steem_instance=self.steem)
            adjusted_followers_score = min(adjusted_followers_per_month * 2.5, 25.0)  # Max 25 points
            
            # 3. Median follower reputation
            median_follower_rep = getMedianFollowerRep(author, steem_instance=self.steem)
            median_rep_score = 0.0
            if median_follower_rep is not None:
                # Normalize median rep (typically 0-80 range)
                median_rep_score = min(max(0, median_follower_rep / 4.0), 15.0)  # Max 15 points
            
            # 4. Account age score (older accounts get more trust)
            age_score = min(account_age_days / 100.0, 15.0)  # Reduced from 20 to 15 to make room for new metrics
            
            # 5. Activity score (penalty for inactivity)
            activity_score = max(0, 15.0 - (last_activity_days / 50.0))  # Reduced from 20 to 15
            
            # Combined author score (max 100)
            author_score = (
                reputation_score + 
                followers_per_month_score + 
                adjusted_followers_score + 
                median_rep_score + 
                age_score + 
                activity_score
            )
            
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
            # Use word count instead of character count
            words = post['body'].split()
            word_count = len(words)
            title_length = len(post['title'])
            
            # Length scoring with optimal ranges
            length_score = 0.0
            if word_count >= 400:
                length_score = min(word_count / 20.0, 30.0)  # Max 30 points (approx 600 words)
            elif word_count >= 100:
                length_score = word_count / 40.0  # Partial credit for shorter posts
            
            # Title quality score
            title_score = min(title_length / 5.0, 10.0)
            
            # Tag quality score
            tags = post['json_metadata'].get('tags', []) if post['json_metadata'] and isinstance(post['json_metadata'], dict) else []
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
        except UnicodeEncodeError as e:
            logger.error(f"Unicode encoding error in language scoring: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Error in language scoring: {e}")
            return 0.0
    
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
