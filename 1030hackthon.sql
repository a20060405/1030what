-- Adminer 6.1.0 PostgreSQL 17.6 dump

DROP TABLE IF EXISTS "public"."events", "public"."registrations";

CREATE TABLE "public"."events" (
    "id" serial NOT NULL,
    "title" character varying(255) NOT NULL,
    "description" text,
    "deadline" timestamp,
    CONSTRAINT "events_pkey" PRIMARY KEY ("id")
);


CREATE TABLE "public"."registrations" (
    "id" serial NOT NULL,
    "event_id" integer NOT NULL,
    "name" character varying(100) NOT NULL,
    "phone" character varying(50) NOT NULL,
    "created_at" timestamp DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "registrations_pkey" PRIMARY KEY ("id")
);


ALTER TABLE ONLY "public"."registrations" ADD CONSTRAINT "registrations_event_id_fkey" FOREIGN KEY (event_id) REFERENCES "public"."events"(id);

-- 2026-10-30 06:32:41 UTC
