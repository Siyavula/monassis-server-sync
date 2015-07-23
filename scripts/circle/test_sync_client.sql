DROP DATABASE IF EXISTS test_sync_client;

CREATE DATABASE test_sync_client WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'en_ZA.UTF-8' LC_CTYPE = 'en_ZA.UTF-8';

\connect test_sync_client

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

CREATE SCHEMA public;

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;

SET search_path = public, pg_catalog;
SET default_tablespace = '';
SET default_with_oids = false;

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

CREATE TABLE records (
    id integer NOT NULL,
    column1 character varying,
    column2 character varying,
    column3 character varying
);

CREATE SEQUENCE records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE records_id_seq OWNED BY records.id;

ALTER TABLE ONLY record_hashes ALTER COLUMN id SET DEFAULT nextval('record_hashes_id_seq'::regclass);
ALTER TABLE ONLY records ALTER COLUMN id SET DEFAULT nextval('records_id_seq'::regclass);
ALTER TABLE ONLY record_hashes ADD CONSTRAINT record_hashes_pkey PRIMARY KEY (id);
ALTER TABLE ONLY records ADD CONSTRAINT records_pkey PRIMARY KEY (id);

CREATE INDEX ix_record_hashes_section_name ON record_hashes USING btree (section_name);
CREATE INDEX ix_record_hashes_sync_name ON record_hashes USING btree (sync_name);
