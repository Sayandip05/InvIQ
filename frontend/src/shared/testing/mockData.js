/**
 * mockData.js — 100% self-contained frontend demo & preview dataset.
 *
 * Isolated inside shared/testing to prevent accidental production bundle inclusion.
 * Used exclusively by PreviewDashboard for unauthenticated sandbox walkthroughs.
 */

export const MOCK_STATS = {
    category_distribution: [
        { name: 'Antibiotics', value: 420 },
        { name: 'Vaccines (Fridge)', value: 180 },
        { name: 'Pain Relief', value: 310 },
        { name: 'Heart Care', value: 240 },
        { name: 'Breathing Care', value: 150 },
    ],
    status_distribution: [
        { name: 'HEALTHY', value: 960 },
        { name: 'WARNING', value: 45 },
        { name: 'CRITICAL', value: 12 },
    ],
    location_stock: [
        { name: 'Central Warehouse', total: 640 },
        { name: 'Store Counter A', total: 290 },
        { name: 'Cold-Storage Facility', total: 180 },
        { name: 'North Branch', total: 190 },
    ],
    low_stock_items: [
        { id: 1, name: 'Amoxicillin 500mg', category: 'Antibiotics', current_stock: 15, min_stock: 50, location: 'Store Counter A' },
        { id: 2, name: 'Covaxin Vaccine Vials', category: 'Vaccines', current_stock: 8, min_stock: 30, location: 'Cold-Storage Facility' },
        { id: 3, name: 'Paracetamol 100ml Drip Bottle', category: 'Pain Relief', current_stock: 22, min_stock: 60, location: 'Central Warehouse' },
        { id: 4, name: 'Azithromycin 250mg', category: 'Antibiotics', current_stock: 12, min_stock: 40, location: 'North Branch' },
    ],
    expiry_timeline: [
        { month: 'Jan', expiring: 25, threshold: 18, risk_level: 'Low' },
        { month: 'Feb', expiring: 45, threshold: 32, risk_level: 'Medium' },
        { month: 'Mar', expiring: 38, threshold: 29, risk_level: 'Low' },
        { month: 'Apr', expiring: 65, threshold: 48, risk_level: 'High' },
        { month: 'May', expiring: 52, threshold: 41, risk_level: 'Medium' },
        { month: 'Jun', expiring: 85, threshold: 61, risk_level: 'Critical' },
    ],
};

export const MOCK_LOCATIONS = [
    { id: 1, name: 'Central Warehouse', type: 'warehouse', address: 'Plot 42, Industrial Zone, New Delhi', total_items: 640 },
    { id: 2, name: 'Store Counter A', type: 'pharmacy', address: 'Store Block B, Mumbai', total_items: 290 },
    { id: 3, name: 'Cold-Storage Facility', type: 'cold_chain', address: 'Terminal 3 Logistics Hub, Hyderabad', total_items: 180 },
    { id: 4, name: 'North Branch', type: 'clinic', address: 'Sector 14 Market, Gurugram', total_items: 190 },
];

