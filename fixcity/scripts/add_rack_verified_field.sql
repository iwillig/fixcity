-- SQL to remove the 'steps' stuff we didn't end up using, and add
-- a 'verified' column to racks.

ALTER TABLE bmabr_rack ADD COLUMN verified BOOLEAN NOT NULL DEFAULT 'false';

DROP TABLE bmabr_steps;
