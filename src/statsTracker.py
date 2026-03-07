import numpy as np
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class StatsTracker:
    """A class to track and report statistics for the content screening process."""

    def __init__(self):
        self.total_evaluated = 0
        self.rejection_counts = defaultdict(int)
        self.rejected_scores = []
        self.accepted_scores = []
        self.accepted_by_tier = defaultdict(int)
        logger.info("StatsTracker initialized.")

    def track_evaluation(self):
        """Increment the total number of posts evaluated."""
        self.total_evaluated += 1

    def track_rejection(self, rule_type, score=None):
        """
        Track a rejected post.

        Args:
            rule_type (str): The type of rule that caused the rejection.
            score (float, optional): The score of the post if it was rejected by score.
        """
        self.rejection_counts[rule_type] += 1
        if rule_type == 'score_rejected' and score is not None:
            self.rejected_scores.append(score)

    def track_acceptance(self, score, quality_tier):
        """
        Track an accepted post.

        Args:
            score (float): The final score of the accepted post.
            quality_tier (str): The quality tier of the accepted post.
        """
        self.accepted_scores.append(score)
        self.accepted_by_tier[quality_tier] += 1

    def _calculate_stats(self, scores):
        """Helper function to calculate min, max, mean, and median for a list of scores."""
        if not scores:
            return {'min': 0, 'max': 0, 'mean': 0, 'median': 0, 'count': 0}
        
        scores_np = np.array(scores)
        return {
            'min': round(np.min(scores_np), 2),
            'max': round(np.max(scores_np), 2),
            'mean': round(np.mean(scores_np), 2),
            'median': round(np.median(scores_np), 2),
            'count': len(scores)
        }

    def generate_report(self):
        """Generate and return a formatted string of the run statistics."""
        report = []
        report.append("\n" + "="*50)
        report.append(" Curation Run Statistics ".center(50, "="))
        report.append("="*50)

        total_accepted = len(self.accepted_scores)
        total_rejected_by_rule = sum(v for k, v in self.rejection_counts.items() if k != 'score_rejected')
        total_rejected_by_score = len(self.rejected_scores)
        total_rejected = total_rejected_by_rule + total_rejected_by_score

        report.append(f"\nTotal Posts Evaluated: {self.total_evaluated}")
        report.append(f"Total Posts Accepted for Curation: {total_accepted}")
        report.append(f"Total Posts Rejected: {total_rejected}")
        
        acceptance_rate = (total_accepted / self.total_evaluated * 100) if self.total_evaluated > 0 else 0
        report.append(f"Acceptance Rate: {acceptance_rate:.2f}%")

        report.append("\n--- Rejection Details ---")
        report.append(f"Rejected by Rule: {total_rejected_by_rule}")
        if total_rejected_by_rule > 0:
            for rule, count in sorted(self.rejection_counts.items()):
                if rule != 'score_rejected':
                    report.append(f"  - {rule}: {count}")
        
        report.append(f"\nRejected by Score Threshold: {total_rejected_by_score}")
        rejected_score_stats = self._calculate_stats(self.rejected_scores)
        if rejected_score_stats['count'] > 0:
            report.append(f"  - Score Stats (Rejected): Min: {rejected_score_stats['min']}, Max: {rejected_score_stats['max']}, Mean: {rejected_score_stats['mean']}, Median: {rejected_score_stats['median']}")

        report.append("\n--- Acceptance Details ---")
        report.append(f"Accepted by Tier:")
        for tier, count in sorted(self.accepted_by_tier.items(), key=lambda item: item[1], reverse=True):
            report.append(f"  - {tier.capitalize()}: {count}")

        accepted_score_stats = self._calculate_stats(self.accepted_scores)
        if accepted_score_stats['count'] > 0:
            report.append(f"\n  - Score Stats (Accepted): Min: {accepted_score_stats['min']}, Max: {accepted_score_stats['max']}, Mean: {accepted_score_stats['mean']}, Median: {accepted_score_stats['median']}")

        report.append("\n" + "="*50)
        
        return "\n".join(report)