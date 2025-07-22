"""
Analysis Service for background audio processing and task management.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import json
import sqlite3
import os

from utils.enhanced_analyzer import EnhancedTrackAnalyzer
from utils.librosa import analyze_track
import numpy as np

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisTask:
    task_id: str
    filepath: str
    priority: int
    deck_id: Optional[str]
    analysis_type: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    results: Optional[Dict] = None


class AnalysisService:
    """Service for managing and executing audio analysis tasks."""

    def __init__(self, db_path: str, max_workers: int = 2):
        self.db_path = db_path
        self.max_workers = max_workers
        self.tasks: Dict[str, AnalysisTask] = {}
        self.task_queue = asyncio.PriorityQueue()
        self.workers = []
        self.running = False
        self.analyzer = EnhancedTrackAnalyzer(db_path)
        self._cache = {}  # Simple in-memory cache

    async def start(self):
        """Start the analysis service and worker tasks."""
        if self.running:
            return

        self.running = True
        logger.info(f"🚀 Starting analysis service with {self.max_workers} workers")

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self.workers.append(worker)

    async def stop(self):
        """Stop the analysis service."""
        logger.info("🛑 Stopping analysis service...")
        self.running = False

        # Cancel all workers
        for worker in self.workers:
            if not worker.done():
                worker.cancel()

        # Wait for workers to finish with timeout
        if self.workers:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.workers, return_exceptions=True),
                    timeout=5.0,  # 5 second timeout
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ Some workers did not stop cleanly within timeout")

        self.workers.clear()

        # Clear the queue
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        logger.info("🛑 Analysis service stopped")

    async def enqueue_analysis(
        self,
        filepath: str,
        priority: int = 2,
        deck_id: Optional[str] = None,
        analysis_type: str = "full",
    ) -> str:
        """Add a track to the analysis queue."""
        # Check if already analyzed (cache hit)
        if filepath in self._cache:
            logger.info(f"📋 Using cached analysis for {filepath}")
            return self._cache[filepath]["task_id"]

        # Create new task
        task_id = str(uuid.uuid4())
        task = AnalysisTask(
            task_id=task_id,
            filepath=filepath,
            priority=priority,
            deck_id=deck_id,
            analysis_type=analysis_type,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
        )

        self.tasks[task_id] = task

        # Add to priority queue (lower number = higher priority)
        await self.task_queue.put((priority, task_id))

        logger.info(f"📥 Enqueued analysis task {task_id} for {filepath}")
        return task_id

    async def get_task_status(self, task_id: str) -> Dict:
        """Get the status of an analysis task."""
        task = self.tasks.get(task_id)
        if not task:
            return {"status": "unknown", "error": "Task not found"}

        result = {
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
            "deck_id": task.deck_id,
        }

        if task.started_at:
            result["started_at"] = task.started_at.isoformat()

        if task.completed_at:
            result["completed_at"] = task.completed_at.isoformat()
            result["duration"] = (task.completed_at - task.started_at).total_seconds()

        if task.error:
            result["error"] = task.error

        if task.results:
            result["results"] = task.results

        return result

    async def get_cached_analysis(self, filepath: str) -> Dict:
        """Get cached analysis results for a track."""
        # Check memory cache
        if filepath in self._cache:
            return self._cache[filepath]["results"]

        # Check database
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT bpm, key, camelot_key, energy_level, energy_profile,
                       spectral_centroid, danceability, beat_times, hot_cues
                FROM tracks
                WHERE filepath = ?
            """,
                (filepath,),
            )

            row = cursor.fetchone()
            conn.close()

            if row and row["bpm"]:  # Has analysis data
                results = dict(row)
                # Parse JSON fields
                if results.get("beat_times"):
                    results["beat_times"] = json.loads(results["beat_times"])
                if results.get("hot_cues"):
                    results["hot_cues"] = json.loads(results["hot_cues"])
                if results.get("energy_profile"):
                    results["energy_profile"] = json.loads(results["energy_profile"])

                # Cache for future use
                self._cache[filepath] = {"task_id": "cached", "results": results}

                return results
        except Exception as e:
            logger.error(f"Error getting cached analysis: {e}")

        # No cached data available
        return {}

    async def _worker(self, worker_id: int):
        """Worker task that processes analysis jobs from the queue."""
        logger.info(f"🔧 Worker {worker_id} started")

        try:
            while self.running:
                try:
                    # Get task from queue (with timeout to allow checking self.running)
                    priority, task_id = await asyncio.wait_for(
                        self.task_queue.get(), timeout=1.0
                    )

                    task = self.tasks.get(task_id)
                    if not task:
                        continue

                    # Update task status
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.utcnow()

                    logger.info(f"🔬 Worker {worker_id} processing {task.filepath}")

                    # Perform analysis
                    try:
                        if task.analysis_type == "realtime":
                            results = await self._analyze_realtime(task.filepath)
                        else:
                            results = await self._analyze_full(task.filepath)

                        task.results = results
                        task.status = TaskStatus.COMPLETED

                        # Cache results
                        self._cache[task.filepath] = {
                            "task_id": task_id,
                            "results": results,
                        }

                        logger.info(
                            f"✅ Worker {worker_id} completed analysis for {task.filepath}"
                        )

                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        logger.error(f"❌ Worker {worker_id} failed: {e}")

                    finally:
                        task.completed_at = datetime.utcnow()

                except asyncio.TimeoutError:
                    # Timeout is expected - continue to check if still running
                    continue
                except asyncio.CancelledError:
                    # Task was cancelled - exit gracefully
                    logger.info(f"🛑 Worker {worker_id} cancelled")
                    break
                except Exception as e:
                    logger.error(f"Worker {worker_id} unexpected error: {e}")
                    # Continue working unless explicitly stopped
                    if not self.running:
                        break

        except Exception as e:
            logger.error(f"Worker {worker_id} critical error: {e}")
        finally:
            logger.info(f"🛑 Worker {worker_id} stopped")

    async def _analyze_realtime(self, filepath: str) -> Dict:
        """Perform real-time optimized analysis."""
        # Quick analysis for real-time use
        results = {}

        try:
            # Basic BPM and beat detection using librosa
            analysis = await asyncio.to_thread(analyze_track, filepath)
            results.update(analysis)

            # Get additional metadata from database if available
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT key, camelot_key, energy_level, genre
                FROM tracks
                WHERE filepath = ?
            """,
                (filepath,),
            )

            row = cursor.fetchone()
            if row:
                results["key"] = row[0]
                results["camelot_key"] = row[1]
                results["energy_level"] = row[2]
                results["genre"] = row[3]

            conn.close()

            # Quick structure detection (simplified)
            if "beat_times" in results and results["beat_times"]:
                beats = results["beat_times"]
                results["structure"] = {
                    "intro_end": beats[64] if len(beats) > 64 else 0,  # 16 bars
                    "outro_start": beats[-128]
                    if len(beats) > 128
                    else beats[-1],  # 32 bars from end
                }

        except Exception as e:
            logger.error(f"Real-time analysis error: {e}")
            results["error"] = str(e)

        return results

    async def _analyze_full(self, filepath: str) -> Dict:
        """Perform comprehensive analysis."""
        try:
            # Use enhanced analyzer for full analysis
            # Run in thread pool to avoid blocking
            success = await asyncio.to_thread(self.analyzer.analyze_file, filepath)

            if success:
                # Get results from database
                return await self.get_cached_analysis(filepath)
            else:
                # Fallback to basic analysis
                return await self._analyze_realtime(filepath)

        except Exception as e:
            logger.error(f"Full analysis error: {e}")
            return {"error": str(e)}

    def get_queue_status(self) -> Dict:
        """Get current queue statistics."""
        pending_count = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.PENDING
        )
        processing_count = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.PROCESSING
        )
        completed_count = sum(
            1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED
        )

        return {
            "pending": pending_count,
            "processing": processing_count,
            "completed": completed_count,
            "failed": sum(
                1 for t in self.tasks.values() if t.status == TaskStatus.FAILED
            ),
            "total": len(self.tasks),
            "queue_size": self.task_queue.qsize(),
            "workers": len(self.workers),
            "running": self.running,
        }
