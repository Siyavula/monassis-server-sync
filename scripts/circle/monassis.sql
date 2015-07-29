CREATE TYPE "ClassUserRole" AS ENUM (
    'learner',
    'teacher',
    'monitor'
);

CREATE TYPE "ConceptType" AS ENUM (
    'concept',
    'fact',
    'special_case',
    'group',
    'misconception'
);

CREATE TYPE "Curriculum" AS ENUM (
    'NCS',
    'CAPS',
    'IEB'
);

CREATE TYPE "Province" AS ENUM (
    'Eastern Cape',
    'Free State',
    'Gauteng',
    'KwaZulu-Natal',
    'Limpopo',
    'Mpumalanga',
    'Northern Cape',
    'North West',
    'Western Cape'
);

CREATE TYPE "SchoolUserRole" AS ENUM (
    'student',
    'staff'
);

CREATE TYPE "SectionType" AS ENUM (
    'chapter',
    'section'
);

CREATE TYPE "TaskState" AS ENUM (
    'pending',
    'started',
    'succeeded',
    'failed'
);

CREATE TYPE "UserType" AS ENUM (
    'learner',
    'teacher'
);

CREATE TYPE "MessageSeverity" AS ENUM (
    'info',
    'warning',
    'critical'
);

SET default_tablespace = '';

SET default_with_oids = false;
CREATE TABLE activities (
    uuid uuid NOT NULL,
    assignment_uuid uuid,
    content text,
    user_uuid uuid NOT NULL,
    start_time timestamp without time zone NOT NULL,
    last_active timestamp without time zone NOT NULL
);

CREATE TABLE books (
    uuid uuid NOT NULL,
    subject character varying NOT NULL,
    grade integer NOT NULL,
    title character varying NOT NULL,
    curriculum "Curriculum" DEFAULT 'CAPS'::"Curriculum" NOT NULL
);

CREATE TABLE cache (
    name character varying,
    data bytea,
    expires timestamp without time zone
);

CREATE TABLE chapters (
    uuid uuid NOT NULL,
    book_uuid uuid NOT NULL,
    number integer NOT NULL,
    title character varying NOT NULL,
    path character varying,
    visible boolean,
    active boolean,
    shortcode character varying
);

CREATE TABLE classes (
    uuid uuid NOT NULL,
    school_uuid uuid NOT NULL,
    subject character varying NOT NULL,
    grade integer NOT NULL,
    name character varying NOT NULL
);

CREATE TABLE concept_dependencies (
    from_uuid uuid NOT NULL,
    to_uuid uuid NOT NULL
);

CREATE TABLE concept_group_hierarchy (
    parent_uuid uuid NOT NULL,
    child_uuid uuid NOT NULL
);

CREATE TABLE concepts (
    uuid uuid NOT NULL,
    type "ConceptType" DEFAULT 'concept'::"ConceptType" NOT NULL,
    label character varying,
    identifier character varying NOT NULL
);

CREATE TABLE curricula (
    uuid uuid NOT NULL,
    curriculum_name character varying NOT NULL,
    subject character varying NOT NULL,
    section_root_uuid uuid NOT NULL
);

CREATE TABLE message_types (
  id serial NOT NULL,
  name character varying,
  description character varying,
  CONSTRAINT message_types_pkey PRIMARY KEY (id)
);

CREATE TABLE messages (
  uuid uuid NOT NULL,
  created timestamp without time zone NOT NULL,
  deleted timestamp without time zone,
  type_id integer NOT NULL,
  to_user_uuid uuid NOT NULL,
  from_user_uuid uuid NOT NULL,
  notification_content character varying,
  action_description character varying,
  action_link character varying,
  message_content text,
  severity "MessageSeverity",
  subject character varying,
  notification_read_at timestamp without time zone,
  message_read_at timestamp without time zone,
  parent_message_uuid uuid,
  root_message_uuid uuid,
  CONSTRAINT messages_pkey PRIMARY KEY (uuid),
  CONSTRAINT messages_parent_message_uuid_fkey FOREIGN KEY (parent_message_uuid)
      REFERENCES messages (uuid) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT messages_root_message_uuid_fkey FOREIGN KEY (root_message_uuid)
      REFERENCES messages (uuid) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION,
  CONSTRAINT messages_type_id_fkey FOREIGN KEY (type_id)
      REFERENCES message_types (id) MATCH SIMPLE
      ON UPDATE NO ACTION ON DELETE NO ACTION
);

CREATE TABLE meta (
    version character varying
);

