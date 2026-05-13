import React, { useState, useEffect } from 'react';
import { auth as authApi } from '../../services/api';
import { Users, Search, Plus, Edit2, Trash2, Shield, Building2, ChevronDown, X } from 'lucide-react';

const UserManagement = () => {
    const [users, setUsers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [showModal, setShowModal] = useState(false);
    const [editingUser, setEditingUser] = useState(null);
    const [formData, setFormData] = useState({ username: '', email: '', full_name: '', role: 'staff', password: '' });
    const [saving, setSaving] = useState(false);

    const loadUsers = async () => {
        try {
            const res = await authApi.list();
            if (res.data.success) {
                setUsers(res.data.data);
            }
        } catch (err) {
            console.error("Failed to load users", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadUsers(); }, []);

    const filteredUsers = users.filter(u =>
        u.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        u.full_name?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (editingUser) {
                await authApi.update(editingUser.id, formData);
            } else {
                await authApi.register(formData);
            }
            setShowModal(false);
            setEditingUser(null);
            setFormData({ username: '', email: '', full_name: '', role: 'staff', password: '' });
            loadUsers();
        } catch (err) {
            // Backend returns { error: { message: "..." } } — not FastAPI's default { detail: "..." }
            const msg =
                err.response?.data?.error?.message ||   // custom AppException / ValidationError shape
                err.response?.data?.detail ||           // fallback for any raw FastAPI 422
                'Operation failed. Please check your input and try again.';
            alert(msg);
        } finally {
            setSaving(false);
        }
    };

    const handleEdit = (user) => {
        setEditingUser(user);
        setFormData({ username: user.username, email: user.email || '', full_name: user.full_name || '', role: user.role, password: '' });
        setShowModal(true);
    };

    const handleDelete = async (id) => {
        if (!confirm('Are you sure you want to delete this user?')) return;
        try {
            await authApi.delete(id);
            loadUsers();
        } catch (err) {
            alert('Delete failed');
        }
    };

    const getRoleBadge = (role) => {
        const colors = {
            super_admin: 'bg-purple-100 text-purple-700',
            admin: 'bg-red-100 text-red-700',
            manager: 'bg-yellow-100 text-yellow-700',
            staff: 'bg-blue-100 text-blue-700',
            vendor: 'bg-green-100 text-green-700',
            viewer: 'bg-slate-100 text-slate-700',
        };
        return <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[role] || colors.viewer}`}>{role}</span>;
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900">User Management</h2>
                    <p className="text-slate-500">Manage system users and their roles</p>
                </div>
                <button
                    onClick={() => { setEditingUser(null); setFormData({ username: '', email: '', full_name: '', role: 'staff', password: '' }); setShowModal(true); }}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
                >
                    <Plus size={18} /> Add User
                </button>
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-slate-200">
                <div className="p-4 border-b border-slate-100">
                    <div className="relative max-w-md">
                        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={18} />
                        <input
                            type="text"
                            placeholder="Search users..."
                            className="w-full pl-10 pr-4 py-2 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 text-slate-600 font-medium text-sm">
                            <tr>
                                <th className="px-6 py-4">User</th>
                                <th className="px-6 py-4">Email</th>
                                <th className="px-6 py-4">Role</th>
                                <th className="px-6 py-4">Location</th>
                                <th className="px-6 py-4">Status</th>
                                <th className="px-6 py-4 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {loading ? (
                                <tr><td colSpan="6" className="text-center py-8 text-slate-400">Loading...</td></tr>
                            ) : filteredUsers.length === 0 ? (
                                <tr><td colSpan="6" className="text-center py-8 text-slate-400">No users found</td></tr>
                            ) : (
                                filteredUsers.map(user => (
                                    <tr key={user.id} className="hover:bg-slate-50 transition">
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-sm font-medium">
                                                    {user.username?.[0]?.toUpperCase()}
                                                </div>
                                                <div>
                                                    <p className="font-medium text-slate-800">{user.username}</p>
                                                    <p className="text-xs text-slate-500">{user.full_name || 'No name'}</p>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-slate-500 text-sm">{user.email || '-'}</td>
                                        <td className="px-6 py-4">{getRoleBadge(user.role)}</td>
                                        <td className="px-6 py-4 text-slate-500 text-sm">{user.location_ids?.length || 0} locations</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-0.5 rounded text-xs font-medium ${user.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                                {user.is_active ? 'Active' : 'Inactive'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                <button onClick={() => handleEdit(user)} className="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded transition">
                                                    <Edit2 size={16} />
                                                </button>
                                                <button onClick={() => handleDelete(user.id)} className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition">
                                                    <Trash2 size={16} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold">{editingUser ? 'Edit User' : 'Add New User'}</h3>
                            <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-slate-600">
                                <X size={20} />
                            </button>
                        </div>
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Username *</label>
                                <input type="text" required className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" value={formData.username} onChange={e => setFormData({ ...formData, username: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
                                <input type="email" className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" value={formData.email} onChange={e => setFormData({ ...formData, email: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                                <input type="text" className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" value={formData.full_name} onChange={e => setFormData({ ...formData, full_name: e.target.value })} />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Role *</label>
                                <select required className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none" value={formData.role} onChange={e => setFormData({ ...formData, role: e.target.value })}>
                                    <option value="viewer">Viewer</option>
                                    <option value="staff">Staff</option>
                                    <option value="vendor">Vendor</option>
                                    <option value="manager">Manager</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">{editingUser ? 'New Password (optional)' : 'Password *'}</label>
                                <input
                                    type="password"
                                    required={!editingUser}
                                    minLength={8}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                                    value={formData.password}
                                    onChange={e => setFormData({ ...formData, password: e.target.value })}
                                />
                                <p className="text-xs text-slate-400 mt-1">Minimum 8 characters</p>
                            </div>
                            <div className="flex justify-end gap-3 pt-2">
                                <button type="button" onClick={() => setShowModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition">Cancel</button>
                                <button type="submit" disabled={saving} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50">
                                    {saving ? 'Saving...' : (editingUser ? 'Update' : 'Create')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
};

export default UserManagement;