export const MOCK_ITEMS = [
    { id: 101, name: 'Amoxicillin 500mg Capsules', category: 'Antibiotics', batch_number: 'AMX-2026-08', expiry_date: '2027-04-15', current_stock: 15, min_stock: 50, unit: 'strips', storage_temp: 'ambient', status: 'CRITICAL', unit_price: 65.0 },
    { id: 102, name: 'Human Insulin 100IU', category: 'Diabetes Care', batch_number: 'INS-2026-11', expiry_date: '2026-12-30', current_stock: 8, min_stock: 30, unit: 'vials', storage_temp: 'cold_chain', status: 'CRITICAL', unit_price: 480.0 },
    { id: 103, name: 'Azithromycin 500mg Tablets', category: 'Antibiotics', batch_number: 'AZI-2026-04', expiry_date: '2027-08-20', current_stock: 140, min_stock: 40, unit: 'strips', storage_temp: 'ambient', status: 'HEALTHY', unit_price: 110.0 },
    { id: 104, name: 'Paracetamol 100ml Drip Bottle', category: 'Pain Relief', batch_number: 'PCM-2026-02', expiry_date: '2027-01-10', current_stock: 22, min_stock: 60, unit: 'bottles', storage_temp: 'ambient', status: 'WARNING', unit_price: 35.0 },
    { id: 105, name: 'Hepatitis B Vaccine', category: 'Vaccines', batch_number: 'HEPB-2026-09', expiry_date: '2026-10-15', current_stock: 45, min_stock: 25, unit: 'vials', storage_temp: 'cold_chain', status: 'HEALTHY', unit_price: 260.0 },
    { id: 106, name: 'Atorvastatin 20mg Tablets', category: 'Heart Care', batch_number: 'ATV-2026-05', expiry_date: '2027-11-28', current_stock: 310, min_stock: 80, unit: 'strips', storage_temp: 'ambient', status: 'HEALTHY', unit_price: 85.0 },
    { id: 107, name: 'Salbutamol Inhaler', category: 'Breathing Care', batch_number: 'SLB-2026-01', expiry_date: '2026-09-30', current_stock: 18, min_stock: 35, unit: 'inhalers', storage_temp: 'ambient', status: 'WARNING', unit_price: 140.0 },
    { id: 108, name: 'Metformin 500mg SR Tablets', category: 'Diabetes Care', batch_number: 'MET-2026-07', expiry_date: '2028-02-14', current_stock: 520, min_stock: 100, unit: 'strips', storage_temp: 'ambient', status: 'HEALTHY', unit_price: 25.0 },
];

export const MOCK_REQUISITIONS = [
    { id: 'REQ-2026-001', requested_by: 'Dr. Priya Sharma', role: 'Store Pharmacist', destination: 'Store Counter A', items_count: 4, priority: 'HIGH', status: 'PENDING', created_at: '2026-08-08 09:30 AM', total_cost: 14500 },
    { id: 'REQ-2026-002', requested_by: 'Rajesh Verma', role: 'Logistics Manager', destination: 'Cold-Storage Facility', items_count: 2, priority: 'CRITICAL', status: 'APPROVED', created_at: '2026-08-08 11:15 AM', total_cost: 38400 },
    { id: 'REQ-2026-003', requested_by: 'Sunita Rao', role: 'Store Staff', destination: 'North Branch', items_count: 6, priority: 'MEDIUM', status: 'COMPLETED', created_at: '2026-08-07 04:45 PM', total_cost: 8200 },
    { id: 'REQ-2026-004', requested_by: 'Anand Kumar', role: 'Warehouse Supervisor', destination: 'Central Warehouse', items_count: 3, priority: 'LOW', status: 'PENDING', created_at: '2026-08-08 02:00 PM', total_cost: 5600 },
];

export const MOCK_CHAT_RESPONSES = [
    {
        trigger: 'stock',
        answer: 'Current Stock Summary across 4 locations:\n\n• **Amoxicillin 500mg**: 15 strips left at Store Counter A (Critical - below minimum 50)\n• **Human Insulin**: 8 vials remaining in Cold-Storage (Immediate replenishment recommended)\n• **Paracetamol**: 22 bottles in Central Warehouse\n\nWould you like me to initiate an emergency stock request for low-stock items?',
    },
    {
        trigger: 'cold',
        answer: 'Cold Storage Stock Status:\n\n• **Insulin**: 8 vials, storage at 4°C (Safe range 2-8°C)\n• **Covaxin Vaccine**: 45 doses, temperature steady over last 24 hours\n• **Hepatitis B**: 45 units stored safely\n\nAll sensors report stock stored within safe temperature limits.',
    },
    {
        trigger: 'requisition',
        answer: 'Recent Stock Requests:\n\n1. **REQ-2026-001**: 4 items for Store Counter A (Pending approval)\n2. **REQ-2026-002**: Cold-storage stock approved by Logistics Manager\n\nEstimated delivery time: 24 to 48 hours from suppliers.',
    },
];

export const MOCK_CHATBOT_REPLIES = MOCK_CHAT_RESPONSES;