CREATE TABLE new_section_concept (
    section_uuid uuid NOT NULL,
    concept_uuid uuid NOT NULL
);

CREATE TABLE new_section_hierarchy (
    parent_uuid uuid NOT NULL,
    child_uuid uuid NOT NULL
);

CREATE TABLE new_sections (
    uuid uuid NOT NULL,
    number integer NOT NULL,
    title character varying NOT NULL,
    visible boolean,
    shortcode character varying
);

CREATE TABLE projects (
    uuid uuid NOT NULL,
    name character varying,
    school_ids uuid[]
);

CREATE TABLE record_hashes (
    id integer NOT NULL,
    sync_name character varying NOT NULL,
    section_name character varying NOT NULL,
    record_id character varying NOT NULL,
    record_hash character varying(32) NOT NULL
);

CREATE SEQUENCE record_hashes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE record_hashes_id_seq OWNED BY record_hashes.id;

CREATE TABLE responses (
    uuid uuid NOT NULL,
    user_uuid uuid NOT NULL,
    template_uuid uuid NOT NULL,
    random_seed integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    responses text,
    correct text,
    marks text,
    durations text,
    activity_uuid uuid
);

CREATE TABLE schools (
    uuid uuid NOT NULL,
    name character varying NOT NULL,
    code character varying NOT NULL,
    curriculum "Curriculum",
    government_school boolean,
    province "Province"
);

CREATE TABLE sections (
    uuid uuid NOT NULL,
    chapter_uuid uuid NOT NULL,
    number integer NOT NULL,
    title character varying NOT NULL,
    visible boolean,
    shortcode character varying
);

CREATE TABLE sessions (
    session_id integer NOT NULL,
    user_uuid uuid NOT NULL,
    book_uuid uuid,
    session_start timestamp without time zone NOT NULL,
    last_active timestamp without time zone,
    last_action character varying,
    activity_uuid uuid,
    dashboard_section_uuid uuid
);

CREATE SEQUENCE sessions_session_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE sessions_session_id_seq OWNED BY sessions.session_id;

CREATE TABLE shortcodes (
    uuid uuid NOT NULL,
    shortcode character varying NOT NULL,
    section_type "SectionType" NOT NULL,
    section_uuid uuid NOT NULL
);

CREATE TABLE tasks (
    id integer NOT NULL,
    method text,
    args text,
    kwargs text,
    recur_after integer,
    scheduled timestamp without time zone,
    started timestamp without time zone,
    finished timestamp without time zone,
    state "TaskState",
    result text
);

CREATE SEQUENCE tasks_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE tasks_id_seq OWNED BY tasks.id;

CREATE TABLE template_new_section (
    template_uuid uuid NOT NULL,
    section_uuid uuid NOT NULL
);

CREATE TABLE template_section (
    template_uuid uuid NOT NULL,
    section_type "SectionType" DEFAULT 'section'::"SectionType" NOT NULL,
    section_uuid uuid NOT NULL
);

CREATE TABLE templates (
    uuid uuid NOT NULL,
    zipdata bytea NOT NULL,
    muesli double precision
);

CREATE TABLE user_class (
    user_uuid uuid NOT NULL,
    class_uuid uuid NOT NULL,
    role "ClassUserRole" NOT NULL
);

CREATE TABLE user_school (
    user_uuid uuid NOT NULL,
    school_uuid uuid NOT NULL,
    role "SchoolUserRole" NOT NULL
);

CREATE TABLE vouchers (
    id integer NOT NULL,
    code character varying NOT NULL,
    class_uuid uuid,
    issue_count integer NOT NULL,
    issue_used integer DEFAULT 0 NOT NULL,
    expiry_maths character varying,
    expiry_science character varying,
    issue_timestamp timestamp without time zone DEFAULT now() NOT NULL,
    redeemable boolean DEFAULT true NOT NULL,
    cancelled boolean DEFAULT false NOT NULL
);

CREATE SEQUENCE vouchers_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- SEQUENCES
ALTER SEQUENCE vouchers_id_seq OWNED BY vouchers.id;

ALTER TABLE ONLY record_hashes ALTER COLUMN id SET DEFAULT nextval('record_hashes_id_seq'::regclass);
ALTER TABLE ONLY sessions ALTER COLUMN session_id SET DEFAULT nextval('sessions_session_id_seq'::regclass);
ALTER TABLE ONLY tasks ALTER COLUMN id SET DEFAULT nextval('tasks_id_seq'::regclass);
ALTER TABLE ONLY vouchers ALTER COLUMN id SET DEFAULT nextval('vouchers_id_seq'::regclass);

