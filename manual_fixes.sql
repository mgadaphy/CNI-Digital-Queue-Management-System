-- Manual SQL fixes for CNI Queue Management System

-- 1. Create 3 new test tickets for assignment testing
INSERT INTO queue (ticket_number, citizen_id, service_type_id, status, priority_score, created_at, updated_at)
VALUES 
    ('TEST001', 1, 1, 'waiting', 500, NOW(), NOW()),
    ('TEST002', 2, 2, 'waiting', 600, NOW(), NOW()),
    ('TEST003', 3, 1, 'waiting', 400, NOW(), NOW());

-- 2. Fix any tickets that were incorrectly marked as no_show but have agents
UPDATE queue 
SET status = 'in_progress', updated_at = NOW() 
WHERE status = 'no_show' AND agent_id IS NOT NULL;

-- 3. Check current system state
SELECT 
    status, 
    COUNT(*) as count,
    GROUP_CONCAT(ticket_number) as tickets
FROM queue 
GROUP BY status;

-- 4. Check Marie Kouassi's tickets specifically
SELECT 
    q.ticket_number,
    q.status,
    q.agent_id,
    c.first_name,
    c.last_name,
    s.name_fr as service_name
FROM queue q
JOIN citizens c ON q.citizen_id = c.id
JOIN service_types s ON q.service_type_id = s.id
JOIN agents a ON q.agent_id = a.id
WHERE a.employee_id = 'AGT001';
