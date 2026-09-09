/**
 * mockData.js — 100% self-contained frontend demo & preview dataset.
 *
 * Isolated inside shared/testing to prevent accidental production bundle inclusion.
 * Used exclusively by PreviewDashboard for unauthenticated sandbox walkthroughs.
 */

export const MOCK_STATS = {
    category_distribution: [
        { name: 'Antibiotics', value: 420 },
        { name: 'Vaccines (Cold-Chain)', value: 180 },
        { name: 'Pain Relief & Analgesics', value: 310 },
        { name: 'Cardiovascular', value: 240 },
        { name: 'Respiratory & Inhalers', value: 150 },
    ],
    status_distribution: [
        { name: 'HEALTHY', value: 960 },
        { name: 'WARNING', value: 45 },
        { name: 'CRITICAL', value: 12 },
    ],
    location_stock: [
        { name: 'Central Warehouse', total: 640 },
        { name: 'Pharmacy Wing A', total: 290 },
        { name: 'Cold-Storage Facility', total: 180 },
        { name: 'North Dispensary', total: 190 },
    ],
    low_stock_items: [
        { id: 1, name: 'Amoxicillin 500mg', category: 'Antibiotics', current_stock: 15, min_stock: 50, location: 'Pharmacy Wing A' },
        { id: 2, name: 'Covaxin Cold-Chain Vials', category: 'Vaccines', current_stock: 8, min_stock: 30, location: 'Cold-Storage Facility' },
        { id: 3, name: 'Paracetamol IV 100ml', category: 'Analgesics', current_stock: 22, min_stock: 60, location: 'Central Warehouse' },
        { id: 4, name: 'Azithromycin 250mg', category: 'Antibiotics', current_stock: 12, min_stock: 40, location: 'North Dispensary' },
    ],
};

export const MOCK_LOCATIONS = [
    { id: 1, name: 'Central Warehouse', type: 'warehouse', address: 'Plot 42, Industrial Zone, New Delhi', total_items: 640 },
    { id: 2, name: 'Pharmacy Wing A', type: 'pharmacy', address: 'Apollo Hospital Block B, Mumbai', total_items: 290 },
    { id: 3, name: 'Cold-Storage Facility', type: 'cold_chain', address: 'Terminal 3 Logistics Hub, Hyderabad', total_items: 180 },
    { id: 4, name: 'North Dispensary', type: 'clinic', address: 'Sector 14 Medical Enclave, Gurugram', total_items: 190 },
];

export const MOCK_ITEMS = [
    { id: 101, name: 'Amoxicillin 500mg Capsules', category: 'Antibiotics', batch_number: 'AMX-2026-08', expiry_date: '2027-04-15', current_stock: 15, min_stock: 50, unit: 'strips', storage_temp: 'ambient', status: 'CRITICAL', unit_price: 65.0 },
    { id: 102, name: 'Human Insulin Glargine 100IU', category: 'Cardiovascular', batch_number: 'INS-2026-11', expiry_date: '2026-12-30', current_stock: 8, min_stock: 30, unit: 'vials', storage_temp: 'cold_chain', status: 'CRITICAL', unit_price: 480.0 },
    { id: 103, name: 'Azithromycin 500mg Tablets', category: 'Antibiotics', batch_number: 'AZI-2026-04', expiry_date: '2027-08-20', current_stock: 140, min_stock: 40, unit: 'strips', storage_temp: 'ambient', status: 'HEALTHY', unit_price: 110.0 },
    { id: 104, name: 'Paracetamol IV 100ml Infusion', category: 'Pain Relief', batch_number: 'PCM-2026-02', expiry_date: '2027-01-10', current_stock: 22, min_stock: 60, unit: 'bottles', storage_temp: 'ambient', status: 'WARNING', unit_price: 35.0 },
    { id: 105, name: 'Hepatitis B Recombinant Vaccine', category: 'Vaccines', batch_number: 'HEPB-2026-09', expiry_date: '2026-10-15', current_stock: 45, min_stock: 25, unit: 'vials', storage_temp: 'cold_chain', status: 'HEALTHY', unit_price: 260.0 },
    { id: 106, name: 'Atorvastatin 20mg Tablets', category: 'Cardiovascular', batch_number: 'ATV-2026-05', expiry_date: '2027-11-28', current_stock: 310, min_stock: 80, unit: 'strips', storage_temp: 'ambient', status: 'HEALTHY', unit_price: 85.0 },
    { id: 107, name: 'Salbutamol Respiratory Inhaler', category: 'Respiratory', batch_number: 'SLB-2026-01', expiry_date: '2026-09-30', current_stock: 18, min_stock: 35, unit: 'inhalers', storage_temp: 'ambient', status: 'WARNING', unit_price: 140.0 },
    { id: 108, name: 'Metformin 500mg SR Tablets', category: 'Endocrine', batch_number: 'MET-2026-07', expiry_date: '2028-02-14', current_stock: 520, min_stock: 100, unit: 'strips', storage_temp: 'ambient', status: 'HEALTHY', unit_price: 25.0 },
];

export const MOCK_REQUISITIONS = [
    { id: 'REQ-2026-001', requested_by: 'Dr. Priya Sharma', role: 'Chief Pharmacist', destination: 'Pharmacy Wing A', items_count: 4, priority: 'HIGH', status: 'PENDING', created_at: '2026-08-08 09:30 AM', total_cost: 14500 },
    { id: 'REQ-2026-002', requested_by: 'Rajesh Verma', role: 'Logistics Manager', destination: 'Cold-Storage Facility', items_count: 2, priority: 'CRITICAL', status: 'APPROVED', created_at: '2026-08-08 11:15 AM', total_cost: 38400 },
    { id: 'REQ-2026-003', requested_by: 'Sunita Rao', role: 'Staff Nurse', destination: 'North Dispensary', items_count: 6, priority: 'MEDIUM', status: 'COMPLETED', created_at: '2026-08-07 04:45 PM', total_cost: 8200 },
    { id: 'REQ-2026-004', requested_by: 'Anand Kumar', role: 'Warehouse Supervisor', destination: 'Central Warehouse', items_count: 3, priority: 'LOW', status: 'PENDING', created_at: '2026-08-08 02:00 PM', total_cost: 5600 },
];

export const MOCK_CHAT_RESPONSES = [
    {
        trigger: 'stock',
        answer: 'Current Stock Summary across 4 locations:\n\n• **Amoxicillin 500mg**: 15 strips left at Pharmacy Wing A (Critical - below minimum 50)\n• **Human Insulin**: 8 vials remaining in Cold-Storage (Immediate replenishment recommended)\n• **Paracetamol IV**: 22 bottles in Central Warehouse\n\nWould you like me to initiate an emergency requisition for low-stock items?',
    },
    {
        trigger: 'cold',
        answer: 'Cold-Chain Biological Status:\n\n• **Insulin Glargine**: 8 vials, storage at 4°C (Normal range 2-8°C)\n• **Covaxin Vials**: 45 doses, temp variance 0.2°C over last 24 hours\n• **Hepatitis B**: 45 units stored safely\n\nAll IoT sensors report telemetry within compliant pharmaceutical safety thresholds.',
    },
    {
        trigger: 'requisition',
        answer: 'Recent Requisition Activities:\n\n1. **REQ-2026-001**: 4 items for Pharmacy Wing A (Pending approval)\n2. **REQ-2026-002**: Cold-Chain replenishment approved by Logistics Manager\n\nEstimated replenishment transit time: 24 to 48 hours via certified distributors.',
    },
];

export const MOCK_CHATBOT_REPLIES = MOCK_CHAT_RESPONSES;

