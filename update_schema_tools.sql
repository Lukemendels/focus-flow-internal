-- Add tools_enabled column to kernels table if it doesn't exist
ALTER TABLE kernels 
ADD COLUMN IF NOT EXISTS tools_enabled TEXT[];

-- Update The Watcher to have read_logs enabled
UPDATE kernels 
SET tools_enabled = ARRAY['read_logs'] 
WHERE role_name = 'The Watcher';

-- Initial setup: Ensure others are null or empty
UPDATE kernels SET tools_enabled = NULL WHERE role_name != 'The Watcher';
