import sqlite3
import os
from datetime import datetime, timedelta

class CurationHistory:
    def __init__(self, db_path="data/curation_history.db"):
        """
        Initializes the local SQLite database for tracking curated posts.
        Creates the necessary directory and table if they do not exist.
        """
        self.db_path = db_path
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS curated_posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    author TEXT NOT NULL,
                    permlink TEXT NOT NULL,
                    curated_at TIMESTAMP NOT NULL
                )
            ''')
            # Indexes for faster time and author based queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_author_time ON curated_posts(author, curated_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_post ON curated_posts(author, permlink)')
            conn.commit()

    def record_curation(self, author, permlink):
        """Records a newly curated post into the local database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO curated_posts (author, permlink, curated_at) VALUES (?, ?, ?)',
                (author, permlink, datetime.utcnow())
            )
            conn.commit()

    def get_author_curation_count(self, author, days):
        """Returns the number of times an author was curated in the last X days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) FROM curated_posts WHERE author = ? AND curated_at >= ?',
                (author, cutoff_date)
            )
            return cursor.fetchone()[0]

    def has_post_been_curated(self, author, permlink, days=30):
        """Checks if a specific post has been curated in the last X days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM curated_posts WHERE author = ? AND permlink = ? AND curated_at >= ? LIMIT 1',
                (author, permlink, cutoff_date)
            )
            return cursor.fetchone() is not None

    def cleanup_old_records(self, retain_days=30):
        """
        Deletes records older than retain_days to keep the database small.
        Should be called once per Thoth run.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retain_days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM curated_posts WHERE curated_at < ?', (cutoff_date,))
            conn.commit()