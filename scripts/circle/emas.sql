CREATE TABLE memberservices (
    memberservice_id integer NOT NULL,
    memberid character varying(100) NOT NULL,
    title character varying(100) NOT NULL,
    related_service_id integer NOT NULL,
    expiry_date date,
    credits integer,
    service_type character varying(100),
    zope_uid integer
);

CREATE SEQUENCE memberservices_memberservice_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE memberservices_memberservice_id_seq OWNED BY memberservices.memberservice_id;

CREATE TABLE otp_table (
    id integer NOT NULL,
    identifier text,
    otp text,
    secret text,
    "timestamp" timestamp without time zone
);


CREATE SEQUENCE otp_table_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE otp_table_id_seq OWNED BY otp_table.id;

CREATE TABLE user_identifiers (
    internal_user_id integer NOT NULL,
    field_name character varying NOT NULL,
    field_value character varying NOT NULL
);


CREATE TABLE user_profile (
    uuid text NOT NULL,
    user_profile character varying
);


CREATE TABLE user_profile_general (
    uuid text NOT NULL,
    name text,
    surname text,
    username text,
    email text,
    telephone text
);


CREATE TABLE users (
    internal_user_id integer NOT NULL,
    user_id uuid NOT NULL,
    password_method character varying NOT NULL,
    password_salt character varying,
    password_hash character varying NOT NULL,
    last_login timestamp with time zone,
    password_reset_token character varying,
    password_reset_expiry timestamp with time zone,
    role_id integer NOT NULL
);


CREATE SEQUENCE users_internal_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


-- SEQUENCES
ALTER SEQUENCE users_internal_user_id_seq OWNED BY users.internal_user_id;
ALTER TABLE ONLY memberservices ALTER COLUMN memberservice_id SET DEFAULT nextval('memberservices_memberservice_id_seq'::regclass);
ALTER TABLE ONLY otp_table ALTER COLUMN id SET DEFAULT nextval('otp_table_id_seq'::regclass);
ALTER TABLE ONLY users ALTER COLUMN internal_user_id SET DEFAULT nextval('users_internal_user_id_seq'::regclass);

-- PRIMARY KEYS AND UNIQUE CONSTRAINTS
ALTER TABLE ONLY memberservices ADD CONSTRAINT memberservices_pkey PRIMARY KEY (memberservice_id);
ALTER TABLE ONLY memberservices ADD CONSTRAINT memberservices_zope_uid_key UNIQUE (zope_uid);
ALTER TABLE ONLY otp_table ADD CONSTRAINT otp_table_pkey PRIMARY KEY (id);
ALTER TABLE ONLY user_identifiers ADD CONSTRAINT user_identifiers_pkey PRIMARY KEY (field_value);
ALTER TABLE ONLY user_profile_general ADD CONSTRAINT user_profile_general_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY user_profile ADD CONSTRAINT user_profile_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY users ADD CONSTRAINT users_pkey PRIMARY KEY (internal_user_id);

-- INDEXES
CREATE UNIQUE INDEX email_unique ON user_profile_general USING btree (lower(email));
CREATE INDEX idx_memberservice_id ON memberservices USING btree (memberservice_id);
CREATE INDEX idx_memeberid ON memberservices USING btree (memberid);
CREATE INDEX idx_related_service_id ON memberservices USING btree (related_service_id);
CREATE INDEX ix_user_identifiers_internal_user_id ON user_identifiers USING btree (internal_user_id);
CREATE UNIQUE INDEX ix_user_profile_general_email ON user_profile_general USING btree (email);
CREATE INDEX ix_user_profile_general_name ON user_profile_general USING btree (name);
CREATE INDEX ix_user_profile_general_surname ON user_profile_general USING btree (surname);
CREATE UNIQUE INDEX ix_user_profile_general_telephone ON user_profile_general USING btree (telephone);
CREATE UNIQUE INDEX ix_user_profile_general_username ON user_profile_general USING btree (username);
CREATE UNIQUE INDEX ix_users_user_id ON users USING btree (user_id);
CREATE UNIQUE INDEX username_unique ON user_profile_general USING btree (lower(username));

-- REFERENCES
ALTER TABLE ONLY user_identifiers ADD CONSTRAINT user_identifiers_internal_user_id_fkey FOREIGN KEY (internal_user_id) REFERENCES users(internal_user_id) ON DELETE CASCADE;
