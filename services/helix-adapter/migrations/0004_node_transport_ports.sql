ALTER TABLE helix.nodes
ADD COLUMN IF NOT EXISTS transport_port INTEGER
    CHECK (transport_port IS NULL OR (transport_port >= 1 AND transport_port <= 65535));

CREATE INDEX IF NOT EXISTS idx_helix_nodes_transport_port
    ON helix.nodes (transport_port)
    WHERE transport_port IS NOT NULL;
