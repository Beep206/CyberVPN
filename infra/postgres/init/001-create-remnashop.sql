DO
$$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'remnashop') THEN
        CREATE DATABASE remnashop;
    END IF;
END
$$;
