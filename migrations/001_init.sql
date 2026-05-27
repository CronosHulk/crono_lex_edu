

\restrict eqFnSAjvGYTgSsKlWthYiWOVHkJ5i6ep7OdHpEPC485RY8hGjFESyaSSOhI1Brp

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';

DROP TABLE IF EXISTS acl CASCADE;
CREATE TABLE IF NOT EXISTS acl (
    id BIGINT NOT NULL,
    group_id BIGINT NOT NULL,
    action TEXT NOT NULL,
    environment TEXT DEFAULT 'web_admin'::TEXT NOT NULL,
    rule TEXT NOT NULL,
    method TEXT DEFAULT 'ANY'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS acl_group CASCADE;
CREATE TABLE IF NOT EXISTS acl_group (
    id BIGINT NOT NULL,
    title TEXT NOT NULL,
    parent_group_id BIGINT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS admin_bot_restore CASCADE;
CREATE TABLE IF NOT EXISTS admin_bot_restore (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    chat_id BIGINT NOT NULL,
    previous_screen_id TEXT,
    status TEXT DEFAULT 'queued'::TEXT NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    sent TIMESTAMP WITH TIME ZONE,
    error_text TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS admin_credential CASCADE;
CREATE TABLE IF NOT EXISTS admin_credential (
    user_uuid UUID NOT NULL,
    password_hash TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS admin_magic_link CASCADE;
CREATE TABLE IF NOT EXISTS admin_magic_link (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    token_hash TEXT NOT NULL,
    target_path TEXT NOT NULL,
    expires TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS admin_otp_challenge CASCADE;
CREATE TABLE IF NOT EXISTS admin_otp_challenge (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    otp_hash TEXT NOT NULL,
    attempts_count INTEGER DEFAULT 0 NOT NULL,
    sent_chat_id BIGINT,
    sent_message_id BIGINT,
    previous_screen_id TEXT,
    expires TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS admin_session CASCADE;
CREATE TABLE IF NOT EXISTS admin_session (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    session_token_hash TEXT NOT NULL,
    expires TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked TIMESTAMP WITH TIME ZONE,
    api_origin TEXT,
    client_ip TEXT,
    user_agent TEXT,
    device_fingerprint_hash TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE
);

DROP TABLE IF EXISTS ai_provider_pricing_snapshot CASCADE;
CREATE TABLE IF NOT EXISTS ai_provider_pricing_snapshot (
    id BIGINT NOT NULL,
    provider_key TEXT NOT NULL,
    model TEXT NOT NULL,
    unit TEXT NOT NULL,
    input_usd_per_1m numeric(18,8) NOT NULL,
    output_usd_per_1m numeric(18,8) NOT NULL,
    source TEXT NOT NULL,
    observed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS ai_usage_session CASCADE;
CREATE TABLE IF NOT EXISTS ai_usage_session (
    id BIGINT NOT NULL,
    task_key TEXT NOT NULL,
    task_scope TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    model TEXT NOT NULL,
    actor_type TEXT NOT NULL,
    actor_user_uuid UUID,
    actor_group_title TEXT,
    source_type TEXT,
    source_identifier TEXT,
    import_job_id BIGINT,
    task_log_id BIGINT,
    batch_key TEXT,
    request_count INTEGER DEFAULT 0 NOT NULL,
    input_tokens INTEGER DEFAULT 0 NOT NULL,
    output_tokens INTEGER DEFAULT 0 NOT NULL,
    total_tokens INTEGER DEFAULT 0 NOT NULL,
    estimated_cost_usd numeric(18,8) DEFAULT '0'::numeric NOT NULL,
    pricing_source TEXT,
    status TEXT DEFAULT 'success'::TEXT NOT NULL,
    summary TEXT,
    metadata_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    started TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    finished TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS app_runtime_state CASCADE;
CREATE TABLE IF NOT EXISTS app_runtime_state (
    key TEXT NOT NULL,
    value_json JSONB NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS app_setting CASCADE;
CREATE TABLE IF NOT EXISTS app_setting (
    key TEXT NOT NULL,
    value_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS app_version CASCADE;
CREATE TABLE IF NOT EXISTS app_version (
    key TEXT NOT NULL,
    version TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS billing_bot_notification CASCADE;
CREATE TABLE IF NOT EXISTS billing_bot_notification (
    id BIGINT NOT NULL,
    payment_id BIGINT NOT NULL,
    notification_type TEXT NOT NULL,
    status_snapshot TEXT DEFAULT 'unknown'::TEXT NOT NULL,
    receipt_ids_json JSONB DEFAULT '[]'::JSONB NOT NULL,
    status TEXT DEFAULT 'queued'::TEXT NOT NULL,
    error_text TEXT,
    claimed_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_billing_bot_notification_status CHECK ((status = ANY (ARRAY['queued'::TEXT, 'claimed'::TEXT, 'sent'::TEXT, 'skipped'::TEXT, 'failed'::TEXT]))),
    CONSTRAINT ck_billing_bot_notification_type CHECK ((notification_type = 'terminal_status'::TEXT))
);

DROP TABLE IF EXISTS billing_offer_acceptance CASCADE;
CREATE TABLE IF NOT EXISTS billing_offer_acceptance (
    id BIGINT NOT NULL,
    payment_id BIGINT,
    user_uuid UUID NOT NULL,
    offer_text_hash TEXT NOT NULL,
    offer_version TEXT,
    accepted_ip TEXT,
    accepted_user_agent TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS billing_payment CASCADE;
CREATE TABLE IF NOT EXISTS billing_payment (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    plan_key TEXT NOT NULL,
    period_months INTEGER NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency INTEGER DEFAULT 980 NOT NULL,
    status TEXT DEFAULT 'created'::TEXT NOT NULL,
    provider TEXT DEFAULT 'monobank'::TEXT NOT NULL,
    provider_mode TEXT NOT NULL,
    provider_invoice_id TEXT,
    provider_reference TEXT NOT NULL,
    checkout_url TEXT,
    return_url TEXT,
    source_path TEXT,
    failure_code TEXT,
    failure_reason TEXT,
    provider_status_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE,
    paid_at TIMESTAMP WITH TIME ZONE,
    success_rechecked_at TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_billing_payment_amount_minor CHECK ((amount_minor > 0)),
    CONSTRAINT ck_billing_payment_period_months CHECK ((period_months = ANY (ARRAY[1, 3, 6, 12]))),
    CONSTRAINT ck_billing_payment_provider CHECK ((provider = 'monobank'::TEXT)),
    CONSTRAINT ck_billing_payment_provider_mode CHECK ((provider_mode = ANY (ARRAY['test'::TEXT, 'production'::TEXT]))),
    CONSTRAINT ck_billing_payment_status CHECK ((status = ANY (ARRAY['created'::TEXT, 'invoice_created'::TEXT, 'processing'::TEXT, 'success'::TEXT, 'failure'::TEXT, 'expired'::TEXT, 'reversed'::TEXT])))
);

DROP TABLE IF EXISTS billing_payment_event CASCADE;
CREATE TABLE IF NOT EXISTS billing_payment_event (
    id BIGINT NOT NULL,
    payment_id BIGINT,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    provider_status TEXT,
    payload_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS billing_receipt CASCADE;
CREATE TABLE IF NOT EXISTS billing_receipt (
    id BIGINT NOT NULL,
    payment_id BIGINT NOT NULL,
    receipt_type TEXT NOT NULL,
    status TEXT NOT NULL,
    provider_check_id TEXT,
    fiscalization_source TEXT,
    tax_url TEXT,
    file_base64 TEXT,
    payload_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    bot_delivery_status TEXT,
    bot_delivery_error TEXT,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    admin_alerted_at TIMESTAMP WITH TIME ZONE,
    admin_alert_status TEXT,
    admin_alert_error TEXT,
    admin_alert_claimed_at TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_billing_receipt_status CHECK ((status = ANY (ARRAY['new'::TEXT, 'process'::TEXT, 'done'::TEXT, 'failed'::TEXT, 'unavailable'::TEXT]))),
    CONSTRAINT ck_billing_receipt_type CHECK ((receipt_type = ANY (ARRAY['receipt'::TEXT, 'fiscal_check'::TEXT])))
);

DROP TABLE IF EXISTS billing_subscription_purchase CASCADE;
CREATE TABLE IF NOT EXISTS billing_subscription_purchase (
    id BIGINT NOT NULL,
    payment_id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    product_type TEXT DEFAULT 'subscription'::TEXT NOT NULL,
    product_key TEXT NOT NULL,
    period_months INTEGER NOT NULL,
    amount_minor INTEGER NOT NULL,
    currency INTEGER DEFAULT 980 NOT NULL,
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    reversed_at TIMESTAMP WITH TIME ZONE,
    metadata_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_billing_subscription_purchase_amount_minor CHECK ((amount_minor > 0)),
    CONSTRAINT ck_billing_subscription_purchase_period_months CHECK ((period_months = ANY (ARRAY[1, 3, 6, 12]))),
    CONSTRAINT ck_billing_subscription_purchase_product_type CHECK ((product_type = 'subscription'::TEXT)),
    CONSTRAINT ck_billing_subscription_purchase_status CHECK ((status = ANY (ARRAY['active'::TEXT, 'reversed'::TEXT])))
);

DROP TABLE IF EXISTS bot_message_log CASCADE;
CREATE TABLE IF NOT EXISTS bot_message_log (
    id BIGINT NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    chat_id BIGINT NOT NULL,
    message_id BIGINT NOT NULL,
    screen_id TEXT NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    error_text TEXT,
    delete_after TIMESTAMP WITH TIME ZONE NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    deleted TIMESTAMP WITH TIME ZONE
);

DROP TABLE IF EXISTS client_web_credential CASCADE;
CREATE TABLE IF NOT EXISTS client_web_credential (
    user_uuid UUID NOT NULL,
    password_hash TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS client_web_magic_link CASCADE;
CREATE TABLE IF NOT EXISTS client_web_magic_link (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    token_hash TEXT NOT NULL,
    target_path TEXT NOT NULL,
    expires TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS client_web_otp_challenge CASCADE;
CREATE TABLE IF NOT EXISTS client_web_otp_challenge (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    otp_hash TEXT NOT NULL,
    attempts_count BIGINT DEFAULT '0'::BIGINT NOT NULL,
    sent_chat_id BIGINT,
    sent_message_id BIGINT,
    expires TIMESTAMP WITH TIME ZONE NOT NULL,
    consumed TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS client_web_session CASCADE;
CREATE TABLE IF NOT EXISTS client_web_session (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    session_token_hash TEXT NOT NULL,
    expires TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked TIMESTAMP WITH TIME ZONE,
    api_origin TEXT,
    client_ip TEXT,
    user_agent TEXT,
    device_fingerprint_hash TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_seen TIMESTAMP WITH TIME ZONE
);

DROP TABLE IF EXISTS dictionary_category CASCADE;
CREATE TABLE IF NOT EXISTS dictionary_category (
    id BIGINT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS dictionary_entry CASCADE;
CREATE TABLE IF NOT EXISTS dictionary_entry (
    id BIGINT NOT NULL,
    source_legacy_id BIGINT,
    source_namespace TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    source_raw_refs_json JSONB DEFAULT '[]'::JSONB NOT NULL,
    entry_key TEXT NOT NULL,
    word TEXT NOT NULL,
    normalized_word TEXT NOT NULL,
    level_id BIGINT,
    transcription TEXT,
    translation_uk TEXT NOT NULL,
    translation_ru TEXT,
    translation_pl TEXT,
    examples_json JSONB NOT NULL,
    entry_type TEXT DEFAULT 'word'::TEXT NOT NULL,
    is_archived BOOLEAN DEFAULT false NOT NULL,
    is_teacher_verified BOOLEAN DEFAULT false NOT NULL,
    teacher_verified_by_user_uuid UUID,
    teacher_verified_at TIMESTAMP WITH TIME ZONE,
    audio_path TEXT NOT NULL,
    embedding public.vector(384),
    embedding_model TEXT,
    is_embedding_ready BOOLEAN DEFAULT false NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS dictionary_entry_category CASCADE;
CREATE TABLE IF NOT EXISTS dictionary_entry_category (
    entry_id BIGINT NOT NULL,
    category_id BIGINT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS dictionary_entry_part_of_speech CASCADE;
CREATE TABLE IF NOT EXISTS dictionary_entry_part_of_speech (
    entry_id BIGINT NOT NULL,
    part_of_speech_id BIGINT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS dictionary_entry_synonym CASCADE;
CREATE TABLE IF NOT EXISTS dictionary_entry_synonym (
    left_entry_id BIGINT NOT NULL,
    right_entry_id BIGINT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT dictionary_entry_synonym_self_check CHECK ((left_entry_id < right_entry_id))
);

DROP TABLE IF EXISTS dictionary_part_of_speech CASCADE;
CREATE TABLE IF NOT EXISTS dictionary_part_of_speech (
    id BIGINT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS error_log CASCADE;
CREATE TABLE IF NOT EXISTS error_log (
    id BIGINT NOT NULL,
    level TEXT NOT NULL,
    TEXT TEXT NOT NULL,
    context_json JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS exercise_text_topics CASCADE;
CREATE TABLE IF NOT EXISTS exercise_text_topics (
    exercise_text_id BIGINT NOT NULL,
    grammar_topic_id BIGINT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS exercise_texts CASCADE;
CREATE TABLE IF NOT EXISTS exercise_texts (
    id BIGINT NOT NULL,
    UUID UUID DEFAULT gen_random_uuid() NOT NULL,
    title TEXT,
    status TEXT DEFAULT 'draft'::TEXT NOT NULL,
    difficulty_band TEXT,
    text_types TEXT[] DEFAULT '{}'::TEXT[] NOT NULL,
    content_jsonb JSONB DEFAULT '{}'::JSONB NOT NULL,
    version INTEGER DEFAULT 1 NOT NULL,
    created_by_user_uuid UUID,
    updated_by_user_uuid UUID,
    published_at TIMESTAMP WITH TIME ZONE,
    archived_at TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_exercise_texts_difficulty_band CHECK (((difficulty_band IS NULL) OR (difficulty_band = ANY (ARRAY['A1_A2'::TEXT, 'B1_B2'::TEXT, 'C1_C2'::TEXT])))),
    CONSTRAINT ck_exercise_texts_status CHECK ((status = ANY (ARRAY['draft'::TEXT, 'generated'::TEXT, 'ready'::TEXT, 'published'::TEXT, 'archived'::TEXT]))),
    CONSTRAINT ck_exercise_texts_version_positive CHECK ((version >= 1))
);

DROP TABLE IF EXISTS external_provider_task_setting CASCADE;
CREATE TABLE IF NOT EXISTS external_provider_task_setting (
    task_key TEXT NOT NULL,
    provider_key TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT true NOT NULL,
    config_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    last_status_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS grammar_topics CASCADE;
CREATE TABLE IF NOT EXISTS grammar_topics (
    id BIGINT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    level TEXT NOT NULL,
    min_level TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS language_level CASCADE;
CREATE TABLE IF NOT EXISTS language_level (
    id BIGINT NOT NULL,
    title TEXT NOT NULL,
    description TEXT
);

DROP TABLE IF EXISTS learning_answer CASCADE;
CREATE TABLE IF NOT EXISTS learning_answer (
    id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    session_word_id BIGINT NOT NULL,
    exercise_type TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    attempt_no INTEGER NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS learning_session CASCADE;
CREATE TABLE IF NOT EXISTS learning_session (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    language_level_id BIGINT NOT NULL,
    level_run_id BIGINT,
    source_session_id BIGINT,
    session_type TEXT DEFAULT 'regular'::TEXT NOT NULL,
    words_target_count INTEGER NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    stage_queue_json JSONB NOT NULL,
    stage_position INTEGER DEFAULT 0 NOT NULL,
    active_interface TEXT DEFAULT 'telegram_user'::TEXT NOT NULL,
    interface_revision BIGINT DEFAULT '0'::BIGINT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    completed TIMESTAMP WITH TIME ZONE
);

DROP TABLE IF EXISTS learning_session_word CASCADE;
CREATE TABLE IF NOT EXISTS learning_session_word (
    id BIGINT NOT NULL,
    session_id BIGINT NOT NULL,
    word_source TEXT DEFAULT 'core'::TEXT NOT NULL,
    word_id BIGINT NOT NULL,
    item_order INTEGER NOT NULL,
    card_status TEXT DEFAULT 'pending'::TEXT NOT NULL,
    en_uk_attempts INTEGER DEFAULT 0 NOT NULL,
    en_uk_correct BOOLEAN DEFAULT false NOT NULL,
    uk_en_attempts INTEGER DEFAULT 0 NOT NULL,
    uk_en_correct BOOLEAN DEFAULT false NOT NULL,
    gap_attempts INTEGER DEFAULT 0 NOT NULL,
    gap_correct BOOLEAN DEFAULT false NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_learning_session_word_source CHECK ((word_source = ANY (ARRAY['core'::TEXT, 'user'::TEXT])))
);

DROP TABLE IF EXISTS learning_syllabus_domain CASCADE;
CREATE TABLE IF NOT EXISTS learning_syllabus_domain (
    id BIGINT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS learning_syllabus_item CASCADE;
CREATE TABLE IF NOT EXISTS learning_syllabus_item (
    id BIGINT NOT NULL,
    level_id BIGINT NOT NULL,
    domain_id BIGINT NOT NULL,
    code TEXT NOT NULL,
    title TEXT NOT NULL,
    normalized_title TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    metadata_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS monobank_audit_log CASCADE;
CREATE TABLE IF NOT EXISTS monobank_audit_log (
    id BIGINT NOT NULL,
    direction TEXT NOT NULL,
    provider_mode TEXT NOT NULL,
    source_place TEXT NOT NULL,
    actor_user_uuid UUID,
    telegram_user_id BIGINT,
    payment_id BIGINT,
    order_reference TEXT,
    invoice_id TEXT,
    request_method TEXT,
    request_url TEXT,
    request_ip TEXT,
    request_headers_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    request_body_json JSONB,
    request_raw_body TEXT,
    response_status_code INTEGER,
    response_headers_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    response_body_json JSONB,
    response_raw_body TEXT,
    signature_valid BOOLEAN,
    processing_result TEXT,
    error_text TEXT,
    started TIMESTAMP WITH TIME ZONE NOT NULL,
    finished TIMESTAMP WITH TIME ZONE,
    duration_ms INTEGER,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_monobank_audit_log_direction CHECK ((direction = ANY (ARRAY['outgoing'::TEXT, 'incoming'::TEXT]))),
    CONSTRAINT ck_monobank_audit_log_provider_mode CHECK ((provider_mode = ANY (ARRAY['test'::TEXT, 'production'::TEXT, 'unknown'::TEXT])))
);

DROP TABLE IF EXISTS task_log CASCADE;
CREATE TABLE IF NOT EXISTS task_log (
    id BIGINT NOT NULL,
    task_type TEXT NOT NULL,
    status TEXT DEFAULT 'processing'::TEXT NOT NULL,
    user_uuid UUID,
    source_type TEXT,
    source_identifier TEXT,
    import_job_id BIGINT,
    description TEXT,
    error_text TEXT,
    result_json JSONB NOT NULL,
    started TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    finished TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT task_log_status_check CHECK ((status = ANY (ARRAY['queued'::TEXT, 'processing'::TEXT, 'success'::TEXT, 'error'::TEXT, 'fatal'::TEXT])))
);

DROP TABLE IF EXISTS teacher_google_oauth_connection CASCADE;
CREATE TABLE IF NOT EXISTS teacher_google_oauth_connection (
    id BIGINT NOT NULL,
    teacher_user_uuid UUID NOT NULL,
    provider TEXT DEFAULT 'google'::TEXT NOT NULL,
    refresh_token_ciphertext TEXT NOT NULL,
    access_token_ciphertext TEXT,
    access_token_expires_at TIMESTAMP WITH TIME ZONE,
    scope TEXT,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_teacher_google_oauth_connection_status CHECK ((status = ANY (ARRAY['active'::TEXT, 'revoked'::TEXT])))
);

DROP TABLE IF EXISTS teacher_student_group CASCADE;
CREATE TABLE IF NOT EXISTS teacher_student_group (
    id BIGINT NOT NULL,
    teacher_user_uuid UUID NOT NULL,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_teacher_student_group_status CHECK ((status = ANY (ARRAY['active'::TEXT, 'archived'::TEXT])))
);

DROP TABLE IF EXISTS teacher_student_link CASCADE;
CREATE TABLE IF NOT EXISTS teacher_student_link (
    id BIGINT NOT NULL,
    teacher_user_uuid UUID NOT NULL,
    student_user_uuid UUID NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    group_id BIGINT,
    teacher_alias TEXT
);

DROP TABLE IF EXISTS teacher_student_meet_session CASCADE;
CREATE TABLE IF NOT EXISTS teacher_student_meet_session (
    id BIGINT NOT NULL,
    teacher_user_uuid UUID NOT NULL,
    student_user_uuid UUID NOT NULL,
    provider TEXT DEFAULT 'google_meet'::TEXT NOT NULL,
    calendar_event_id TEXT,
    join_url TEXT NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    error_text TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_teacher_student_meet_session_provider CHECK ((provider = 'google_meet'::TEXT)),
    CONSTRAINT ck_teacher_student_meet_session_status CHECK ((status = ANY (ARRAY['active'::TEXT, 'failed'::TEXT, 'archived'::TEXT])))
);

DROP TABLE IF EXISTS training_schedule CASCADE;
CREATE TABLE IF NOT EXISTS training_schedule (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    schedule_type TEXT NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    schedule_date date NOT NULL,
    period_code TEXT,
    source_session_id BIGINT,
    status TEXT DEFAULT 'pending'::TEXT NOT NULL,
    notified TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS tts_voices CASCADE;
CREATE TABLE IF NOT EXISTS tts_voices (
    id BIGINT NOT NULL,
    provider TEXT NOT NULL,
    code TEXT NOT NULL,
    display_name TEXT NOT NULL,
    language_code TEXT NOT NULL,
    gender TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    sort_order INTEGER DEFAULT 0 NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_tts_voices_gender CHECK ((gender = ANY (ARRAY['female'::TEXT, 'male'::TEXT])))
);

DROP TABLE IF EXISTS "user" CASCADE;
CREATE TABLE IF NOT EXISTS "user" (
    id BIGINT NOT NULL,
    UUID UUID DEFAULT gen_random_uuid() NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    is_bot BOOLEAN,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    language_code TEXT,
    interface_locale TEXT DEFAULT 'uk'::TEXT NOT NULL,
    client_web_password_prompted BOOLEAN DEFAULT false NOT NULL,
    admin_web_password_prompted BOOLEAN DEFAULT false NOT NULL,
    is_premium BOOLEAN,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    learning_role TEXT DEFAULT 'student'::TEXT NOT NULL,
    acl_group_id BIGINT NOT NULL,
    language_level_id BIGINT,
    chat_id BIGINT,
    chat_type TEXT,
    chat_username TEXT,
    chat_title TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    raw_telegram_json json,
    is_video_learner BOOLEAN DEFAULT false NOT NULL
);

DROP TABLE IF EXISTS user_dictionary_entry CASCADE;
CREATE TABLE IF NOT EXISTS user_dictionary_entry (
    id BIGINT NOT NULL,
    word TEXT NOT NULL,
    normalized_word TEXT NOT NULL,
    entry_key TEXT NOT NULL,
    entry_type TEXT DEFAULT 'word'::TEXT NOT NULL,
    part_of_speech TEXT NOT NULL,
    level_id BIGINT,
    transcription TEXT,
    translation_uk TEXT,
    translation_ru TEXT,
    translation_pl TEXT,
    examples_json JSONB NOT NULL,
    audio_path TEXT,
    embedding public.vector(384),
    embedding_model TEXT,
    is_embedding_ready BOOLEAN DEFAULT false NOT NULL,
    status TEXT DEFAULT 'queued_for_details'::TEXT NOT NULL,
    promoted_dictionary_entry_id BIGINT,
    created_by_user_uuid UUID,
    source_provider_status_json JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_user_dictionary_entry_status CHECK ((status = ANY (ARRAY['queued_for_details'::TEXT, 'details_failed'::TEXT, 'queued_for_audio'::TEXT, 'audio_failed'::TEXT, 'queued_for_embedding'::TEXT, 'embedding_failed'::TEXT, 'ready_for_rotation'::TEXT, 'rejected'::TEXT, 'archived'::TEXT, 'promoted'::TEXT])))
);

DROP TABLE IF EXISTS user_events CASCADE;
CREATE TABLE IF NOT EXISTS user_events (
    id BIGINT NOT NULL,
    telegram_user_id BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    message_text TEXT,
    callback_data TEXT,
    raw_update_json JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS user_import_google_doc_progress CASCADE;
CREATE TABLE IF NOT EXISTS user_import_google_doc_progress (
    user_uuid UUID NOT NULL,
    google_doc_id TEXT NOT NULL,
    last_processed_line INTEGER DEFAULT 0 NOT NULL,
    last_processed_line_hash TEXT,
    last_processed_lookup_word TEXT,
    last_synced TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS user_learning_settings CASCADE;
CREATE TABLE IF NOT EXISTS user_learning_settings (
    user_uuid UUID NOT NULL,
    words_per_session INTEGER DEFAULT 10 NOT NULL,
    daily_reminder_hour INTEGER,
    preferred_gender TEXT,
    import_google_doc_id TEXT,
    is_import_google_doc_auto_sync_enabled BOOLEAN DEFAULT false NOT NULL,
    import_google_doc_last_synced TIMESTAMP WITH TIME ZONE,
    import_google_doc_last_error TEXT,
    import_google_doc_retry_count INTEGER DEFAULT 0 NOT NULL,
    import_google_doc_next_retry_at TIMESTAMP WITH TIME ZONE,
    import_google_doc_claimed_until TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS user_level_run CASCADE;
CREATE TABLE IF NOT EXISTS user_level_run (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    level_id BIGINT NOT NULL,
    run_no INTEGER NOT NULL,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    completed TIMESTAMP WITH TIME ZONE
);

DROP TABLE IF EXISTS user_reminder_schedule CASCADE;
CREATE TABLE IF NOT EXISTS user_reminder_schedule (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    weekday INTEGER NOT NULL,
    hour INTEGER NOT NULL,
    status TEXT DEFAULT 'enabled'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    minute INTEGER DEFAULT 0 NOT NULL,
    title TEXT,
    CONSTRAINT ck_user_reminder_schedule_hour CHECK (((hour >= 7) AND (hour <= 22))),
    CONSTRAINT ck_user_reminder_schedule_minute CHECK ((minute = ANY (ARRAY[0, 30]))),
    CONSTRAINT ck_user_reminder_schedule_status CHECK ((status = ANY (ARRAY['enabled'::TEXT, 'disabled'::TEXT]))),
    CONSTRAINT ck_user_reminder_schedule_weekday CHECK (((weekday >= 0) AND (weekday <= 6)))
);

DROP TABLE IF EXISTS user_reminder_weekday CASCADE;
CREATE TABLE IF NOT EXISTS user_reminder_weekday (
    user_uuid UUID NOT NULL,
    weekday INTEGER NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS user_subscription CASCADE;
CREATE TABLE IF NOT EXISTS user_subscription (
    user_uuid UUID NOT NULL,
    plan_key TEXT NOT NULL,
    start TIMESTAMP WITH TIME ZONE NOT NULL,
    "end" TIMESTAMP WITH TIME ZONE,
    trial_start TIMESTAMP WITH TIME ZONE,
    trial_end TIMESTAMP WITH TIME ZONE,
    payment_required BOOLEAN DEFAULT false NOT NULL,
    payment_due_at TIMESTAMP WITH TIME ZONE,
    payment_reason TEXT,
    status TEXT DEFAULT 'active'::TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_user_subscription_plan_key CHECK ((plan_key = ANY (ARRAY['free'::TEXT, 'premium'::TEXT, 'premium_plus'::TEXT, 'permanent_premium'::TEXT, 'teacher_free'::TEXT, 'teacher_premium'::TEXT]))),
    CONSTRAINT ck_user_subscription_status CHECK ((status = ANY (ARRAY['active'::TEXT, 'expired'::TEXT, 'canceled'::TEXT])))
);

DROP TABLE IF EXISTS user_vocabulary_import_item CASCADE;
CREATE TABLE IF NOT EXISTS user_vocabulary_import_item (
    id BIGINT NOT NULL,
    import_job_id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    task_log_id BIGINT,
    raw_value TEXT NOT NULL,
    lookup_word TEXT NOT NULL,
    translation_hint TEXT,
    validated_lookup_word TEXT,
    validated_part_of_speech TEXT,
    validated_translation_uk TEXT,
    validated_translation_ru TEXT,
    validated_translation_pl TEXT,
    status TEXT DEFAULT 'pending'::TEXT NOT NULL,
    error_text TEXT,
    existing_word_id BIGINT,
    user_dictionary_entry_id BIGINT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    processed TIMESTAMP WITH TIME ZONE
);

DROP TABLE IF EXISTS user_vocabulary_import_job CASCADE;
CREATE TABLE IF NOT EXISTS user_vocabulary_import_job (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    task_log_id BIGINT,
    source_type TEXT NOT NULL,
    source_identifier TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    status TEXT DEFAULT 'queued'::TEXT NOT NULL,
    total_items INTEGER DEFAULT 0 NOT NULL,
    processed_items INTEGER DEFAULT 0 NOT NULL,
    successful_items INTEGER DEFAULT 0 NOT NULL,
    failed_items INTEGER DEFAULT 0 NOT NULL,
    summary_sent BOOLEAN DEFAULT false NOT NULL,
    publish_summary_sent BOOLEAN DEFAULT false NOT NULL,
    processing_claimed_until TIMESTAMP WITH TIME ZONE,
    last_error TEXT,
    completed TIMESTAMP WITH TIME ZONE,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

DROP TABLE IF EXISTS user_word_assignment CASCADE;
CREATE TABLE IF NOT EXISTS user_word_assignment (
    id BIGINT NOT NULL,
    user_uuid UUID NOT NULL,
    word_source TEXT NOT NULL,
    word_id BIGINT NOT NULL,
    status TEXT DEFAULT 'available_for_rotation'::TEXT NOT NULL,
    priority_rank BIGINT DEFAULT '0'::BIGINT NOT NULL,
    is_known BOOLEAN DEFAULT false NOT NULL,
    learning_state TEXT DEFAULT 'learning'::TEXT NOT NULL,
    control_success_streak INTEGER DEFAULT 0 NOT NULL,
    review_priority INTEGER DEFAULT 0 NOT NULL,
    last_level_run_id BIGINT,
    last_completed TIMESTAMP WITH TIME ZONE,
    next_review_at TIMESTAMP WITH TIME ZONE,
    import_job_id BIGINT,
    import_item_id BIGINT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    priority_state TEXT DEFAULT 'none'::TEXT NOT NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE,
    last_reviewed_at TIMESTAMP WITH TIME ZONE,
    review_stage INTEGER DEFAULT 0 NOT NULL,
    mistake_count INTEGER DEFAULT 0 NOT NULL,
    CONSTRAINT ck_user_word_assignment_learning_state CHECK ((learning_state = ANY (ARRAY['learning'::TEXT, 'needs_work'::TEXT, 'learned'::TEXT]))),
    CONSTRAINT ck_user_word_assignment_priority_state CHECK ((priority_state = ANY (ARRAY['none'::TEXT, 'pending'::TEXT, 'introduced'::TEXT, 'consumed'::TEXT]))),
    CONSTRAINT ck_user_word_assignment_status CHECK ((status = ANY (ARRAY['waiting_for_entry'::TEXT, 'available_for_rotation'::TEXT, 'hidden'::TEXT, 'archived'::TEXT]))),
    CONSTRAINT ck_user_word_assignment_word_source CHECK ((word_source = ANY (ARRAY['core'::TEXT, 'user'::TEXT])))
);

DROP TABLE IF EXISTS video_generation_job CASCADE;
CREATE TABLE IF NOT EXISTS video_generation_job (
    id BIGINT NOT NULL,
    video_id TEXT NOT NULL,
    learner_id BIGINT NOT NULL,
    video_format TEXT NOT NULL,
    locale TEXT DEFAULT 'uk'::TEXT NOT NULL,
    interface TEXT DEFAULT 'web'::TEXT NOT NULL,
    status TEXT DEFAULT 'draft'::TEXT NOT NULL,
    review_status TEXT DEFAULT 'draft'::TEXT NOT NULL,
    artifact_dir TEXT NOT NULL,
    error_code TEXT,
    error_message TEXT,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    lesson_id TEXT,
    lesson_number BIGINT,
    CONSTRAINT ck_video_generation_job_review_status CHECK ((review_status = ANY (ARRAY['draft'::TEXT, 'ready_for_review'::TEXT, 'approved'::TEXT, 'rejected'::TEXT, 'deleted'::TEXT, 'posted'::TEXT, 'failed'::TEXT]))),
    CONSTRAINT ck_video_generation_job_status CHECK ((status = ANY (ARRAY['draft'::TEXT, 'processing'::TEXT, 'success'::TEXT, 'error'::TEXT, 'fatal'::TEXT])))
);

DROP TABLE IF EXISTS video_learner CASCADE;
CREATE TABLE IF NOT EXISTS video_learner (
    id BIGINT NOT NULL,
    learner_key TEXT NOT NULL,
    user_uuid UUID NOT NULL,
    display_name TEXT NOT NULL,
    level_id BIGINT NOT NULL,
    locale TEXT DEFAULT 'uk'::TEXT NOT NULL,
    words_count INTEGER DEFAULT 5 NOT NULL,
    mistake_probability numeric(4,3) DEFAULT 0 NOT NULL,
    tts_provider TEXT DEFAULT 'google_tts'::TEXT NOT NULL,
    voice_code TEXT NOT NULL,
    preferred_interfaces JSONB DEFAULT '["web"]'::JSONB NOT NULL,
    is_enabled BOOLEAN DEFAULT true NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    learner_category TEXT DEFAULT 'video_student'::TEXT NOT NULL,
    uk_voice_code TEXT NOT NULL,
    en_voice_code TEXT NOT NULL,
    CONSTRAINT ck_video_learner_category CHECK ((learner_category = 'video_student'::TEXT)),
    CONSTRAINT ck_video_learner_mistake_probability CHECK (((mistake_probability >= (0)::numeric) AND (mistake_probability <= (1)::numeric))),
    CONSTRAINT ck_video_learner_words_count_v1 CHECK ((words_count = 5))
);

DROP TABLE IF EXISTS video_publishing_post CASCADE;
CREATE TABLE IF NOT EXISTS video_publishing_post (
    id BIGINT NOT NULL,
    job_id BIGINT NOT NULL,
    target_id BIGINT NOT NULL,
    status TEXT DEFAULT 'queued'::TEXT NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    external_id TEXT,
    external_url TEXT,
    caption TEXT,
    hashtags_jsonb JSONB DEFAULT '[]'::JSONB NOT NULL,
    safe_error_code TEXT,
    safe_error_message TEXT,
    metadata_jsonb JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_video_publishing_post_hashtags_array CHECK ((jsonb_typeof(hashtags_jsonb) = 'array'::TEXT)),
    CONSTRAINT ck_video_publishing_post_metadata_object CHECK ((jsonb_typeof(metadata_jsonb) = 'object'::TEXT)),
    CONSTRAINT ck_video_publishing_post_status CHECK ((status = ANY (ARRAY['queued'::TEXT, 'publishing'::TEXT, 'published'::TEXT, 'failed'::TEXT, 'skipped'::TEXT, 'cancelled'::TEXT])))
);

DROP TABLE IF EXISTS video_publishing_target CASCADE;
CREATE TABLE IF NOT EXISTS video_publishing_target (
    id BIGINT NOT NULL,
    platform TEXT NOT NULL,
    display_name TEXT NOT NULL,
    is_enabled BOOLEAN DEFAULT false NOT NULL,
    connection_status TEXT DEFAULT 'not_configured'::TEXT NOT NULL,
    settings_jsonb JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_video_publishing_target_connection_status CHECK ((connection_status = ANY (ARRAY['not_configured'::TEXT, 'configured'::TEXT, 'needs_reauth'::TEXT, 'disabled'::TEXT]))),
    CONSTRAINT ck_video_publishing_target_platform CHECK ((platform = ANY (ARRAY['tiktok'::TEXT, 'youtube_shorts'::TEXT, 'instagram_reels'::TEXT]))),
    CONSTRAINT ck_video_publishing_target_settings_object CHECK ((jsonb_typeof(settings_jsonb) = 'object'::TEXT))
);

DROP TABLE IF EXISTS video_tracking_link CASCADE;
CREATE TABLE IF NOT EXISTS video_tracking_link (
    id BIGINT NOT NULL,
    job_id BIGINT NOT NULL,
    tracking_code TEXT NOT NULL,
    link_path TEXT NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT ck_video_tracking_link_code_nonempty CHECK ((length(TRIM(BOTH FROM tracking_code)) > 0)),
    CONSTRAINT ck_video_tracking_link_path CHECK ((link_path ~~ '/video/t/%'::TEXT))
);

DROP TABLE IF EXISTS web_login_history CASCADE;
CREATE TABLE IF NOT EXISTS web_login_history (
    id BIGINT NOT NULL,
    user_uuid UUID,
    username_attempted TEXT,
    interface_context TEXT NOT NULL,
    event_type TEXT NOT NULL,
    result TEXT NOT NULL,
    api_origin TEXT,
    api_path TEXT,
    client_ip TEXT,
    user_agent TEXT,
    device_fingerprint_hash TEXT,
    details_json JSONB DEFAULT '{}'::JSONB NOT NULL,
    created TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

ALTER TABLE ONLY acl ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY acl_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY admin_bot_restore ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY admin_magic_link ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY admin_otp_challenge ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY admin_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY ai_provider_pricing_snapshot ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY ai_usage_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY billing_bot_notification ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY billing_offer_acceptance ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY billing_payment ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY billing_payment_event ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY billing_receipt ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY billing_subscription_purchase ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY bot_message_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY client_web_magic_link ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY client_web_otp_challenge ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY client_web_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY dictionary_category ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY dictionary_entry ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY dictionary_part_of_speech ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY error_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY exercise_texts ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY grammar_topics ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY language_level ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY learning_answer ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY learning_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY learning_session_word ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY learning_syllabus_domain ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY learning_syllabus_item ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY monobank_audit_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY task_log ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY teacher_google_oauth_connection ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY teacher_student_group ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY teacher_student_link ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY teacher_student_meet_session ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY training_schedule ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY tts_voices ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY "user" ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_dictionary_entry ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_events ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_level_run ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_reminder_schedule ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_vocabulary_import_item ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_vocabulary_import_job ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY user_word_assignment ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY video_generation_job ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY video_learner ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY video_publishing_post ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY video_publishing_target ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY video_tracking_link ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY web_login_history ALTER COLUMN id ADD GENERATED BY DEFAULT AS IDENTITY;

ALTER TABLE ONLY public.acl_group
    ADD CONSTRAINT acl_group_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.acl_group
    ADD CONSTRAINT acl_group_title_key UNIQUE (title);

ALTER TABLE ONLY public.acl
    ADD CONSTRAINT acl_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.admin_bot_restore
    ADD CONSTRAINT admin_bot_restore_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.admin_credential
    ADD CONSTRAINT admin_credential_pkey PRIMARY KEY (user_uuid);

ALTER TABLE ONLY public.admin_magic_link
    ADD CONSTRAINT admin_magic_link_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.admin_magic_link
    ADD CONSTRAINT admin_magic_link_token_hash_key UNIQUE (token_hash);

ALTER TABLE ONLY public.admin_otp_challenge
    ADD CONSTRAINT admin_otp_challenge_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.admin_session
    ADD CONSTRAINT admin_session_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.admin_session
    ADD CONSTRAINT admin_session_session_token_hash_key UNIQUE (session_token_hash);

ALTER TABLE ONLY public.ai_provider_pricing_snapshot
    ADD CONSTRAINT ai_provider_pricing_snapshot_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.ai_usage_session
    ADD CONSTRAINT ai_usage_session_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.app_runtime_state
    ADD CONSTRAINT app_runtime_state_pkey PRIMARY KEY (key);

ALTER TABLE ONLY public.app_setting
    ADD CONSTRAINT app_setting_pkey PRIMARY KEY (key);

ALTER TABLE ONLY public.app_version
    ADD CONSTRAINT app_version_pkey PRIMARY KEY (key);

ALTER TABLE ONLY public.billing_bot_notification
    ADD CONSTRAINT billing_bot_notification_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_offer_acceptance
    ADD CONSTRAINT billing_offer_acceptance_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_payment_event
    ADD CONSTRAINT billing_payment_event_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_payment
    ADD CONSTRAINT billing_payment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_payment
    ADD CONSTRAINT billing_payment_provider_invoice_id_key UNIQUE (provider_invoice_id);

ALTER TABLE ONLY public.billing_payment
    ADD CONSTRAINT billing_payment_provider_reference_key UNIQUE (provider_reference);

ALTER TABLE ONLY public.billing_receipt
    ADD CONSTRAINT billing_receipt_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_subscription_purchase
    ADD CONSTRAINT billing_subscription_purchase_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.bot_message_log
    ADD CONSTRAINT bot_message_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.client_web_credential
    ADD CONSTRAINT client_web_credential_pkey PRIMARY KEY (user_uuid);

ALTER TABLE ONLY public.client_web_magic_link
    ADD CONSTRAINT client_web_magic_link_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.client_web_magic_link
    ADD CONSTRAINT client_web_magic_link_token_hash_key UNIQUE (token_hash);

ALTER TABLE ONLY public.client_web_otp_challenge
    ADD CONSTRAINT client_web_otp_challenge_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.client_web_session
    ADD CONSTRAINT client_web_session_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.client_web_session
    ADD CONSTRAINT client_web_session_session_token_hash_key UNIQUE (session_token_hash);

ALTER TABLE ONLY public.dictionary_category
    ADD CONSTRAINT dictionary_category_code_key UNIQUE (code);

ALTER TABLE ONLY public.dictionary_category
    ADD CONSTRAINT dictionary_category_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dictionary_entry_category
    ADD CONSTRAINT dictionary_entry_category_pkey PRIMARY KEY (entry_id, category_id);

ALTER TABLE ONLY public.dictionary_entry
    ADD CONSTRAINT dictionary_entry_entry_key_key UNIQUE (entry_key);

ALTER TABLE ONLY public.dictionary_entry_part_of_speech
    ADD CONSTRAINT dictionary_entry_part_of_speech_pkey PRIMARY KEY (entry_id, part_of_speech_id);

ALTER TABLE ONLY public.dictionary_entry
    ADD CONSTRAINT dictionary_entry_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dictionary_entry
    ADD CONSTRAINT dictionary_entry_source_ref_key UNIQUE (source_ref);

ALTER TABLE ONLY public.dictionary_entry_synonym
    ADD CONSTRAINT dictionary_entry_synonym_pkey PRIMARY KEY (left_entry_id, right_entry_id);

ALTER TABLE ONLY public.dictionary_part_of_speech
    ADD CONSTRAINT dictionary_part_of_speech_code_key UNIQUE (code);

ALTER TABLE ONLY public.dictionary_part_of_speech
    ADD CONSTRAINT dictionary_part_of_speech_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.error_log
    ADD CONSTRAINT error_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.exercise_text_topics
    ADD CONSTRAINT exercise_text_topics_pkey PRIMARY KEY (exercise_text_id, grammar_topic_id);

ALTER TABLE ONLY public.exercise_texts
    ADD CONSTRAINT exercise_texts_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.exercise_texts
    ADD CONSTRAINT exercise_texts_uuid_key UNIQUE (UUID);

ALTER TABLE ONLY public.external_provider_task_setting
    ADD CONSTRAINT external_provider_task_setting_pkey PRIMARY KEY (task_key);

ALTER TABLE ONLY public.grammar_topics
    ADD CONSTRAINT grammar_topics_code_key UNIQUE (code);

ALTER TABLE ONLY public.grammar_topics
    ADD CONSTRAINT grammar_topics_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.language_level
    ADD CONSTRAINT language_level_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.language_level
    ADD CONSTRAINT language_level_title_key UNIQUE (title);

ALTER TABLE ONLY public.learning_answer
    ADD CONSTRAINT learning_answer_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.learning_session
    ADD CONSTRAINT learning_session_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.learning_session_word
    ADD CONSTRAINT learning_session_word_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.learning_syllabus_domain
    ADD CONSTRAINT learning_syllabus_domain_code_key UNIQUE (code);

ALTER TABLE ONLY public.learning_syllabus_domain
    ADD CONSTRAINT learning_syllabus_domain_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.learning_syllabus_item
    ADD CONSTRAINT learning_syllabus_item_code_key UNIQUE (code);

ALTER TABLE ONLY public.learning_syllabus_item
    ADD CONSTRAINT learning_syllabus_item_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.monobank_audit_log
    ADD CONSTRAINT monobank_audit_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.task_log
    ADD CONSTRAINT task_log_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.teacher_google_oauth_connection
    ADD CONSTRAINT teacher_google_oauth_connection_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.teacher_student_group
    ADD CONSTRAINT teacher_student_group_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.teacher_student_link
    ADD CONSTRAINT teacher_student_link_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.teacher_student_meet_session
    ADD CONSTRAINT teacher_student_meet_session_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.training_schedule
    ADD CONSTRAINT training_schedule_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.tts_voices
    ADD CONSTRAINT tts_voices_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.billing_bot_notification
    ADD CONSTRAINT uq_billing_bot_notification_payment_type_status UNIQUE (payment_id, notification_type, status_snapshot);

ALTER TABLE ONLY public.billing_subscription_purchase
    ADD CONSTRAINT uq_billing_subscription_purchase_payment UNIQUE (payment_id);

ALTER TABLE ONLY public.learning_syllabus_item
    ADD CONSTRAINT uq_learning_syllabus_item_level_domain_title UNIQUE (level_id, domain_id, normalized_title);

ALTER TABLE ONLY public.teacher_google_oauth_connection
    ADD CONSTRAINT uq_teacher_google_oauth_connection_teacher_provider UNIQUE (teacher_user_uuid, provider);

ALTER TABLE ONLY public.teacher_student_group
    ADD CONSTRAINT uq_teacher_student_group_teacher_title UNIQUE (teacher_user_uuid, title);

ALTER TABLE ONLY public.tts_voices
    ADD CONSTRAINT uq_tts_voices_provider_code UNIQUE (provider, code);

ALTER TABLE ONLY public.user_dictionary_entry
    ADD CONSTRAINT uq_user_dictionary_entry_normalized_word_pos UNIQUE (normalized_word, part_of_speech);

ALTER TABLE ONLY public.user_level_run
    ADD CONSTRAINT uq_user_level_run_user_level_run_no UNIQUE (user_uuid, level_id, run_no);

ALTER TABLE ONLY public.user_reminder_schedule
    ADD CONSTRAINT uq_user_reminder_schedule_user_weekday_time UNIQUE (user_uuid, weekday, hour, minute);

ALTER TABLE ONLY public.user_word_assignment
    ADD CONSTRAINT uq_user_word_assignment_user_source_word UNIQUE (user_uuid, word_source, word_id);

ALTER TABLE ONLY public.user_dictionary_entry
    ADD CONSTRAINT user_dictionary_entry_entry_key_key UNIQUE (entry_key);

ALTER TABLE ONLY public.user_dictionary_entry
    ADD CONSTRAINT user_dictionary_entry_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_events
    ADD CONSTRAINT user_events_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_import_google_doc_progress
    ADD CONSTRAINT user_import_google_doc_progress_pkey PRIMARY KEY (user_uuid, google_doc_id);

ALTER TABLE ONLY public.user_learning_settings
    ADD CONSTRAINT user_learning_settings_pkey PRIMARY KEY (user_uuid);

ALTER TABLE ONLY public.user_level_run
    ADD CONSTRAINT user_level_run_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_reminder_schedule
    ADD CONSTRAINT user_reminder_schedule_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_reminder_weekday
    ADD CONSTRAINT user_reminder_weekday_pkey PRIMARY KEY (user_uuid, weekday);

ALTER TABLE ONLY public.user_subscription
    ADD CONSTRAINT user_subscription_pkey PRIMARY KEY (user_uuid);

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_telegram_user_id_key UNIQUE (telegram_user_id);

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_uuid_key UNIQUE (UUID);

ALTER TABLE ONLY public.user_vocabulary_import_item
    ADD CONSTRAINT user_vocabulary_import_item_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_vocabulary_import_job
    ADD CONSTRAINT user_vocabulary_import_job_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_word_assignment
    ADD CONSTRAINT user_word_assignment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.video_generation_job
    ADD CONSTRAINT video_generation_job_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.video_generation_job
    ADD CONSTRAINT video_generation_job_video_id_key UNIQUE (video_id);

ALTER TABLE ONLY public.video_learner
    ADD CONSTRAINT video_learner_learner_key_key UNIQUE (learner_key);

ALTER TABLE ONLY public.video_learner
    ADD CONSTRAINT video_learner_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.video_learner
    ADD CONSTRAINT video_learner_user_uuid_key UNIQUE (user_uuid);

ALTER TABLE ONLY public.video_publishing_post
    ADD CONSTRAINT video_publishing_post_job_id_target_id_key UNIQUE (job_id, target_id);

ALTER TABLE ONLY public.video_publishing_post
    ADD CONSTRAINT video_publishing_post_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.video_publishing_target
    ADD CONSTRAINT video_publishing_target_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.video_publishing_target
    ADD CONSTRAINT video_publishing_target_platform_key UNIQUE (platform);

ALTER TABLE ONLY public.video_tracking_link
    ADD CONSTRAINT video_tracking_link_job_id_key UNIQUE (job_id);

ALTER TABLE ONLY public.video_tracking_link
    ADD CONSTRAINT video_tracking_link_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.video_tracking_link
    ADD CONSTRAINT video_tracking_link_tracking_code_key UNIQUE (tracking_code);

ALTER TABLE ONLY public.web_login_history
    ADD CONSTRAINT web_login_history_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX idx_acl_group_environment_action ON public.acl USING btree (group_id, environment, action);

CREATE INDEX idx_admin_bot_restore_due ON public.admin_bot_restore USING btree (status, scheduled_for, id);

CREATE INDEX idx_admin_magic_link_active ON public.admin_magic_link USING btree (token_hash, expires) WHERE (consumed IS NULL);

CREATE INDEX idx_admin_magic_link_user_created ON public.admin_magic_link USING btree (user_uuid, created DESC);

CREATE INDEX idx_admin_otp_challenge_user_created ON public.admin_otp_challenge USING btree (user_uuid, created DESC);

CREATE INDEX idx_admin_session_user ON public.admin_session USING btree (user_uuid, expires DESC);

CREATE INDEX idx_ai_provider_pricing_snapshot_lookup ON public.ai_provider_pricing_snapshot USING btree (provider_key, model, unit, observed_at);

CREATE INDEX idx_ai_provider_pricing_snapshot_observed ON public.ai_provider_pricing_snapshot USING btree (observed_at DESC);

CREATE INDEX idx_ai_provider_pricing_snapshot_provider_model ON public.ai_provider_pricing_snapshot USING btree (provider_key, model, observed_at DESC);

CREATE INDEX idx_ai_usage_session_actor ON public.ai_usage_session USING btree (actor_user_uuid);

CREATE INDEX idx_ai_usage_session_created ON public.ai_usage_session USING btree (created DESC);

CREATE INDEX idx_ai_usage_session_scope_model ON public.ai_usage_session USING btree (task_scope, provider_key, model);

CREATE INDEX idx_ai_usage_session_task_started ON public.ai_usage_session USING btree (task_key, started);

CREATE INDEX idx_billing_bot_notification_status_created ON public.billing_bot_notification USING btree (status, created);

CREATE INDEX idx_billing_offer_acceptance_payment ON public.billing_offer_acceptance USING btree (payment_id);

CREATE INDEX idx_billing_offer_acceptance_user_created ON public.billing_offer_acceptance USING btree (user_uuid, created DESC);

CREATE INDEX idx_billing_payment_event_payment_created ON public.billing_payment_event USING btree (payment_id, created DESC);

CREATE INDEX idx_billing_payment_invoice_id ON public.billing_payment USING btree (provider_invoice_id);

CREATE INDEX idx_billing_payment_status_updated ON public.billing_payment USING btree (status, updated);

CREATE INDEX idx_billing_payment_success_recheck ON public.billing_payment USING btree (status, paid_at, success_rechecked_at);

CREATE INDEX idx_billing_payment_user_created ON public.billing_payment USING btree (user_uuid, created DESC);

CREATE INDEX idx_billing_receipt_admin_alert_delivery ON public.billing_receipt USING btree (admin_alert_status, admin_alert_claimed_at, id);

CREATE INDEX idx_billing_receipt_bot_delivery ON public.billing_receipt USING btree (bot_delivery_status, updated, id);

CREATE INDEX idx_billing_receipt_payment_created ON public.billing_receipt USING btree (payment_id, created DESC);

CREATE INDEX idx_billing_receipt_retry_due ON public.billing_receipt USING btree (status, next_retry_at, id);

CREATE INDEX idx_billing_subscription_purchase_payment ON public.billing_subscription_purchase USING btree (payment_id);

CREATE INDEX idx_billing_subscription_purchase_user_period ON public.billing_subscription_purchase USING btree (user_uuid, period_start, period_end);

CREATE INDEX idx_bot_message_log_due_cleanup ON public.bot_message_log USING btree (status, delete_after, updated, id) WHERE (deleted IS NULL);

CREATE INDEX idx_bot_message_log_user_created ON public.bot_message_log USING btree (telegram_user_id, created DESC);

CREATE INDEX idx_client_web_magic_link_active ON public.client_web_magic_link USING btree (token_hash, expires) WHERE (consumed IS NULL);

CREATE INDEX idx_client_web_session_user ON public.client_web_session USING btree (user_uuid, expires DESC);

CREATE INDEX idx_dictionary_entry_category_lookup ON public.dictionary_entry_category USING btree (category_id, entry_id);

CREATE INDEX idx_dictionary_entry_entry_type ON public.dictionary_entry USING btree (entry_type);

CREATE INDEX idx_dictionary_entry_is_archived ON public.dictionary_entry USING btree (is_archived);

CREATE INDEX idx_dictionary_entry_is_embedding_ready ON public.dictionary_entry USING btree (is_embedding_ready);

CREATE INDEX idx_dictionary_entry_level_id ON public.dictionary_entry USING btree (level_id);

CREATE INDEX idx_dictionary_entry_normalized_word ON public.dictionary_entry USING btree (normalized_word);

CREATE INDEX idx_dictionary_entry_part_of_speech_lookup ON public.dictionary_entry_part_of_speech USING btree (part_of_speech_id, entry_id);

CREATE INDEX idx_dictionary_entry_source_namespace_legacy_id ON public.dictionary_entry USING btree (source_namespace, source_legacy_id);

CREATE INDEX idx_dictionary_entry_synonym_right ON public.dictionary_entry_synonym USING btree (right_entry_id, left_entry_id);

CREATE INDEX idx_dictionary_entry_teacher_verified ON public.dictionary_entry USING btree (is_teacher_verified, word, id);

CREATE INDEX idx_exercise_text_topics_topic ON public.exercise_text_topics USING btree (grammar_topic_id, exercise_text_id);

CREATE INDEX idx_exercise_texts_difficulty_updated ON public.exercise_texts USING btree (difficulty_band, updated DESC);

CREATE INDEX idx_exercise_texts_status_updated ON public.exercise_texts USING btree (status, updated DESC);

CREATE INDEX idx_grammar_topics_active_level_title ON public.grammar_topics USING btree (is_active, level, title);

CREATE INDEX idx_learning_answer_session_created ON public.learning_answer USING btree (session_id, created DESC);

CREATE INDEX idx_learning_session_level_run_status ON public.learning_session USING btree (level_run_id, status, created DESC);

CREATE INDEX idx_learning_session_user_status ON public.learning_session USING btree (user_uuid, status, created DESC);

CREATE INDEX idx_learning_session_word_session_order ON public.learning_session_word USING btree (session_id, item_order);

CREATE INDEX idx_learning_syllabus_item_level_domain_order ON public.learning_syllabus_item USING btree (level_id, domain_id, sort_order);

CREATE INDEX idx_monobank_audit_log_actor_created ON public.monobank_audit_log USING btree (actor_user_uuid, created DESC);

CREATE INDEX idx_monobank_audit_log_direction_created ON public.monobank_audit_log USING btree (direction, created DESC);

CREATE INDEX idx_monobank_audit_log_invoice_created ON public.monobank_audit_log USING btree (invoice_id, created DESC);

CREATE INDEX idx_monobank_audit_log_payment_created ON public.monobank_audit_log USING btree (payment_id, created DESC);

CREATE INDEX idx_task_log_status_created ON public.task_log USING btree (status, created DESC);

CREATE INDEX idx_task_log_type_created ON public.task_log USING btree (task_type, created DESC);

CREATE INDEX idx_task_log_user_created ON public.task_log USING btree (user_uuid, created DESC);

CREATE INDEX idx_teacher_student_group_teacher_status ON public.teacher_student_group USING btree (teacher_user_uuid, status, title);

CREATE INDEX idx_teacher_student_link_student_status ON public.teacher_student_link USING btree (student_user_uuid, status);

CREATE INDEX idx_teacher_student_link_teacher_status ON public.teacher_student_link USING btree (teacher_user_uuid, status);

CREATE INDEX idx_teacher_student_meet_session_lookup ON public.teacher_student_meet_session USING btree (teacher_user_uuid, student_user_uuid, status, created DESC);

CREATE INDEX idx_telegram_users_username ON public."user" USING btree (username);

CREATE UNIQUE INDEX idx_training_schedule_daily_unique ON public.training_schedule USING btree (user_uuid, schedule_type, scheduled_for) WHERE ((schedule_type = 'daily'::TEXT) AND (status = ANY (ARRAY['pending'::TEXT, 'sent'::TEXT, 'completed'::TEXT, 'skipped'::TEXT])));

CREATE INDEX idx_training_schedule_due ON public.training_schedule USING btree (status, scheduled_for, user_uuid);

CREATE INDEX idx_tts_voices_provider_active_order ON public.tts_voices USING btree (provider, is_active, sort_order, display_name);

CREATE INDEX idx_user_dictionary_entry_created_by_user ON public.user_dictionary_entry USING btree (created_by_user_uuid);

CREATE INDEX idx_user_dictionary_entry_normalized_word ON public.user_dictionary_entry USING btree (normalized_word);

CREATE INDEX idx_user_dictionary_entry_promoted ON public.user_dictionary_entry USING btree (promoted_dictionary_entry_id);

CREATE INDEX idx_user_dictionary_entry_status ON public.user_dictionary_entry USING btree (status);

CREATE INDEX idx_user_events_user_created ON public.user_events USING btree (telegram_user_id, created DESC);

CREATE UNIQUE INDEX idx_user_level_run_active_unique ON public.user_level_run USING btree (user_uuid, level_id) WHERE (status = 'active'::TEXT);

CREATE INDEX idx_user_level_run_user_level_created ON public.user_level_run USING btree (user_uuid, level_id, created DESC, id DESC);

CREATE INDEX idx_user_reminder_schedule_lookup ON public.user_reminder_schedule USING btree (user_uuid, weekday, status, hour, minute);

CREATE INDEX idx_user_reminder_weekday_lookup ON public.user_reminder_weekday USING btree (user_uuid, weekday);

CREATE UNIQUE INDEX idx_user_vocabulary_import_item_job_lookup_unique ON public.user_vocabulary_import_item USING btree (import_job_id, lookup_word);

CREATE INDEX idx_user_vocabulary_import_item_status ON public.user_vocabulary_import_item USING btree (status, import_job_id);

CREATE INDEX idx_user_vocabulary_import_item_task_log ON public.user_vocabulary_import_item USING btree (task_log_id);

CREATE INDEX idx_user_vocabulary_import_item_user_dictionary_entry ON public.user_vocabulary_import_item USING btree (user_dictionary_entry_id);

CREATE INDEX idx_user_vocabulary_import_job_status ON public.user_vocabulary_import_job USING btree (status, summary_sent);

CREATE INDEX idx_user_vocabulary_import_job_task_log ON public.user_vocabulary_import_job USING btree (task_log_id);

CREATE INDEX idx_user_vocabulary_import_job_user ON public.user_vocabulary_import_job USING btree (user_uuid, created);

CREATE INDEX idx_user_word_assignment_import_job ON public.user_word_assignment USING btree (import_job_id);

CREATE INDEX idx_user_word_assignment_source_word ON public.user_word_assignment USING btree (word_source, word_id);

CREATE INDEX idx_user_word_assignment_user_last_seen ON public.user_word_assignment USING btree (user_uuid, status, last_seen_at);

CREATE INDEX idx_user_word_assignment_user_learning ON public.user_word_assignment USING btree (user_uuid, status, learning_state);

CREATE INDEX idx_user_word_assignment_user_priority_state ON public.user_word_assignment USING btree (user_uuid, status, priority_state, priority_rank DESC);

CREATE INDEX idx_user_word_assignment_user_review ON public.user_word_assignment USING btree (user_uuid, status, next_review_at, review_priority DESC);

CREATE INDEX idx_user_word_assignment_user_status ON public.user_word_assignment USING btree (user_uuid, status);

CREATE INDEX idx_user_word_assignment_user_status_rank ON public.user_word_assignment USING btree (user_uuid, status, priority_rank DESC);

CREATE INDEX idx_video_generation_job_learner_status ON public.video_generation_job USING btree (learner_id, status, created);

CREATE INDEX idx_video_generation_job_lesson_review ON public.video_generation_job USING btree (lesson_id, review_status, created);

CREATE INDEX idx_video_generation_job_review_pool ON public.video_generation_job USING btree (review_status, updated);

CREATE INDEX idx_video_publishing_post_status ON public.video_publishing_post USING btree (status);

CREATE INDEX idx_video_publishing_post_target_status ON public.video_publishing_post USING btree (target_id, status);

CREATE INDEX idx_video_tracking_link_job ON public.video_tracking_link USING btree (job_id);

CREATE INDEX idx_web_login_history_created ON public.web_login_history USING btree (created DESC);

CREATE INDEX idx_web_login_history_user_created ON public.web_login_history USING btree (user_uuid, created DESC);

ALTER TABLE ONLY public.acl
    ADD CONSTRAINT acl_group_id_fkey FOREIGN KEY (group_id) REFERENCES public.acl_group(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.acl_group
    ADD CONSTRAINT acl_group_parent_group_id_fkey FOREIGN KEY (parent_group_id) REFERENCES public.acl_group(id);

ALTER TABLE ONLY public.admin_bot_restore
    ADD CONSTRAINT admin_bot_restore_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.admin_credential
    ADD CONSTRAINT admin_credential_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.admin_magic_link
    ADD CONSTRAINT admin_magic_link_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.admin_otp_challenge
    ADD CONSTRAINT admin_otp_challenge_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.admin_session
    ADD CONSTRAINT admin_session_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.billing_bot_notification
    ADD CONSTRAINT billing_bot_notification_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.billing_payment(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.billing_offer_acceptance
    ADD CONSTRAINT billing_offer_acceptance_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.billing_payment(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.billing_offer_acceptance
    ADD CONSTRAINT billing_offer_acceptance_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.billing_payment_event
    ADD CONSTRAINT billing_payment_event_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.billing_payment(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.billing_payment
    ADD CONSTRAINT billing_payment_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.billing_receipt
    ADD CONSTRAINT billing_receipt_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.billing_payment(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.billing_subscription_purchase
    ADD CONSTRAINT billing_subscription_purchase_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.billing_payment(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.billing_subscription_purchase
    ADD CONSTRAINT billing_subscription_purchase_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.bot_message_log
    ADD CONSTRAINT bot_message_log_telegram_user_id_fkey FOREIGN KEY (telegram_user_id) REFERENCES public."user"(telegram_user_id) ON DELETE CASCADE;

ALTER TABLE ONLY public.client_web_credential
    ADD CONSTRAINT client_web_credential_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.client_web_magic_link
    ADD CONSTRAINT client_web_magic_link_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.client_web_otp_challenge
    ADD CONSTRAINT client_web_otp_challenge_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.client_web_session
    ADD CONSTRAINT client_web_session_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry_category
    ADD CONSTRAINT dictionary_entry_category_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.dictionary_category(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry_category
    ADD CONSTRAINT dictionary_entry_category_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.dictionary_entry(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry
    ADD CONSTRAINT dictionary_entry_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.language_level(id);

ALTER TABLE ONLY public.dictionary_entry_part_of_speech
    ADD CONSTRAINT dictionary_entry_part_of_speech_entry_id_fkey FOREIGN KEY (entry_id) REFERENCES public.dictionary_entry(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry_part_of_speech
    ADD CONSTRAINT dictionary_entry_part_of_speech_part_of_speech_id_fkey FOREIGN KEY (part_of_speech_id) REFERENCES public.dictionary_part_of_speech(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry_synonym
    ADD CONSTRAINT dictionary_entry_synonym_left_entry_id_fkey FOREIGN KEY (left_entry_id) REFERENCES public.dictionary_entry(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry_synonym
    ADD CONSTRAINT dictionary_entry_synonym_right_entry_id_fkey FOREIGN KEY (right_entry_id) REFERENCES public.dictionary_entry(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dictionary_entry
    ADD CONSTRAINT dictionary_entry_teacher_verified_by_user_uuid_fkey FOREIGN KEY (teacher_verified_by_user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

ALTER TABLE ONLY public.exercise_text_topics
    ADD CONSTRAINT exercise_text_topics_exercise_text_id_fkey FOREIGN KEY (exercise_text_id) REFERENCES public.exercise_texts(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.exercise_text_topics
    ADD CONSTRAINT exercise_text_topics_grammar_topic_id_fkey FOREIGN KEY (grammar_topic_id) REFERENCES public.grammar_topics(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.exercise_texts
    ADD CONSTRAINT exercise_texts_created_by_user_uuid_fkey FOREIGN KEY (created_by_user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

ALTER TABLE ONLY public.exercise_texts
    ADD CONSTRAINT exercise_texts_updated_by_user_uuid_fkey FOREIGN KEY (updated_by_user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

ALTER TABLE ONLY public.teacher_student_link
    ADD CONSTRAINT fk_teacher_student_link_group_id FOREIGN KEY (group_id) REFERENCES public.teacher_student_group(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.learning_answer
    ADD CONSTRAINT learning_answer_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.learning_session(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_answer
    ADD CONSTRAINT learning_answer_session_word_id_fkey FOREIGN KEY (session_word_id) REFERENCES public.learning_session_word(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_session
    ADD CONSTRAINT learning_session_language_level_id_fkey FOREIGN KEY (language_level_id) REFERENCES public.language_level(id);

ALTER TABLE ONLY public.learning_session
    ADD CONSTRAINT learning_session_level_run_id_fkey FOREIGN KEY (level_run_id) REFERENCES public.user_level_run(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.learning_session
    ADD CONSTRAINT learning_session_source_session_id_fkey FOREIGN KEY (source_session_id) REFERENCES public.learning_session(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.learning_session
    ADD CONSTRAINT learning_session_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_session_word
    ADD CONSTRAINT learning_session_word_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.learning_session(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_syllabus_item
    ADD CONSTRAINT learning_syllabus_item_domain_id_fkey FOREIGN KEY (domain_id) REFERENCES public.learning_syllabus_domain(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.learning_syllabus_item
    ADD CONSTRAINT learning_syllabus_item_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.language_level(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.monobank_audit_log
    ADD CONSTRAINT monobank_audit_log_actor_user_uuid_fkey FOREIGN KEY (actor_user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

ALTER TABLE ONLY public.monobank_audit_log
    ADD CONSTRAINT monobank_audit_log_payment_id_fkey FOREIGN KEY (payment_id) REFERENCES public.billing_payment(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.task_log
    ADD CONSTRAINT task_log_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

ALTER TABLE ONLY public.teacher_google_oauth_connection
    ADD CONSTRAINT teacher_google_oauth_connection_teacher_user_uuid_fkey FOREIGN KEY (teacher_user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.teacher_student_group
    ADD CONSTRAINT teacher_student_group_teacher_user_uuid_fkey FOREIGN KEY (teacher_user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.teacher_student_link
    ADD CONSTRAINT teacher_student_link_student_user_uuid_fkey FOREIGN KEY (student_user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.teacher_student_link
    ADD CONSTRAINT teacher_student_link_teacher_user_uuid_fkey FOREIGN KEY (teacher_user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.teacher_student_meet_session
    ADD CONSTRAINT teacher_student_meet_session_student_user_uuid_fkey FOREIGN KEY (student_user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.teacher_student_meet_session
    ADD CONSTRAINT teacher_student_meet_session_teacher_user_uuid_fkey FOREIGN KEY (teacher_user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.training_schedule
    ADD CONSTRAINT training_schedule_source_session_id_fkey FOREIGN KEY (source_session_id) REFERENCES public.learning_session(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.training_schedule
    ADD CONSTRAINT training_schedule_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_acl_group_id_fkey FOREIGN KEY (acl_group_id) REFERENCES public.acl_group(id);

ALTER TABLE ONLY public.user_dictionary_entry
    ADD CONSTRAINT user_dictionary_entry_created_by_user_uuid_fkey FOREIGN KEY (created_by_user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_dictionary_entry
    ADD CONSTRAINT user_dictionary_entry_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.language_level(id);

ALTER TABLE ONLY public.user_dictionary_entry
    ADD CONSTRAINT user_dictionary_entry_promoted_dictionary_entry_id_fkey FOREIGN KEY (promoted_dictionary_entry_id) REFERENCES public.dictionary_entry(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_events
    ADD CONSTRAINT user_events_telegram_user_id_fkey FOREIGN KEY (telegram_user_id) REFERENCES public."user"(telegram_user_id);

ALTER TABLE ONLY public.user_import_google_doc_progress
    ADD CONSTRAINT user_import_google_doc_progress_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_language_level_id_fkey FOREIGN KEY (language_level_id) REFERENCES public.language_level(id);

ALTER TABLE ONLY public.user_learning_settings
    ADD CONSTRAINT user_learning_settings_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_level_run
    ADD CONSTRAINT user_level_run_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.language_level(id);

ALTER TABLE ONLY public.user_level_run
    ADD CONSTRAINT user_level_run_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_reminder_schedule
    ADD CONSTRAINT user_reminder_schedule_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_reminder_weekday
    ADD CONSTRAINT user_reminder_weekday_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_subscription
    ADD CONSTRAINT user_subscription_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_vocabulary_import_item
    ADD CONSTRAINT user_vocabulary_import_item_existing_word_id_fkey FOREIGN KEY (existing_word_id) REFERENCES public.dictionary_entry(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_vocabulary_import_item
    ADD CONSTRAINT user_vocabulary_import_item_import_job_id_fkey FOREIGN KEY (import_job_id) REFERENCES public.user_vocabulary_import_job(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_vocabulary_import_item
    ADD CONSTRAINT user_vocabulary_import_item_task_log_id_fkey FOREIGN KEY (task_log_id) REFERENCES public.task_log(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_vocabulary_import_item
    ADD CONSTRAINT user_vocabulary_import_item_user_dictionary_entry_id_fkey FOREIGN KEY (user_dictionary_entry_id) REFERENCES public.user_dictionary_entry(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_vocabulary_import_item
    ADD CONSTRAINT user_vocabulary_import_item_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_vocabulary_import_job
    ADD CONSTRAINT user_vocabulary_import_job_task_log_id_fkey FOREIGN KEY (task_log_id) REFERENCES public.task_log(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_vocabulary_import_job
    ADD CONSTRAINT user_vocabulary_import_job_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_word_assignment
    ADD CONSTRAINT user_word_assignment_import_item_id_fkey FOREIGN KEY (import_item_id) REFERENCES public.user_vocabulary_import_item(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_word_assignment
    ADD CONSTRAINT user_word_assignment_import_job_id_fkey FOREIGN KEY (import_job_id) REFERENCES public.user_vocabulary_import_job(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_word_assignment
    ADD CONSTRAINT user_word_assignment_last_level_run_id_fkey FOREIGN KEY (last_level_run_id) REFERENCES public.user_level_run(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.user_word_assignment
    ADD CONSTRAINT user_word_assignment_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.video_generation_job
    ADD CONSTRAINT video_generation_job_learner_id_fkey FOREIGN KEY (learner_id) REFERENCES public.video_learner(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.video_learner
    ADD CONSTRAINT video_learner_level_id_fkey FOREIGN KEY (level_id) REFERENCES public.language_level(id);

ALTER TABLE ONLY public.video_learner
    ADD CONSTRAINT video_learner_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE CASCADE;

ALTER TABLE ONLY public.video_publishing_post
    ADD CONSTRAINT video_publishing_post_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.video_generation_job(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.video_publishing_post
    ADD CONSTRAINT video_publishing_post_target_id_fkey FOREIGN KEY (target_id) REFERENCES public.video_publishing_target(id) ON DELETE RESTRICT;

ALTER TABLE ONLY public.video_tracking_link
    ADD CONSTRAINT video_tracking_link_job_id_fkey FOREIGN KEY (job_id) REFERENCES public.video_generation_job(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.web_login_history
    ADD CONSTRAINT web_login_history_user_uuid_fkey FOREIGN KEY (user_uuid) REFERENCES public."user"(UUID) ON DELETE SET NULL;

\unrestrict eqFnSAjvGYTgSsKlWthYiWOVHkJ5i6ep7OdHpEPC485RY8hGjFESyaSSOhI1Brp

-- BASELINE DML SEEDS (SYSTEM REFERENCE DATA)

-- App Settings Setup
INSERT INTO app_setting (key, value_json)
VALUES
    ('billing.monobank_mode', '{"monobank_mode": "disabled"}'::JSONB),
    (
        'billing.runtime_settings',
        jsonb_build_object(
            'monobank_mode', 'disabled',
            'enabled_period_months', '[1, 3, 6, 12]'::JSONB,
            'plan_prices_uah', '{
                "premium": {"1": 10, "3": 30, "6": 60, "12": 120},
                "premium_plus": {"1": 20, "3": 60, "6": 120, "12": 240}
            }'::JSONB,
            'invoice_validity_seconds', 3600,
            'webhook_wait_seconds', 20,
            'frontend_poll_interval_seconds', 10,
            'frontend_poll_timeout_seconds', 60,
            'long_processing_seconds', 60,
            'reconciliation_interval_seconds', 3600,
            'subscription_recovery_interval_seconds', 600,
            'receipt_retry_interval_seconds', 2,
            'receipt_retry_delay_seconds', 2,
            'receipt_retry_max_attempts', 3,
            'success_recheck_interval_days', 7,
            'success_recheck_hour', 6,
            'success_recheck_window_days', 7,
            'subscription_expiration_hour', 0,
            'offer_text', $$CronoLex subscription offer

By buying a paid CronoLex subscription, you get access to the selected paid plan for the selected period. The subscription starts only after the payment provider confirms successful payment.

The user IS responsible for entering correct payment data ON the Monobank payment page. CronoLex does not store card numbers or bank authentication data.

If payment IS still processing, CronoLex may notify the user about the final status IN Telegram. Paid access IS granted only after a successful payment status.

Paid subscriptions are not manually downgraded to the free plan by the user. After the paid period expires, CronoLex automatically switches the subscription back to the free plan.

Support questions can be sent through the support link configured IN CronoLex.$$
        )
    )
ON CONFLICT (key) DO NOTHING;

-- Language Levels Descriptions Setup
UPDATE language_level
SET description = seed.description
FROM (
    VALUES
        ('A1', 'Survival English / Базовое выживание'),
        ('A2', 'Everyday Communication'),
        ('B1', 'Independent User'),
        ('B2', 'Upper-Intermediate / Professional Communication'),
        ('C1', 'Advanced / Near-Fluent')
) AS seed(title, description)
WHERE language_level.title = seed.title;

-- Syllabus Domains Setup
INSERT INTO learning_syllabus_domain (code, title, sort_order)
VALUES
    ('grammar', 'Grammar', 10),
    ('vocabulary_theme', 'Vocabulary Themes', 20),
    ('functional_skill', 'Functional Skills', 30)
ON CONFLICT (code) DO UPDATE
SET
    title = EXCLUDED.title,
    sort_order = EXCLUDED.sort_order;

-- Syllabus Items Setup
WITH seed(level_title, domain_code, item_code, title, sort_order) AS (
    VALUES
        ('A1', 'grammar', 'a1_grammar_alphabet_pronunciation_basics', 'Alphabet & pronunciation basics', 10),
        ('A1', 'grammar', 'a1_grammar_personal_pronouns', 'Personal pronouns', 20),
        ('A1', 'grammar', 'a1_grammar_verb_to_be', 'Verb "to be"', 30),
        ('A1', 'grammar', 'a1_grammar_articles_a_an_the', 'Articles (a/an/the)', 40),
        ('A1', 'grammar', 'a1_grammar_singular_plural_nouns', 'Singular / plural nouns', 50),
        ('A1', 'grammar', 'a1_grammar_possessives', 'Possessives (''s, my, your, etc.)', 60),
        ('A1', 'grammar', 'a1_grammar_basic_adjectives', 'Basic adjectives', 70),
        ('A1', 'grammar', 'a1_grammar_present_simple', 'Present Simple', 80),
        ('A1', 'grammar', 'a1_grammar_basic_question_forms', 'Basic question forms', 90),
        ('A1', 'grammar', 'a1_grammar_there_is_there_are', 'There IS / There are', 100),
        ('A1', 'grammar', 'a1_grammar_countable_vs_uncountable_nouns', 'Countable vs uncountable nouns', 110),
        ('A1', 'grammar', 'a1_grammar_some_any', 'Some / any', 120),
        ('A1', 'grammar', 'a1_grammar_basic_prepositions_of_place', 'Basic prepositions of place', 130),
        ('A1', 'grammar', 'a1_grammar_can_cant', 'Can / can''t', 140),
        ('A1', 'grammar', 'a1_grammar_present_continuous', 'Present Continuous', 150),
        ('A1', 'grammar', 'a1_grammar_basic_adverbs_of_frequency', 'Basic adverbs of frequency', 160),
        ('A1', 'grammar', 'a1_grammar_past_simple', 'Past Simple (regular + common irregular)', 170),
        ('A1', 'grammar', 'a1_grammar_future_going_to', 'Future with "going to"', 180),
        ('A1', 'grammar', 'a1_grammar_comparative_adjectives', 'Comparative adjectives', 190),
        ('A1', 'grammar', 'a1_grammar_superlatives', 'Superlatives', 200),
        ('A1', 'grammar', 'a1_grammar_basic_conjunctions', 'Basic conjunctions (and, but, because)', 210),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_greetings_introductions', 'Greetings & introductions', 10),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_family', 'Family', 20),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_numbers_time', 'Numbers & time', 30),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_countries_nationalities', 'Countries & nationalities', 40),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_jobs', 'Jobs', 50),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_daily_routine', 'Daily routine', 60),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_food_drinks', 'Food & drinks', 70),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_shopping', 'Shopping', 80),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_home_furniture', 'Home & furniture', 90),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_city_places', 'City places', 100),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_transport', 'Transport', 110),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_weather', 'Weather', 120),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_hobbies', 'Hobbies', 130),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_clothes', 'Clothes', 140),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_body_health_basics', 'Body & health basics', 150),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_travel_basics', 'Travel basics', 160),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_basic_emotions', 'Basic emotions', 170),
        ('A1', 'vocabulary_theme', 'a1_vocabulary_technology_basics', 'Technology basics', 180),
        ('A1', 'functional_skill', 'a1_skill_introduce_yourself', 'Introduce yourself', 10),
        ('A1', 'functional_skill', 'a1_skill_ask_simple_questions', 'Ask simple questions', 20),
        ('A1', 'functional_skill', 'a1_skill_order_food', 'Order food', 30),
        ('A1', 'functional_skill', 'a1_skill_buy_something', 'Buy something', 40),
        ('A1', 'functional_skill', 'a1_skill_describe_routine', 'Describe routine', 50),
        ('A1', 'functional_skill', 'a1_skill_describe_people_things', 'Describe people/things', 60),
        ('A1', 'functional_skill', 'a1_skill_talk_about_yesterday', 'Talk about yesterday', 70),
        ('A1', 'functional_skill', 'a1_skill_make_simple_plans', 'Make simple plans', 80),

        ('A2', 'grammar', 'a2_grammar_present_perfect_basics', 'Present Perfect basics', 10),
        ('A2', 'grammar', 'a2_grammar_past_continuous', 'Past Continuous', 20),
        ('A2', 'grammar', 'a2_grammar_future_will', 'Future with "will"', 30),
        ('A2', 'grammar', 'a2_grammar_first_conditional', 'First Conditional', 40),
        ('A2', 'grammar', 'a2_grammar_modal_verbs', 'Modal verbs (must, should, have to)', 50),
        ('A2', 'grammar', 'a2_grammar_gerunds_infinitives_basics', 'Gerunds & infinitives basics', 60),
        ('A2', 'grammar', 'a2_grammar_too_enough', 'Too / enough', 70),
        ('A2', 'grammar', 'a2_grammar_reflexive_pronouns', 'Reflexive pronouns', 80),
        ('A2', 'grammar', 'a2_grammar_relative_clauses_basics', 'Relative clauses basics', 90),
        ('A2', 'grammar', 'a2_grammar_present_perfect_vs_past_simple', 'Present Perfect vs Past Simple', 100),
        ('A2', 'grammar', 'a2_grammar_comparative_structures', 'Comparative structures', 110),
        ('A2', 'grammar', 'a2_grammar_quantifiers', 'Quantifiers', 120),
        ('A2', 'grammar', 'a2_grammar_indefinite_pronouns', 'Indefinite pronouns', 130),
        ('A2', 'grammar', 'a2_grammar_used_to', 'Used to', 140),
        ('A2', 'grammar', 'a2_grammar_basic_passive_voice', 'Basic passive voice', 150),
        ('A2', 'grammar', 'a2_grammar_adverbs_of_manner', 'Adverbs of manner', 160),
        ('A2', 'grammar', 'a2_grammar_phrasal_verbs_basics', 'Phrasal verbs basics', 170),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_education', 'Education', 10),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_work_routines', 'Work routines', 20),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_restaurants_cooking', 'Restaurants & cooking', 30),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_free_time', 'Free time', 40),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_internet_apps', 'Internet & apps', 50),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_relationships', 'Relationships', 60),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_health_fitness', 'Health & fitness', 70),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_nature', 'Nature', 80),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_entertainment', 'Entertainment', 90),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_holidays_tourism', 'Holidays & tourism', 100),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_money', 'Money', 110),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_problems_accidents', 'Problems & accidents', 120),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_communication', 'Communication', 130),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_housing', 'Housing', 140),
        ('A2', 'vocabulary_theme', 'a2_vocabulary_personality', 'Personality', 150),
        ('A2', 'functional_skill', 'a2_skill_tell_stories', 'Tell stories', 10),
        ('A2', 'functional_skill', 'a2_skill_give_advice', 'Give advice', 20),
        ('A2', 'functional_skill', 'a2_skill_make_suggestions', 'Make suggestions', 30),
        ('A2', 'functional_skill', 'a2_skill_describe_experiences', 'Describe experiences', 40),
        ('A2', 'functional_skill', 'a2_skill_express_opinions', 'Express opinions', 50),
        ('A2', 'functional_skill', 'a2_skill_compare_things', 'Compare things', 60),
        ('A2', 'functional_skill', 'a2_skill_handle_travel_situations', 'Handle travel situations', 70),
        ('A2', 'functional_skill', 'a2_skill_explain_problems', 'Explain problems', 80),

        ('B1', 'grammar', 'b1_grammar_present_perfect_continuous', 'Present Perfect Continuous', 10),
        ('B1', 'grammar', 'b1_grammar_second_conditional', 'Second Conditional', 20),
        ('B1', 'grammar', 'b1_grammar_passive_voice_expanded', 'Passive voice expanded', 30),
        ('B1', 'grammar', 'b1_grammar_reported_speech_basics', 'Reported speech basics', 40),
        ('B1', 'grammar', 'b1_grammar_relative_clauses', 'Relative clauses', 50),
        ('B1', 'grammar', 'b1_grammar_modals_of_deduction', 'Modals of deduction', 60),
        ('B1', 'grammar', 'b1_grammar_past_perfect', 'Past Perfect', 70),
        ('B1', 'grammar', 'b1_grammar_future_continuous', 'Future Continuous', 80),
        ('B1', 'grammar', 'b1_grammar_future_perfect_basics', 'Future Perfect basics', 90),
        ('B1', 'grammar', 'b1_grammar_zero_conditional', 'Zero Conditional', 100),
        ('B1', 'grammar', 'b1_grammar_verb_patterns', 'Verb patterns', 110),
        ('B1', 'grammar', 'b1_grammar_wish_if_only_basics', 'Wish / if only basics', 120),
        ('B1', 'grammar', 'b1_grammar_articles_deeper_usage', 'Articles deeper usage', 130),
        ('B1', 'grammar', 'b1_grammar_linking_words', 'Linking words', 140),
        ('B1', 'grammar', 'b1_grammar_causatives', 'Causatives (have/get something done)', 150),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_career_interviews', 'Career & interviews', 10),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_business_communication', 'Business communication', 20),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_social_media', 'Social media', 30),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_crime_law', 'Crime & law', 40),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_environment', 'Environment', 50),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_science_basics', 'Science basics', 60),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_emotions_psychology', 'Emotions & psychology', 70),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_culture', 'Culture', 80),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_news_media', 'News & media', 90),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_relationships_conflicts', 'Relationships & conflicts', 100),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_technology', 'Technology', 110),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_personal_development', 'Personal development', 120),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_education_systems', 'Education systems', 130),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_global_issues', 'Global issues', 140),
        ('B1', 'vocabulary_theme', 'b1_vocabulary_everyday_finance', 'Everyday finance', 150),
        ('B1', 'functional_skill', 'b1_skill_hold_conversations_naturally', 'Hold conversations naturally', 10),
        ('B1', 'functional_skill', 'b1_skill_explain_opinions_in_detail', 'Explain opinions IN detail', 20),
        ('B1', 'functional_skill', 'b1_skill_write_emails_messages', 'Write emails/messages', 30),
        ('B1', 'functional_skill', 'b1_skill_discuss_goals', 'Discuss goals', 40),
        ('B1', 'functional_skill', 'b1_skill_solve_misunderstandings', 'Solve misunderstandings', 50),
        ('B1', 'functional_skill', 'b1_skill_participate_in_meetings', 'Participate IN meetings', 60),
        ('B1', 'functional_skill', 'b1_skill_describe_processes', 'Describe processes', 70),
        ('B1', 'functional_skill', 'b1_skill_retell_articles_videos', 'Retell articles/videos', 80),

        ('B2', 'grammar', 'b2_grammar_third_conditional', 'Third Conditional', 10),
        ('B2', 'grammar', 'b2_grammar_mixed_conditionals', 'Mixed Conditionals', 20),
        ('B2', 'grammar', 'b2_grammar_advanced_reported_speech', 'Advanced reported speech', 30),
        ('B2', 'grammar', 'b2_grammar_inversion_basics', 'Inversion basics', 40),
        ('B2', 'grammar', 'b2_grammar_advanced_passive_structures', 'Advanced passive structures', 50),
        ('B2', 'grammar', 'b2_grammar_modal_nuances', 'Modals of deduction', 60),
        ('B2', 'grammar', 'b2_grammar_future_perfect_continuous', 'Future Perfect Continuous', 70),
        ('B2', 'grammar', 'b2_grammar_advanced_relative_clauses', 'Advanced relative clauses', 80),
        ('B2', 'grammar', 'b2_grammar_participle_clauses', 'Participle clauses', 90),
        ('B2', 'grammar', 'b2_grammar_discourse_markers', 'Discourse markers', 100),
        ('B2', 'grammar', 'b2_grammar_hedging_language', 'Hedging language', 110),
        ('B2', 'grammar', 'b2_grammar_advanced_article_usage', 'Advanced article usage', 120),
        ('B2', 'grammar', 'b2_grammar_complex_noun_phrases', 'Complex noun phrases', 130),
        ('B2', 'grammar', 'b2_grammar_emphasis_structures', 'Emphasis structures', 140),
        ('B2', 'grammar', 'b2_grammar_subjunctive_basics', 'Subjunctive basics', 150),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_management', 'Management', 10),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_startups_business', 'Startups & business', 20),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_negotiation', 'Negotiation', 30),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_economics_basics', 'Economics basics', 40),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_politics', 'Politics', 50),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_advanced_technology', 'Advanced technology', 60),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_ai_innovation', 'AI & innovation', 70),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_psychology', 'Psychology', 80),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_healthcare', 'Healthcare', 90),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_academic_topics', 'Academic topics', 100),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_marketing', 'Marketing', 110),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_productivity', 'Productivity', 120),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_leadership', 'Leadership', 130),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_cultural_differences', 'Cultural differences', 140),
        ('B2', 'vocabulary_theme', 'b2_vocabulary_global_business', 'Global business', 150),
        ('B2', 'functional_skill', 'b2_skill_debate', 'Debate', 10),
        ('B2', 'functional_skill', 'b2_skill_persuade', 'Persuade', 20),
        ('B2', 'functional_skill', 'b2_skill_present_ideas', 'Present ideas', 30),
        ('B2', 'functional_skill', 'b2_skill_explain_abstract_concepts', 'Explain abstract concepts', 40),
        ('B2', 'functional_skill', 'b2_skill_handle_conflict_professionally', 'Handle conflict professionally', 50),
        ('B2', 'functional_skill', 'b2_skill_write_structured_texts', 'Write structured texts', 60),
        ('B2', 'functional_skill', 'b2_skill_participate_in_interviews', 'Participate IN interviews', 70),
        ('B2', 'functional_skill', 'b2_skill_understand_fast_native_speech', 'Understand fast native speech', 80),

        ('C1', 'grammar', 'c1_grammar_advanced_inversion', 'Advanced inversion', 10),
        ('C1', 'grammar', 'c1_grammar_ellipsis_substitution', 'Ellipsis & substitution', 20),
        ('C1', 'grammar', 'c1_grammar_advanced_cleft_sentences', 'Advanced cleft sentences', 30),
        ('C1', 'grammar', 'c1_grammar_nuanced_modal_meaning', 'Nuanced modal meaning', 40),
        ('C1', 'grammar', 'c1_grammar_advanced_discourse_structures', 'Advanced discourse structures', 50),
        ('C1', 'grammar', 'c1_grammar_formal_vs_informal_register', 'Formal vs informal register', 60),
        ('C1', 'grammar', 'c1_grammar_idiomatic_structures', 'Idiomatic structures', 70),
        ('C1', 'grammar', 'c1_grammar_advanced_conditionals', 'Advanced conditionals', 80),
        ('C1', 'grammar', 'c1_grammar_complex_participle_structures', 'Complex participle structures', 90),
        ('C1', 'grammar', 'c1_grammar_precision_articles_prepositions', 'Precision with articles/prepositions', 100),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_philosophy_ethics', 'Philosophy & ethics', 10),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_law_regulation', 'Law & regulation', 20),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_geopolitics', 'Geopolitics', 30),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_academic_english', 'Academic English', 40),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_advanced_business_strategy', 'Advanced business strategy', 50),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_research_analytics', 'Research & analytics', 60),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_advanced_psychology', 'Advanced psychology', 70),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_sociology', 'Sociology', 80),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_literature_rhetoric', 'Literature & rhetoric', 90),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_finance_investment', 'Finance & investment', 100),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_engineering_architecture', 'Engineering & architecture', 110),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_advanced_ai_ml_discussions', 'Advanced AI/ML discussions', 120),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_media_influence', 'Media influence', 130),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_abstract_thinking', 'Abstract thinking', 140),
        ('C1', 'vocabulary_theme', 'c1_vocabulary_cross_cultural_communication', 'Cross-cultural communication', 150),
        ('C1', 'functional_skill', 'c1_skill_speak_spontaneously_at_length', 'Speak spontaneously at length', 10),
        ('C1', 'functional_skill', 'c1_skill_argue_nuanced_positions', 'Argue nuanced positions', 20),
        ('C1', 'functional_skill', 'c1_skill_write_persuasive_professional_texts', 'Write persuasive/professional texts', 30),
        ('C1', 'functional_skill', 'c1_skill_understand_implicit_meaning', 'Understand implicit meaning', 40),
        ('C1', 'functional_skill', 'c1_skill_handle_complex_negotiations', 'Handle complex negotiations', 50),
        ('C1', 'functional_skill', 'c1_skill_read_academic_professional_materials', 'Read academic/professional materials', 60),
        ('C1', 'functional_skill', 'c1_skill_speak_naturally_professional_environments', 'Speak naturally IN professional environments', 70),
        ('C1', 'functional_skill', 'c1_skill_adapt_tone_register_dynamically', 'Adapt tone/register dynamically', 80)
)
INSERT INTO learning_syllabus_item (
    level_id,
    domain_id,
    code,
    title,
    normalized_title,
    sort_order,
    metadata_json
)
SELECT
    language_level.id,
    learning_syllabus_domain.id,
    seed.item_code,
    seed.title,
    lower(regexp_replace(seed.title, '\\s+', ' ', 'g')),
    seed.sort_order,
    jsonb_build_object('source', 'initial_cefr_syllabus_reference')
FROM seed
JOIN language_level ON language_level.title = seed.level_title
JOIN learning_syllabus_domain ON learning_syllabus_domain.code = seed.domain_code
ON CONFLICT (code) DO UPDATE
SET
    level_id = EXCLUDED.level_id,
    domain_id = EXCLUDED.domain_id,
    title = EXCLUDED.title,
    normalized_title = EXCLUDED.normalized_title,
    sort_order = EXCLUDED.sort_order,
    is_active = true,
    metadata_json = EXCLUDED.metadata_json,
    updated = NOW();

-- Grammar Topics Setup
INSERT INTO grammar_topics (
    code,
    title,
    level,
    min_level,
    description,
    is_active
)
SELECT
    learning_syllabus_item.code,
    learning_syllabus_item.title,
    language_level.title,
    language_level.title,
    NULL,
    learning_syllabus_item.is_active
FROM learning_syllabus_item
JOIN language_level ON language_level.id = learning_syllabus_item.level_id
JOIN learning_syllabus_domain ON learning_syllabus_domain.id = learning_syllabus_item.domain_id
WHERE learning_syllabus_domain.code = 'grammar'
ON CONFLICT (code) DO UPDATE
SET
    title = EXCLUDED.title,
    level = EXCLUDED.level,
    min_level = EXCLUDED.min_level,
    description = COALESCE(grammar_topics.description, EXCLUDED.description),
    is_active = EXCLUDED.is_active,
    updated = NOW();

-- TTS Voices Setup
INSERT INTO tts_voices (provider, code, display_name, language_code, gender, sort_order)
VALUES
    ('google_tts', 'en-US-Neural2-C', 'Google en-US Neural2 C', 'en-US', 'female', 10),
    ('google_tts', 'en-US-Neural2-E', 'Google en-US Neural2 E', 'en-US', 'female', 20),
    ('google_tts', 'en-US-Neural2-F', 'Google en-US Neural2 F', 'en-US', 'female', 30),
    ('google_tts', 'en-US-Neural2-G', 'Google en-US Neural2 G', 'en-US', 'female', 40),
    ('google_tts', 'en-US-Neural2-A', 'Google en-US Neural2 A', 'en-US', 'male', 50),
    ('google_tts', 'en-US-Neural2-D', 'Google en-US Neural2 D', 'en-US', 'male', 60),
    ('google_tts', 'en-US-Neural2-I', 'Google en-US Neural2 I', 'en-US', 'male', 70),
    ('google_tts', 'en-US-Neural2-J', 'Google en-US Neural2 J', 'en-US', 'male', 80)
ON CONFLICT (provider, code) DO UPDATE
SET
    display_name = EXCLUDED.display_name,
    language_code = EXCLUDED.language_code,
    gender = EXCLUDED.gender,
    is_active = true,
    sort_order = EXCLUDED.sort_order,
    updated = NOW();

-- ACL Setup
INSERT INTO acl (group_id, environment, action, rule, method)
SELECT acl_group.id, seed.environment, seed.action, seed.rule, 'ANY'
FROM acl_group
JOIN (
    VALUES
        ('admin', 'web_admin', 'exercise_texts/list', 'enabled'),
        ('admin', 'web_admin', 'exercise_texts/view', 'enabled'),
        ('admin', 'web_admin', 'exercise_texts/create', 'enabled'),
        ('admin', 'web_admin', 'exercise_texts/update', 'enabled'),
        ('admin', 'web_admin', 'exercise_texts/archive', 'enabled'),
        ('admin', 'web_admin', 'exercise_texts/publish', 'enabled'),
        ('admin', 'web_admin', 'exercise_texts/play_audio', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/list', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/view', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/create', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/update', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/archive', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/publish', 'enabled'),
        ('admin_editor', 'web_admin', 'exercise_texts/play_audio', 'enabled')
) AS seed(group_title, environment, action, rule)
    ON seed.group_title = acl_group.title
ON CONFLICT (group_id, environment, action) DO UPDATE
SET
    rule = EXCLUDED.rule,
    method = EXCLUDED.method,
    updated = NOW();
