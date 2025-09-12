from datetime import datetime, timedelta

class RetryManager:
    def __init__(self, max_retries=3, retry_intervals=None):
        """
        Initialize the retry manager.
        
        Args:
            max_retries (int): Maximum number of retry attempts
            retry_intervals (list): List of hours to wait between retries
        """
        self.max_retries = max_retries
        self.retry_intervals = retry_intervals or [1, 4, 24]  # Default: 1 hour, 4 hours, 24 hours
    
    def can_retry(self, current_retry_count):
        """
        Check if a lead can be retried.
        
        Args:
            current_retry_count (int): Current number of retry attempts
            
        Returns:
            bool: True if lead can be retried, False otherwise
        """
        return current_retry_count < self.max_retries
    
    def get_next_retry_time(self, current_retry_count):
        """
        Calculate the next retry time based on the current retry count.
        
        Args:
            current_retry_count (int): Current number of retry attempts (0-based)
            
        Returns:
            str: ISO format datetime string for next retry
        """
        # If this is the last allowed retry, no need to calculate next time
        if current_retry_count >= self.max_retries - 1:
            return None
        
        # Get the wait time in hours for this retry
        retry_index = current_retry_count
        if retry_index < len(self.retry_intervals):
            hours_to_add = self.retry_intervals[retry_index]
        else:
            # If we've gone beyond the defined intervals, use the last one
            hours_to_add = self.retry_intervals[-1]
        
        # Calculate and return the next retry time
        next_time = datetime.now() + timedelta(hours=hours_to_add)
        return next_time.isoformat()
    
    def should_trigger_fallback(self, current_retry_count):
        """
        Check if fallback communications should be triggered.
        
        Args:
            current_retry_count (int): Current number of retry attempts
            
        Returns:
            bool: True if fallback should be triggered, False otherwise
        """
        # Trigger fallback if we've reached the max retries
        return current_retry_count >= self.max_retries

