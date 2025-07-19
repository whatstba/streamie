-- Migration: Add music folder management and enhanced metadata fields
-- This migration adds support for configurable music folders and additional track metadata

-- Music folder management
CREATE TABLE IF NOT EXISTS music_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    enabled BOOLEAN DEFAULT 1,
    last_scan TIMESTAMP,
    auto_scan BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add analysis status and enhanced metadata to tracks table
-- Note: SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
-- We'll handle column existence checking in the migration runner code

-- Hot cues and structure data
ALTER TABLE tracks ADD COLUMN hot_cues TEXT; -- JSON array of cues from Serato
ALTER TABLE tracks ADD COLUMN auto_cues TEXT; -- JSON array of auto-detected cues
ALTER TABLE tracks ADD COLUMN has_serato_data BOOLEAN DEFAULT 0;

-- Key detection
ALTER TABLE tracks ADD COLUMN key TEXT; -- e.g., "C major", "A minor"
ALTER TABLE tracks ADD COLUMN key_confidence REAL; -- 0.0-1.0
ALTER TABLE tracks ADD COLUMN camelot_key TEXT; -- e.g., "8B", "5A"

-- Song structure
ALTER TABLE tracks ADD COLUMN intro_start REAL;
ALTER TABLE tracks ADD COLUMN intro_end REAL;
ALTER TABLE tracks ADD COLUMN outro_start REAL;
ALTER TABLE tracks ADD COLUMN outro_end REAL;
ALTER TABLE tracks ADD COLUMN phrase_length INTEGER; -- bars (8, 16, 32)
ALTER TABLE tracks ADD COLUMN downbeats TEXT; -- JSON array of downbeat times

-- Advanced features
ALTER TABLE tracks ADD COLUMN energy_curve TEXT; -- JSON array of energy over time
ALTER TABLE tracks ADD COLUMN spectral_centroid REAL; -- brightness
ALTER TABLE tracks ADD COLUMN genre_detailed TEXT; -- more specific genre

-- Analysis queue for background processing
CREATE TABLE IF NOT EXISTS analysis_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT NOT NULL,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    UNIQUE(filepath)
);

-- Settings table for configuration
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value) VALUES 
    ('auto_analyze', 'true'),
    ('analysis_threads', '4'),
    ('watch_folders', 'true'),
    ('first_run_complete', 'false');

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_analysis_status ON tracks(analysis_status);
CREATE INDEX IF NOT EXISTS idx_analysis_queue_status ON analysis_queue(status);
CREATE INDEX IF NOT EXISTS idx_key ON tracks(key);
CREATE INDEX IF NOT EXISTS idx_camelot ON tracks(camelot_key);