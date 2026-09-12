CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT,
    administrator_role BIGINT,
    moderator_role BIGINT,
    admin_channel BIGINT,
    log_channel BIGINT,
    watchlist_alerts BOOLEAN NOT NULL DEFAULT FALSE,
);

CREATE TABLE IF NOT EXISTS nsv_settings (
    guild_id BIGINT NOT NULL DEFAULT 0,
    guest_role BIGINT NOT NULL DEFAULT 0,
    resident_role BIGINT NOT NULL DEFAULT 0,
    wa_resident_role BIGINT NOT NULL DEFAULT 0,
    verified_role BIGINT NOT NULL DEFAULT 0,
    region TEXT,
    welcome_message TEXT NOT NULL DEFAULT 'Welcome to the server!',
    PRIMARY KEY (guild_id)
);

CREATE TABLE IF NOT EXISTS nation_dump (
    nation VARCHAR(50) NOT NULL,
    region VARCHAR(1000) NOT NULL,
    unstatus VARCHAR(15) NOT NULL,
    endorsements TEXT,
    last_update TIMESTAMP NOT NULL,
    PRIMARY KEY (nation)
);

CREATE TABLE IF NOT EXISTS welcome_settings (
    guild_id BIGINT NOT NULL,
    welcome_channel BIGINT DEFAULT 0,
    welcome_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ping_on_join BOOLEAN NOT NULL DEFAULT FALSE,
    embed_message VARCHAR(500) DEFAULT 'Welcome to the server!',
    PRIMARY KEY (guild_id)
);
