"""
Model Manager - Handles switching between multiple LLM models when rate limited.
"""

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ModelManager:
    """Manages a list of models and tracks which ones are currently rate limited."""
    
    def __init__(self, model_string):
        """
        Initialize with a model string (comma-separated list of models).
        
        Args:
            model_string: Either a single model name or comma-separated list
                         e.g., "gemini-2.5-pro,gemini-2.5-flash"
        """
        self.models = [m.strip() for m in model_string.split(',') if m.strip()]
        self.current_index = 0
        self.rate_limited_models = []
        
        if not self.models:
            raise ValueError("No models provided in model_string")
        
        logging.info(f"Initialized ModelManager with models: {self.models}")
    
    @property
    def current_model(self):
        """Get the currently active model."""
        return self.models[self.current_index]
    
    def get_model_prefix(self):
        """Get the prefix of the current model (e.g., 'gemini' from 'gemini-2.5-pro')."""
        return self.current_model.split('-')[0]
    
    def switch_to_next_model(self):
        """
        Switch to the next available model.
        
        Returns:
            bool: True if switched to a new model, False if already on the last model
        """
        if self.current_index < len(self.models) - 1:
            # Mark current as rate-limited before switching
            if self.models[self.current_index] not in self.rate_limited_models:
                self.rate_limited_models.append(self.models[self.current_index])
            self.current_index += 1
            logging.warning(
                f"Switching to next model: {self.current_model} "
                f"(Rate limited models: {self.rate_limited_models})"
            )
            return True
        else:
            logging.error(
                f"No more models available. All models rate limited: {self.rate_limited_models}"
            )
            return False

    def mark_rate_limited(self, dry_run=False):
        """
        Mark the current model as rate limited and optionally switch to the next model.

        Args:
            dry_run (bool): If True, record that the model is rate limited but do not
                            actually switch to the next model. Useful for observation
                            or dry-run modes.

        Returns:
            bool: True if an actual switch to the next model occurred, False otherwise.
        """
        # Avoid duplicate entries
        if self.current_model not in self.rate_limited_models:
            self.rate_limited_models.append(self.current_model)

        logging.warning(f"Marking model as rate limited: {self.current_model}. Dry run: {dry_run}")

        if dry_run:
            logging.info("Dry-run mode: not switching to next model.")
            return False

        # Switch without re-appending (already marked above)
        if self.current_index < len(self.models) - 1:
            self.current_index += 1
            logging.warning(
                f"Switching to next model: {self.current_model} "
                f"(Rate limited models: {self.rate_limited_models})"
            )
            return True
        else:
            logging.error(
                f"No more models available. All models rate limited: {self.rate_limited_models}"
            )
            return False
    
    def has_next_model(self):
        """Check if there's a next model available."""
        return self.current_index < len(self.models) - 1
    
    def get_models_used(self):
        """
        Get list of models that were actually used (rate-limited models + current model).
        
        Returns:
            list: List of models that have been tried or are currently active
        """
        used = self.rate_limited_models.copy()
        if self.current_model not in used:
            used.append(self.current_model)
        return used
    
    def reset(self):
        """Reset to the first model."""
        self.current_index = 0
        self.rate_limited_models = []
        logging.info("ModelManager reset to first model")

def parse_model_string(model_string):
    """
    Parse a model string and return a list of models.
    
    Args:
        model_string: Either a single model or comma-separated list
        
    Returns:
        list: List of model names
    """
    return [m.strip() for m in model_string.split(',') if m.strip()]