-- PRIMARY KEYS AND UNIQUE CONSTRAINTS
ALTER TABLE ONLY activities ADD CONSTRAINT activities_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY books ADD CONSTRAINT books_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY cache ADD CONSTRAINT cache_name_key UNIQUE (name);
ALTER TABLE ONLY chapters ADD CONSTRAINT chapters_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY classes ADD CONSTRAINT classes_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY concepts ADD CONSTRAINT concepts_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY curricula ADD CONSTRAINT curricula_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY new_sections ADD CONSTRAINT new_sections_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY projects ADD CONSTRAINT projects_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY record_hashes ADD CONSTRAINT record_hashes_pkey PRIMARY KEY (id);
ALTER TABLE ONLY responses ADD CONSTRAINT responses_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY schools ADD CONSTRAINT schools_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY sections ADD CONSTRAINT sections_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY sessions ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id);
ALTER TABLE ONLY shortcodes ADD CONSTRAINT shortcodes_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY shortcodes ADD CONSTRAINT shortcodes_shortcode_key UNIQUE (shortcode);
ALTER TABLE ONLY tasks ADD CONSTRAINT tasks_pkey PRIMARY KEY (id);
ALTER TABLE ONLY templates ADD CONSTRAINT templates_pkey PRIMARY KEY (uuid);
ALTER TABLE ONLY user_class ADD CONSTRAINT uix_user_class_user_uuid_class_uuid_role UNIQUE (user_uuid, class_uuid, role);
ALTER TABLE ONLY user_school ADD CONSTRAINT uix_user_school_user_uuid_school_uuid_role UNIQUE (user_uuid, school_uuid, role);
ALTER TABLE ONLY vouchers ADD CONSTRAINT vouchers_pkey PRIMARY KEY (id);

-- INDEXES
CREATE INDEX ix_activities_assignment_uuid ON activities USING btree (assignment_uuid);
CREATE INDEX ix_activities_user_uuid ON activities USING btree (user_uuid);
CREATE INDEX ix_classes_school_uuid ON classes USING btree (school_uuid);
CREATE INDEX ix_concept_dependencies_from_uuid ON concept_dependencies USING btree (from_uuid);
CREATE INDEX ix_concept_dependencies_to_uuid ON concept_dependencies USING btree (to_uuid);
CREATE INDEX ix_concept_group_hierarchy_child_uuid ON concept_group_hierarchy USING btree (child_uuid);
CREATE INDEX ix_concept_group_hierarchy_parent_uuid ON concept_group_hierarchy USING btree (parent_uuid);
CREATE INDEX ix_new_section_concept_concept_uuid ON new_section_concept USING btree (concept_uuid);
CREATE INDEX ix_new_section_concept_section_uuid ON new_section_concept USING btree (section_uuid);
CREATE UNIQUE INDEX ix_new_section_hierarchy_child_uuid ON new_section_hierarchy USING btree (child_uuid);
CREATE INDEX ix_new_section_hierarchy_parent_uuid ON new_section_hierarchy USING btree (parent_uuid);
CREATE INDEX ix_record_hashes_section_name ON record_hashes USING btree (section_name);
CREATE INDEX ix_record_hashes_sync_name ON record_hashes USING btree (sync_name);
CREATE INDEX ix_responses_template_uuid ON responses USING btree (template_uuid);
CREATE INDEX ix_responses_timestamp ON responses USING btree ("timestamp");
CREATE INDEX ix_responses_user_uuid ON responses USING btree (user_uuid);
CREATE INDEX ix_template_new_section_section_uuid ON template_new_section USING btree (section_uuid);
CREATE INDEX ix_template_new_section_template_uuid ON template_new_section USING btree (template_uuid);
CREATE INDEX ix_template_section_section_uuid ON template_section USING btree (section_uuid);
CREATE INDEX ix_template_section_template_uuid ON template_section USING btree (template_uuid);
CREATE INDEX ix_user_class_class_uuid ON user_class USING btree (class_uuid);
CREATE INDEX ix_user_class_user_uuid ON user_class USING btree (user_uuid);
CREATE INDEX ix_user_school_school_uuid ON user_school USING btree (school_uuid);
CREATE INDEX ix_vouchers_code ON vouchers USING btree (code);
CREATE INDEX record_hashes_record_id_idx ON record_hashes USING btree (record_id);
CREATE INDEX responses_activity_uuid_idx ON responses USING btree (activity_uuid);
CREATE INDEX sessions_user_uuid_book_uuid_key ON sessions USING btree (user_uuid, book_uuid);

