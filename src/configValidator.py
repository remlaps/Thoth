import configparser
import os
from typing import Tuple

class ConfigValidator:
    def __init__(self, config_file: str = r'config\config.ini'):
        """
        Initialize the ConfigValidator with the path to the config file.
        
        Args:
            config_file (str): Path to the configuration file
        """
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.errors = []
    
    def validate_config(self) -> bool:
        """
        Validate the configuration file and environment variables.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        self.errors = []  # Reset errors list
        
        try:
            # Read the config file
            self.config.read(self.config_file)
        except Exception as e:
            self.errors.append(f"Error reading config file: {str(e)}")
            return False
        
        # Validate all requirements
        self._validate_steem_section()
        self._validate_arliai_section()  # Now includes API key validation
        self._validate_blog_section()
        
        return len(self.errors) == 0
    
    def get_errors(self) -> list:
        """
        Get list of validation errors.
        
        Returns:
            list: List of error messages
        """
        return self.errors
    
    def get(self, section: str, key: str, fallback: str = '') -> str:
        """Get a configuration value with fallback."""
        return self.config.get(section, key, fallback=fallback).strip()
    
    def get_int(self, section: str, key: str, fallback: int = 0) -> int:
        """Get an integer configuration value with fallback."""
        try:
            return self.config.getint(section, key, fallback=fallback)
        except (ValueError, configparser.NoOptionError):
            return fallback
    
    def get_float(self, section: str, key: str, fallback: float = 0.0) -> float:
        """Get a float configuration value with fallback."""
        try:
            return self.config.getfloat(section, key, fallback=fallback)
        except (ValueError, configparser.NoOptionError):
            return fallback
    
    def _validate_steem_section(self) -> None:
        """Validate STEEM section requirements."""
        # Requirement 1: POSTING_ACCOUNT must be set
        posting_account = self.config.get('STEEM', 'POSTING_ACCOUNT', fallback='').strip()
        if not posting_account:
            self.errors.append("[STEEM] POSTING_ACCOUNT must be set")
        
        # Requirement 1: UNLOCK environment variable OR POSTING_KEY must be set
        unlock_env = os.environ.get('UNLOCK', '').strip()
        posting_key = self.config.get('STEEM', 'POSTING_KEY', fallback='').strip()
        
        if not unlock_env and not posting_key:
            self.errors.append("Either UNLOCK environment variable or [STEEM] POSTING_KEY must be set")
    
    def _validate_arliai_section(self) -> None:
        """Validate ARLIAI section requirements."""
        # Requirement 2: ARLIAI_MODEL must be set
        arliai_model = self.config.get('ARLIAI', 'ARLIAI_MODEL', fallback='').strip()
        if not arliai_model:
            self.errors.append("[ARLIAI] ARLIAI_MODEL must be set")
        
        # Requirement 3: ARLIAI_URL must be set
        arliai_url = self.config.get('ARLIAI', 'ARLIAI_URL', fallback='').strip()
        if not arliai_url:
            self.errors.append("[ARLIAI] ARLIAI_URL must be set")
        
        # Requirement 7: LLMAPIKEY environment variable OR ARLIAI_KEY must be set
        llm_api_key_env = os.environ.get('LLMAPIKEY', '').strip()
        arliai_key = self.config.get('ARLIAI', 'ARLIAI_KEY', fallback='').strip()
        
        if not llm_api_key_env and not arliai_key:
            self.errors.append("Either LLMAPIKEY environment variable or [ARLIAI] ARLIAI_KEY must be set")
    
    def _validate_blog_section(self) -> None:
        """Validate BLOG section requirements."""
        try:
            # Get values from config
            posting_account_weight = self.config.getint('BLOG', 'POSTING_ACCOUNT_WEIGHT', fallback=0)
            num_delegators = self.config.getint('BLOG', 'NUMBER_OF_DELEGATORS_PER_POST', fallback=0)
            num_reviewed_posts = self.config.getint('BLOG', 'NUMBER_OF_REVIEWED_POSTS', fallback=0)
            delegator_weight = self.config.getint('BLOG', 'DELEGATOR_WEIGHT', fallback=0)
            curated_author_weight = self.config.getint('BLOG', 'CURATED_AUTHOR_WEIGHT', fallback=0)
            
            # Requirement 4: If POSTING_ACCOUNT_WEIGHT is zero, sum must be < 9
            if posting_account_weight == 0:
                if num_delegators + num_reviewed_posts >= 9:
                    self.errors.append(
                        "When [BLOG] POSTING_ACCOUNT_WEIGHT is zero, "
                        "NUMBER_OF_DELEGATORS_PER_POST + NUMBER_OF_REVIEWED_POSTS must be less than 9"
                    )
            
            # Requirement 5: If POSTING_ACCOUNT_WEIGHT > 0, sum must be < 8
            elif posting_account_weight > 0:
                if num_delegators + num_reviewed_posts >= 8:
                    self.errors.append(
                        "When [BLOG] POSTING_ACCOUNT_WEIGHT is greater than zero, "
                        "NUMBER_OF_DELEGATORS_PER_POST + NUMBER_OF_REVIEWED_POSTS must be less than 8"
                    )
            
            # Requirement 6: Total weight calculation must be <= 10000
            total_weight = (
                num_delegators * delegator_weight + 
                num_reviewed_posts * curated_author_weight + 
                posting_account_weight
            )
            
            if total_weight > 10000:
                self.errors.append(
                    f"[BLOG] Total weight calculation exceeds 10000: "
                    f"({num_delegators} * {delegator_weight} + "
                    f"{num_reviewed_posts} * {curated_author_weight} + "
                    f"{posting_account_weight}) = {total_weight}"
                )
                
            # Validate MIN_CURATION_TIER if present
            min_curation_tier = self.config.get('BLOG', 'MIN_CURATION_TIER', fallback='').strip().lower()
            if min_curation_tier and min_curation_tier not in ['excellent', 'good', 'fair', 'poor', 'reject']:
                self.errors.append(
                    f"[BLOG] MIN_CURATION_TIER must be one of: excellent, good, fair, poor, reject. Got: {min_curation_tier}"
                )
                
        except ValueError as e:
            self.errors.append(f"Error parsing BLOG section numeric values: {str(e)}")
