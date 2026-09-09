/**
 * API Services Facade.
 *
 * All domain-specific API calls are modularized inside their respective features:
 * - Auth: '@/features/auth/api'
 * - Inventory: '@/features/inventory/api'
 * - Requisitions: '@/features/requisitions/api'
 * - Billing: '@/features/billing/api'
 * - Analytics: '@/features/analytics/api'
 * - Chat: '@/features/chat/api'
 * - Admin: '@/features/admin/api'
 *
 * This facade re-exports them for complete backward compatibility.
 */

import apiClient, { setAuthToken, getAuthToken } from '@/shared/services/apiClient';
import { authApi } from '@/features/auth/api';
import { inventoryApi } from '@/features/inventory/api';
import { requisitionApi } from '@/features/requisitions/api';
import { billingApi } from '@/features/billing/api';
import { analyticsApi } from '@/features/analytics/api';
import { chatApi } from '@/features/chat/api';
import { adminApi } from '@/features/admin/api';

export { setAuthToken, getAuthToken };
export const auth = authApi;
export const inventory = inventoryApi;
export const requisition = requisitionApi;
export const billing = billingApi;
export const analytics = analyticsApi;
export const chat = chatApi;
export const admin = adminApi;

export default apiClient;
