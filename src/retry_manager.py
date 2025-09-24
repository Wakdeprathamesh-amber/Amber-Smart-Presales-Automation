from datetime import datetime, timedelta

class RetryManager:
    def __init__(self, max_retries=3, retry_intervals=None, interval_unit='hours'):
        """
        Initialize the retry manager.
        
        Args:
            max_retries (int): Maximum number of retry attempts
            retry_intervals (list): List of wait times between retries
            interval_unit (str): 'hours' or 'minutes'
        """
        self.max_retries = max_retries
        # Defaults: 30 minutes then 24 hours
        self.retry_intervals = retry_intervals or [0.5, 24]
        self.interval_unit = (interval_unit or 'hours').lower()
    
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
        
        # Get the wait time for this retry
        retry_index = current_retry_count
        if retry_index < len(self.retry_intervals):
            amount_to_add = self.retry_intervals[retry_index]
        else:
            # If we've gone beyond the defined intervals, use the last one
            amount_to_add = self.retry_intervals[-1]
        
        # Calculate and return the next retry time
        if self.interval_unit == 'minutes':
            next_time = datetime.now() + timedelta(minutes=amount_to_add)
        else:
            next_time = datetime.now() + timedelta(hours=amount_to_add)
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

