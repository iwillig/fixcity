-- SQL to fix bug #59 on existing databases.

ALTER TABLE bmabr_rack ALTER COLUMN description TYPE varchar(300) USING substring(description from 0 for 300);

ALTER TABLE bmabr_comment ALTER COLUMN text TYPE varchar(300) USING substring(text from 0 for 300);
