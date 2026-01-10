-- Add thinking_level column with default 'MINIMAL'
ALTER TABLE kernels 
ADD COLUMN IF NOT EXISTS thinking_level TEXT DEFAULT 'MINIMAL';

-- Update Strategic Architect (Deep Thought)
UPDATE kernels 
SET thinking_level = 'HIGH' 
WHERE role_name = 'Strategic Architect';

-- Update Market Alchemist (Creative Nuance)
UPDATE kernels 
SET thinking_level = 'LOW' 
WHERE role_name = 'Market Alchemist';

-- Update Others (Speed/Execution)
UPDATE kernels 
SET thinking_level = 'MINIMAL' 
WHERE role_name IN ('Operational Commander', 'The Chairman', 'The Watcher', 'Genesis Architect');
