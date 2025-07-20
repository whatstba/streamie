"""Background analysis queue for processing tracks."""

import asyncio
import sqlite3
import logging
import os
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AnalysisJob:
    """Represents a track analysis job."""

    id: Optional[int]
    filepath: str
    priority: int = 5
    status: str = "pending"
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class AnalysisQueue:
    """Manages background analysis of music tracks."""

    def __init__(self, db_path: str, max_workers: int = 4):
        self.db_path = db_path
        self.max_workers = max_workers
        self.workers: List[asyncio.Task] = []
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.progress: Dict[str, Dict] = {}
        self.running = False
        self._analyzer = None  # Will be set when starting

    async def start(self, analyzer):
        """Start the analysis queue workers."""
        self.running = True
        self._analyzer = analyzer

        # Load pending jobs from database
        await self._load_pending_jobs()

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        logger.info(f"Started {self.max_workers} analysis workers")

    async def stop(self):
        """Stop all workers gracefully."""
        self.running = False

        # Cancel all workers
        for worker in self.workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("Analysis queue stopped")

    async def add_track(self, filepath: str, priority: int = 5) -> int:
        """Add a track to the analysis queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Insert or update in database
            cursor.execute(
                """
                INSERT OR REPLACE INTO analysis_queue 
                (filepath, priority, status, created_at)
                VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
            """,
                (filepath, priority),
            )

            job_id = cursor.lastrowid
            conn.commit()

            # Add to in-memory queue
            await self.queue.put((priority, job_id, filepath))

            logger.info(f"Added track to analysis queue: {filepath}")
            return job_id

        finally:
            conn.close()

    async def add_folder(self, folder_path: str, priority: int = 5):
        """Add all audio files in a folder to the queue."""
        audio_extensions = {".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac"}
        added_count = 0

        for root, _, files in os.walk(folder_path):
            for filename in files:
                if any(filename.lower().endswith(ext) for ext in audio_extensions):
                    filepath = os.path.join(root, filename)
                    await self.add_track(filepath, priority)
                    added_count += 1

        logger.info(f"Added {added_count} tracks from {folder_path}")
        return added_count

    async def get_status(self) -> Dict:
        """Get current queue status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT status, COUNT(*) 
                FROM analysis_queue 
                GROUP BY status
            """)

            status_counts = dict(cursor.fetchall())

            return {
                "pending": status_counts.get("pending", 0),
                "processing": status_counts.get("processing", 0),
                "completed": status_counts.get("completed", 0),
                "failed": status_counts.get("failed", 0),
                "total": sum(status_counts.values()),
                "workers": len(self.workers),
                "running": self.running,
            }

        finally:
            conn.close()

    async def get_progress(self, filepath: str) -> Optional[Dict]:
        """Get progress for a specific track."""
        return self.progress.get(filepath)

    async def _load_pending_jobs(self):
        """Load pending jobs from database into queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Reset any 'processing' jobs to 'pending' (in case of crash)
            cursor.execute("""
                UPDATE analysis_queue 
                SET status = 'pending' 
                WHERE status = 'processing'
            """)

            # Load all pending jobs
            cursor.execute("""
                SELECT id, filepath, priority 
                FROM analysis_queue 
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
            """)

            jobs = cursor.fetchall()
            conn.commit()

            # Add to queue
            for job_id, filepath, priority in jobs:
                await self.queue.put((priority, job_id, filepath))

            logger.info(f"Loaded {len(jobs)} pending jobs")

        finally:
            conn.close()

    async def _worker(self, worker_name: str):
        """Worker coroutine that processes jobs from the queue."""
        logger.info(f"{worker_name} started")

        while self.running:
            try:
                # Get job from queue (with timeout to check running status)
                priority, job_id, filepath = await asyncio.wait_for(
                    self.queue.get(), timeout=1.0
                )

                # Process the job
                await self._process_job(job_id, filepath, worker_name)

            except asyncio.TimeoutError:
                continue  # Check if still running
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"{worker_name} error: {e}")

        logger.info(f"{worker_name} stopped")

    async def _process_job(self, job_id: int, filepath: str, worker_name: str):
        """Process a single analysis job."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Mark as processing
            cursor.execute(
                """
                UPDATE analysis_queue 
                SET status = 'processing', started_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """,
                (job_id,),
            )
            conn.commit()

            logger.info(f"{worker_name} analyzing: {filepath}")

            # Update progress
            self.progress[filepath] = {
                "status": "analyzing",
                "worker": worker_name,
                "started_at": datetime.now().isoformat(),
            }

            # Run the analysis
            if self._analyzer:
                success = await self._analyzer.analyze_file(filepath)
            else:
                # Fallback for testing
                await asyncio.sleep(2)  # Simulate analysis
                success = True

            if success:
                # Mark as completed
                cursor.execute(
                    """
                    UPDATE analysis_queue 
                    SET status = 'completed', 
                        completed_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """,
                    (job_id,),
                )

                # Also update tracks table
                cursor.execute(
                    """
                    UPDATE tracks 
                    SET analysis_status = 'completed' 
                    WHERE filepath = ?
                """,
                    (os.path.relpath(filepath),),
                )

                self.progress[filepath]["status"] = "completed"
                logger.info(f"{worker_name} completed: {filepath}")

            else:
                raise Exception("Analysis failed")

        except Exception as e:
            # Mark as failed
            cursor.execute(
                """
                UPDATE analysis_queue 
                SET status = 'failed', 
                    error_message = ?,
                    retry_count = retry_count + 1
                WHERE id = ?
            """,
                (str(e), job_id),
            )

            self.progress[filepath] = {"status": "failed", "error": str(e)}

            logger.error(f"{worker_name} failed on {filepath}: {e}")

        finally:
            conn.commit()
            conn.close()

            # Clean up old progress entries
            if len(self.progress) > 100:
                # Keep only recent entries
                sorted_entries = sorted(
                    self.progress.items(),
                    key=lambda x: x[1].get("started_at", ""),
                    reverse=True,
                )
                self.progress = dict(sorted_entries[:50])

    async def retry_failed(self, max_retries: int = 3):
        """Retry failed jobs up to max_retries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                SELECT id, filepath, priority 
                FROM analysis_queue 
                WHERE status = 'failed' AND retry_count < ?
            """,
                (max_retries,),
            )

            failed_jobs = cursor.fetchall()

            # Reset status and add back to queue
            for job_id, filepath, priority in failed_jobs:
                cursor.execute(
                    """
                    UPDATE analysis_queue 
                    SET status = 'pending' 
                    WHERE id = ?
                """,
                    (job_id,),
                )

                await self.queue.put((priority, job_id, filepath))

            conn.commit()
            logger.info(f"Retrying {len(failed_jobs)} failed jobs")

        finally:
            conn.close()
