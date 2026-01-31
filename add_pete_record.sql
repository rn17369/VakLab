-- Add new member record for your phone number
-- This keeps the original dev's record intact

-- Add to call list
INSERT INTO campaign_target_member_call_list (member_id, phone_number, campaign_name, call_status)
VALUES ('1002', '+17047766238', 'Metna Better Care Rewards', 'Not Called')
ON CONFLICT (member_id) DO UPDATE SET 
    phone_number = '+17047766238',
    call_status = 'Not Called';

-- Add to member details
INSERT INTO target_members_detail 
    (member_id, phone_number, member_first_name, member_last_name, member_email, 
     campaign_name, zip_code, csr_name, csr_phone_number)
VALUES 
    ('1002', '+17047766238', 'Pete', 'Scheuermann', 'pete@vaklabs.com', 
     'Metna Breast Screening Partner Program', '28277', 'Sarah', '7047766238')
ON CONFLICT (member_id) DO UPDATE SET 
    phone_number = '+17047766238',
    member_first_name = 'Pete',
    member_last_name = 'Scheuermann';

-- Add to appointment backfill (for testing appointment campaign)
INSERT INTO patients (patient_id, phone_number, first_name, last_name, email)
VALUES ('PAT002', '+17047766238', 'Pete', 'Scheuermann', 'pete@vaklabs.com')
ON CONFLICT (patient_id) DO NOTHING;

-- Verify
SELECT member_id, phone_number, campaign_name, call_status 
FROM campaign_target_member_call_list 
ORDER BY member_id;
