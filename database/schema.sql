-- Locations (Hospitals & Clinics)
CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL,
    region VARCHAR(100) NOT NULL,
    address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Medical Items (Medicines & Supplies)
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    lead_time_days INTEGER NOT NULL,
    min_stock INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Daily Inventory Transactions
CREATE TABLE IF NOT EXISTS inventory_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    date DATE NOT NULL,
    opening_stock INTEGER NOT NULL,
    received INTEGER NOT NULL DEFAULT 0,
    issued INTEGER NOT NULL DEFAULT 0,
    closing_stock INTEGER NOT NULL,
    notes TEXT,
    entered_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

-- Stock Health View (Calculated)
CREATE VIEW IF NOT EXISTS stock_health AS
SELECT 
    t.location_id,
    t.item_id,
    l.name as location_name,
    i.name as item_name,
    i.category,
    t.closing_stock as current_stock,
    AVG(t.issued) OVER (
        PARTITION BY t.location_id, t.item_id 
        ORDER BY t.date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as avg_daily_usage,
    CASE 
        WHEN AVG(t.issued) OVER (
            PARTITION BY t.location_id, t.item_id 
            ORDER BY t.date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) > 0 
        THEN t.closing_stock / AVG(t.issued) OVER (
            PARTITION BY t.location_id, t.item_id 
            ORDER BY t.date 
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        )
        ELSE 999
    END as days_remaining,
    CASE 
        WHEN (
            CASE 
                WHEN AVG(t.issued) OVER (
                    PARTITION BY t.location_id, t.item_id 
                    ORDER BY t.date 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) > 0 
                THEN t.closing_stock / AVG(t.issued) OVER (
                    PARTITION BY t.location_id, t.item_id 
                    ORDER BY t.date 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                )
                ELSE 999
            END
        ) < 3 THEN 'CRITICAL'
        WHEN (
            CASE 
                WHEN AVG(t.issued) OVER (
                    PARTITION BY t.location_id, t.item_id 
                    ORDER BY t.date 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                ) > 0 
                THEN t.closing_stock / AVG(t.issued) OVER (
                    PARTITION BY t.location_id, t.item_id 
                    ORDER BY t.date 
                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                )
                ELSE 999
            END
        ) BETWEEN 3 AND 7 THEN 'WARNING'
        ELSE 'HEALTHY'
    END as health_status,
    t.date as last_updated
FROM inventory_transactions t
JOIN locations l ON t.location_id = l.id
JOIN items i ON t.item_id = i.id;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_transactions_date ON inventory_transactions(date);
CREATE INDEX IF NOT EXISTS idx_transactions_location ON inventory_transactions(location_id);
CREATE INDEX IF NOT EXISTS idx_transactions_item ON inventory_transactions(item_id);

-- ─── Stock OUT Requisitions ───

CREATE TABLE IF NOT EXISTS requisitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_number VARCHAR(50) NOT NULL UNIQUE,
    location_id INTEGER NOT NULL,
    requested_by VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    urgency VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    approved_by VARCHAR(100),
    rejection_reason TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (location_id) REFERENCES locations(id)
);

CREATE TABLE IF NOT EXISTS requisition_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requisition_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    quantity_requested INTEGER NOT NULL,
    quantity_approved INTEGER,
    notes TEXT,
    FOREIGN KEY (requisition_id) REFERENCES requisitions(id),
    FOREIGN KEY (item_id) REFERENCES items(id)
);

CREATE INDEX IF NOT EXISTS idx_requisitions_status ON requisitions(status);
CREATE INDEX IF NOT EXISTS idx_requisitions_location ON requisitions(location_id);
CREATE INDEX IF NOT EXISTS idx_requisition_items_req ON requisition_items(requisition_id);
