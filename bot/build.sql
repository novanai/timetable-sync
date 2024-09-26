CREATE TABLE IF NOT EXISTS default_courses (
    user_id BIGINT PRIMARY KEY,
    course_id TEXT
);

CREATE TABLE IF NOT EXISTS default_modules (
    user_id BIGINT,
    module_id TEXT
);
