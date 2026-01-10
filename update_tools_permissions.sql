-- Update Strategic Architect (CEO) permissions
UPDATE kernels 
SET tools_enabled = ARRAY['web_search', 'calculate_metrics'] 
WHERE role_name = 'Strategic Architect';

-- Update Market Alchemist (CMO) permissions
UPDATE kernels 
SET tools_enabled = ARRAY['web_search'] 
WHERE role_name = 'Market Alchemist';

-- Update Operational Commander (COO) permissions
UPDATE kernels 
SET tools_enabled = ARRAY['block_calendar_time', 'update_calendar_event', 'delete_calendar_event', 'calculate_metrics'] 
WHERE role_name = 'Operational Commander';
