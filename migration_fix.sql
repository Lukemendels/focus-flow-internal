-- ROBUST MIGRATION SCRIPT

-- 1. Add missing context column to goals if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'goals' AND column_name = 'context') THEN
        ALTER TABLE goals ADD COLUMN context text;
    END IF;
END $$;

-- 2. Dynamically Drop ALL Policies
-- This loop finds every policy on the relevant tables and drops it.
-- This prevents errors from slightly different policy names.
DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT policyname, tablename
        FROM pg_policies
        WHERE tablename IN ('goals', 'reflections', 'marketing_assets', 'tasks')
    LOOP
        RAISE NOTICE 'Dropping policy % on %', r.policyname, r.tablename;
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', r.policyname, r.tablename);
    END LOOP;
END $$;

-- 3. Change user_id to TEXT on all tables
-- This aligns the database with the App's usage of "test_user"
ALTER TABLE goals ALTER COLUMN user_id TYPE text;
ALTER TABLE reflections ALTER COLUMN user_id TYPE text;
ALTER TABLE marketing_assets ALTER COLUMN user_id TYPE text;
ALTER TABLE tasks ALTER COLUMN user_id TYPE text;

-- 4. Re-create Open Policies (Permissive for this app)
CREATE POLICY "Enable all access for all users" ON goals FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for all users" ON reflections FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for all users" ON marketing_assets FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Enable all access for all users" ON tasks FOR ALL USING (true) WITH CHECK (true);
