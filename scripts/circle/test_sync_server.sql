--
-- PostgreSQL database dump
--

-- Dumped from database version 9.4.1
-- Dumped by pg_dump version 9.4.0
-- Started on 2015-05-01 01:12:23 SAST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

DROP DATABASE test_sync_server;
--
-- TOC entry 2278 (class 1262 OID 158453)
-- Name: test_sync_server; Type: DATABASE; Schema: -; Owner: sync_server
--

CREATE DATABASE test_sync_server WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'en_ZA.UTF-8' LC_CTYPE = 'en_ZA.UTF-8';


ALTER DATABASE test_sync_server OWNER TO sync_server;

\connect test_sync_server

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 5 (class 2615 OID 2200)
-- Name: public; Type: SCHEMA; Schema: -; Owner: ubuntu
--

CREATE SCHEMA public;


ALTER SCHEMA public OWNER TO ubuntu;

--
-- TOC entry 2279 (class 0 OID 0)
-- Dependencies: 5
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: ubuntu
--

COMMENT ON SCHEMA public IS 'standard public schema';


--
-- TOC entry 176 (class 3079 OID 12125)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner:
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2281 (class 0 OID 0)
-- Dependencies: 176
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner:
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 175 (class 1259 OID 158492)
-- Name: record_hashes; Type: TABLE; Schema: public; Owner: ubuntu; Tablespace:
--

CREATE TABLE record_hashes (
    id integer NOT NULL,
    sync_name character varying NOT NULL,
    section_name character varying NOT NULL,
    record_id character varying NOT NULL,
    record_hash character varying(32) NOT NULL
);


ALTER TABLE record_hashes OWNER TO ubuntu;

--
-- TOC entry 174 (class 1259 OID 158490)
-- Name: record_hashes_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE record_hashes_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE record_hashes_id_seq OWNER TO ubuntu;

--
-- TOC entry 2282 (class 0 OID 0)
-- Dependencies: 174
-- Name: record_hashes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE record_hashes_id_seq OWNED BY record_hashes.id;


--
-- TOC entry 173 (class 1259 OID 158481)
-- Name: records; Type: TABLE; Schema: public; Owner: ubuntu; Tablespace:
--

CREATE TABLE records (
    id integer NOT NULL,
    column1 character varying,
    column2 character varying,
    column3 character varying
);


ALTER TABLE records OWNER TO ubuntu;

--
-- TOC entry 172 (class 1259 OID 158479)
-- Name: records_id_seq; Type: SEQUENCE; Schema: public; Owner: ubuntu
--

CREATE SEQUENCE records_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE records_id_seq OWNER TO ubuntu;

--
-- TOC entry 2283 (class 0 OID 0)
-- Dependencies: 172
-- Name: records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: ubuntu
--

ALTER SEQUENCE records_id_seq OWNED BY records.id;


--
-- TOC entry 2158 (class 2604 OID 158495)
-- Name: id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY record_hashes ALTER COLUMN id SET DEFAULT nextval('record_hashes_id_seq'::regclass);


--
-- TOC entry 2157 (class 2604 OID 158484)
-- Name: id; Type: DEFAULT; Schema: public; Owner: ubuntu
--

ALTER TABLE ONLY records ALTER COLUMN id SET DEFAULT nextval('records_id_seq'::regclass);


--
-- TOC entry 2164 (class 2606 OID 158500)
-- Name: record_hashes_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu; Tablespace:
--

ALTER TABLE ONLY record_hashes
    ADD CONSTRAINT record_hashes_pkey PRIMARY KEY (id);


--
-- TOC entry 2160 (class 2606 OID 158489)
-- Name: records_pkey; Type: CONSTRAINT; Schema: public; Owner: ubuntu; Tablespace:
--

ALTER TABLE ONLY records
    ADD CONSTRAINT records_pkey PRIMARY KEY (id);


--
-- TOC entry 2161 (class 1259 OID 158502)
-- Name: ix_record_hashes_section_name; Type: INDEX; Schema: public; Owner: ubuntu; Tablespace:
--

CREATE INDEX ix_record_hashes_section_name ON record_hashes USING btree (section_name);


--
-- TOC entry 2162 (class 1259 OID 158501)
-- Name: ix_record_hashes_sync_name; Type: INDEX; Schema: public; Owner: ubuntu; Tablespace:
--

CREATE INDEX ix_record_hashes_sync_name ON record_hashes USING btree (sync_name);


--
-- TOC entry 2280 (class 0 OID 0)
-- Dependencies: 5
-- Name: public; Type: ACL; Schema: -; Owner: ubuntu
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2015-05-01 01:12:23 SAST

--
-- PostgreSQL database dump complete
--

