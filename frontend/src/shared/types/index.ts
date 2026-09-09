/**
 * Core Domain Interfaces and Type Definitions for InvIQ Frontend.
 */

export type UserRole = 'admin' | 'manager' | 'staff' | 'vendor';

export interface User {
    id: number;
    email: string;
    username: string;
    full_name?: string;
    role: UserRole;
    org_id: number | null;
    location_ids?: number[];
    is_active: boolean;
    is_verified: boolean;
    created_at?: string;
}

export interface Organization {
    id: number;
    name: string;
    slug: string;
    plan: 'single_pharmacy' | 'multi_branch' | 'enterprise';
    is_active: boolean;
    contact_phone?: string;
    contact_email?: string;
    address?: string;
    gstin?: string;
    discount_policy?: {
        enabled: boolean;
        senior_citizen_pct: number;
        loyalty_member_pct: number;
        bulk_purchase_pct: number;
        bulk_threshold_amount: number;
    };
    created_at?: string;
}

export interface Location {
    id: number;
    org_id: number;
    name: string;
    type: 'retail_counter' | 'warehouse' | 'cold_storage';
    region: string;
    radius_meters?: number;
    pincode?: string;
    phone?: string;
    address?: string;
    created_at?: string;
}

export interface Item {
    id: number;
    name: string;
    category: string;
    unit: string;
    lead_time_days: number;
    min_stock: number;
    storage_temp: 'ambient' | 'cold_chain';
    barcode?: string;
    strength?: string;
    mrp?: number;
    purchase_rate?: number;
    org_id: number;
    created_at?: string;
}

export type RequisitionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
export type UrgencyLevel = 'LOW' | 'NORMAL' | 'HIGH' | 'EMERGENCY';

export interface RequisitionItem {
    id?: number;
    requisition_id?: number;
    item_id: number;
    item_name?: string;
    quantity: number;
    packaging_unit?: string;
    notes?: string;
}

export interface Requisition {
    id: number;
    org_id: number;
    location_id: number;
    location_name?: string;
    requested_by: string;
    department: string;
    urgency: UrgencyLevel;
    status: RequisitionStatus;
    notes?: string;
    created_at: string;
    reviewed_by?: string;
    reviewed_at?: string;
    rejection_reason?: string;
    items: RequisitionItem[];
}

export interface BillItem {
    item_id: number;
    name: string;
    batch_number: string;
    quantity: number;
    unit: string;
    multiplier: number;
    mrp: number;
    discount_pct: number;
    final_unit_price: number;
    total: number;
    expiry_date?: string;
}

export interface BillingSession {
    session_id: string;
    counter_id: number;
    operator_name: string;
    customer_phone?: string;
    customer_name?: string;
    customer_type?: 'REGULAR' | 'SENIOR' | 'LOYALTY';
    items: BillItem[];
    subtotal: number;
    total_discount: number;
    tax_amount: number;
    grand_total: number;
    status: 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
}

export interface ApiResponse<T = any> {
    success: boolean;
    data?: T;
    message?: string;
    error?: string;
    detail?: string;
    total?: number;
}
