/**
 * Role Constants & Hierarchy Definition.
 * Single source of truth across App routing and ProtectedRoute guards.
 */

export const ROLE_HIERARCHY = Object.freeze({
    vendor: 2,
    staff: 3,
    manager: 4,
    admin: 5,
});

/**
 * Maps authenticated roles to their respective default landing paths.
 * Single Chemist & Multi-Branch Admins both land on /admin/dashboard.
 */
export const ROLE_HOME = Object.freeze({
    admin: '/admin/dashboard',
    manager: '/admin/dashboard',
    staff: '/staff',
    vendor: '/vendor',
});

/**
 * Evaluates whether a given user role meets or exceeds a required role level.
 * @param {string} userRole
 * @param {string} requiredRole
 * @returns {boolean}
 */
export function hasRolePermission(userRole, requiredRole) {
    if (!requiredRole) return true;
    const userLevel = ROLE_HIERARCHY[userRole] ?? 0;
    const requiredLevel = ROLE_HIERARCHY[requiredRole] ?? 999;
    return userLevel >= requiredLevel;
}

/**
 * Returns the default home path for a given role, falling back to preview.
 * @param {string} [role]
 * @returns {string}
 */
export function getRoleHome(role) {
    if (!role) return '/preview';
    return ROLE_HOME[role] || '/admin/dashboard';
}
