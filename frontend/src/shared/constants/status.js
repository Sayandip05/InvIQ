/**
 * Status and Urgency Style Constants.
 * Centralized styling and options for Requisitions, Deliveries, and Ingestion.
 */

export const REQUISITION_STATUSES = Object.freeze({
    PENDING: 'PENDING',
    APPROVED: 'APPROVED',
    REJECTED: 'REJECTED',
    CANCELLED: 'CANCELLED',
});

export const STATUS_STYLES = Object.freeze({
    PENDING: 'bg-amber-500/10 text-amber-800 border border-amber-500/30 font-semibold',
    APPROVED: 'bg-emerald-500/10 text-emerald-800 border border-emerald-500/30 font-semibold',
    REJECTED: 'bg-destructive/10 text-destructive border border-destructive/30 font-semibold',
    CANCELLED: 'bg-accent/50 text-muted-foreground border border-border',
    COMPLETED: 'bg-emerald-500/10 text-emerald-800 border border-emerald-500/30 font-semibold',
    PARTIAL: 'bg-amber-500/10 text-amber-800 border border-amber-500/30 font-semibold',
    FAILED: 'bg-destructive/10 text-destructive border border-destructive/30 font-semibold',
});

export const URGENCY_LEVELS = Object.freeze({
    LOW: 'LOW',
    NORMAL: 'NORMAL',
    HIGH: 'HIGH',
    EMERGENCY: 'EMERGENCY',
});

export const URGENCY_OPTIONS = Object.freeze([
    'LOW',
    'NORMAL',
    'HIGH',
    'EMERGENCY',
]);

export const URGENCY_STYLES = Object.freeze({
    LOW: 'bg-accent/50 text-foreground border border-border font-medium',
    NORMAL: 'bg-primary text-primary-foreground border border-primary font-medium',
    HIGH: 'bg-amber-500/20 text-amber-900 border border-amber-500/40 font-bold',
    EMERGENCY: 'bg-[#F26A4B] text-white border border-[#F26A4B] font-bold animate-pulse',
});

export const DEPARTMENTS = Object.freeze([
    'Pharmacy Counter',
    'Emergency',
    'ICU',
    'Cardiology',
    'General Ward',
    'OT',
    'Pediatrics',
    'Oncology',
    'Lab',
]);
