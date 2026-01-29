-- Clinic Scheduler Schema for Appointment Backfill Campaign
-- Supports appointment rescheduling to fill cancellation slots

-- Clinic/Provider Structure
CREATE TABLE IF NOT EXISTS clinics (
    clinic_id VARCHAR(50) PRIMARY KEY,
    clinic_name VARCHAR(200) NOT NULL,
    address VARCHAR(500),
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS providers (
    provider_id VARCHAR(50) PRIMARY KEY,
    clinic_id VARCHAR(50) REFERENCES clinics(clinic_id),
    provider_name VARCHAR(200) NOT NULL,
    specialty VARCHAR(100)
);

-- Patient records (separate from HEDIS members)
CREATE TABLE IF NOT EXISTS patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    phone_number VARCHAR(20) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(200)
);

-- Appointments
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    provider_id VARCHAR(50) REFERENCES providers(provider_id),
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    status VARCHAR(50) DEFAULT 'scheduled',  -- scheduled, completed, cancelled, rescheduled
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Backfill queue (cancellation slots to fill)
CREATE TABLE IF NOT EXISTS appointment_backfill_queue (
    queue_id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    phone_number VARCHAR(20) NOT NULL,
    original_appointment_id VARCHAR(50) REFERENCES appointments(appointment_id),
    available_slot_date DATE NOT NULL,
    available_slot_time TIME NOT NULL,
    provider_id VARCHAR(50) REFERENCES providers(provider_id),
    call_status VARCHAR(50) DEFAULT 'Not Called',
    campaign_type VARCHAR(100) DEFAULT 'appointment_backfill'
);

-- Seed data matching golden_convo/appt_case.json
INSERT INTO clinics (clinic_id, clinic_name, address, phone)
VALUES ('CLINIC001', 'Northview Family Medicine', '123 Health Ave, Plano TX 75087', '972-555-0100')
ON CONFLICT (clinic_id) DO NOTHING;

INSERT INTO providers (provider_id, clinic_id, provider_name, specialty)
VALUES ('PROV001', 'CLINIC001', 'Dr. Sarah Patel', 'Family Medicine')
ON CONFLICT (provider_id) DO NOTHING;

INSERT INTO patients (patient_id, phone_number, first_name, last_name, email)
VALUES ('PAT001', '9135960926', 'Mark', 'Reynolds', 'mark.reynolds@email.com')
ON CONFLICT (patient_id) DO NOTHING;

-- Original appointment (Feb 3, 10:00 AM)
INSERT INTO appointments (appointment_id, patient_id, provider_id, appointment_date, appointment_time, status)
VALUES ('APPT001', 'PAT001', 'PROV001', '2026-02-03', '10:00:00', 'scheduled')
ON CONFLICT (appointment_id) DO NOTHING;

-- Backfill opportunity (Feb 1, 2:30 PM - cancellation slot)
INSERT INTO appointment_backfill_queue (patient_id, phone_number, original_appointment_id, available_slot_date, available_slot_time, provider_id)
VALUES ('PAT001', '9135960926', 'APPT001', '2026-02-01', '14:30:00', 'PROV001')
ON CONFLICT DO NOTHING;