-- REFERENCES
ALTER TABLE ONLY chapters ADD CONSTRAINT chapters_book_uuid_fkey FOREIGN KEY (book_uuid) REFERENCES books(uuid);
ALTER TABLE ONLY classes ADD CONSTRAINT classes_school_uuid_fkey FOREIGN KEY (school_uuid) REFERENCES schools(uuid);
ALTER TABLE ONLY concept_dependencies ADD CONSTRAINT concept_dependencies_from_uuid_fkey FOREIGN KEY (from_uuid) REFERENCES concepts(uuid);
ALTER TABLE ONLY concept_dependencies ADD CONSTRAINT concept_dependencies_to_uuid_fkey FOREIGN KEY (to_uuid) REFERENCES concepts(uuid);
ALTER TABLE ONLY concept_group_hierarchy ADD CONSTRAINT concept_group_hierarchy_child_uuid_fkey FOREIGN KEY (child_uuid) REFERENCES concepts(uuid);
ALTER TABLE ONLY concept_group_hierarchy ADD CONSTRAINT concept_group_hierarchy_parent_uuid_fkey FOREIGN KEY (parent_uuid) REFERENCES concepts(uuid);
ALTER TABLE ONLY curricula ADD CONSTRAINT curricula_section_root_uuid_fkey FOREIGN KEY (section_root_uuid) REFERENCES new_sections(uuid);
ALTER TABLE ONLY new_section_concept ADD CONSTRAINT new_section_concept_concept_uuid_fkey FOREIGN KEY (concept_uuid) REFERENCES concepts(uuid);
ALTER TABLE ONLY new_section_concept ADD CONSTRAINT new_section_concept_section_uuid_fkey FOREIGN KEY (section_uuid) REFERENCES new_sections(uuid);
ALTER TABLE ONLY new_section_hierarchy ADD CONSTRAINT new_section_hierarchy_child_uuid_fkey FOREIGN KEY (child_uuid) REFERENCES new_sections(uuid);
ALTER TABLE ONLY new_section_hierarchy ADD CONSTRAINT new_section_hierarchy_parent_uuid_fkey FOREIGN KEY (parent_uuid) REFERENCES new_sections(uuid);
ALTER TABLE ONLY responses ADD CONSTRAINT responses_activity_uuid_fkey FOREIGN KEY (activity_uuid) REFERENCES activities(uuid) ON DELETE SET NULL;
ALTER TABLE ONLY sections ADD CONSTRAINT sections_chapter_uuid_fkey FOREIGN KEY (chapter_uuid) REFERENCES chapters(uuid);
ALTER TABLE ONLY sessions ADD CONSTRAINT sessions_activity_uuid_fkey FOREIGN KEY (activity_uuid) REFERENCES activities(uuid) ON DELETE CASCADE;
ALTER TABLE ONLY sessions ADD CONSTRAINT sessions_book_uuid_fkey FOREIGN KEY (book_uuid) REFERENCES books(uuid);
ALTER TABLE ONLY sessions ADD CONSTRAINT sessions_dashboard_section_uuid_fkey FOREIGN KEY (dashboard_section_uuid) REFERENCES new_sections(uuid);
ALTER TABLE ONLY template_new_section ADD CONSTRAINT template_new_section_section_uuid_fkey FOREIGN KEY (section_uuid) REFERENCES new_sections(uuid);
ALTER TABLE ONLY template_new_section ADD CONSTRAINT template_new_section_template_uuid_fkey FOREIGN KEY (template_uuid) REFERENCES templates(uuid);
ALTER TABLE ONLY template_section ADD CONSTRAINT template_section_template_uuid_fkey FOREIGN KEY (template_uuid) REFERENCES templates(uuid);
ALTER TABLE ONLY user_class ADD CONSTRAINT user_class_class_uuid_fkey FOREIGN KEY (class_uuid) REFERENCES classes(uuid);
ALTER TABLE ONLY user_school ADD CONSTRAINT user_school_school_uuid_fkey FOREIGN KEY (school_uuid) REFERENCES schools(uuid);
ALTER TABLE ONLY vouchers ADD CONSTRAINT vouchers_class_uuid_fkey FOREIGN KEY (class_uuid) REFERENCES classes(uuid);

-- SEEDS
INSERT INTO message_types(name, description) VALUES ('error_report', 'Error Report'), ('assignment', 'Assignment');
