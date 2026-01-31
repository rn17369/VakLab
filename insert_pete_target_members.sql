-- Insert Pete (member 1002) into target_members_detail table
-- This is required for the context_data to load properly

INSERT INTO target_members_detail (
    member_id,
    phone_number,
    member_first_name,
    member_last_name,
    member_email,
    campaign_name,
    zip_code,
    member_reached_ai_agent,
    member_enrolled,
    csr_name,
    csr_phone_number,
    campaign_email_sent
) VALUES (
    '1002',
    '+17047766238',
    'Pete',
    'Scheuermann',
    'pete@example.com',
    'Metna Better Care Rewards',
    '28204',
    false,
    false,
    'VakLab Support',
    '+18133363443',
    false
)
ON CONFLICT (member_id) DO UPDATE SET
    phone_number = EXCLUDED.phone_number,
    member_first_name = EXCLUDED.member_first_name,
    member_last_name = EXCLUDED.member_last_name,
    campaign_name = EXCLUDED.campaign_name;
