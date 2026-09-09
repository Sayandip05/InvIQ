import { useState, useEffect, useCallback, useMemo } from 'react';
import { requisitionApi } from '@/features/requisitions/api';
import { useGuest } from '@/context/GuestContext';

export function useRequisitions() {
    const { isGuest, showAuthModal } = useGuest();
    const [requests, setRequests] = useState([]);
    const [stats, setStats] = useState(null);
    const [filter, setFilter] = useState('');
    const [expandedId, setExpandedId] = useState(null);
    const [approverName, setApproverName] = useState('');
    const [rejectReason, setRejectReason] = useState('');
    const [actionLoading, setActionLoading] = useState(null);
    const [showRejectModal, setShowRejectModal] = useState(null);
    const [loading, setLoading] = useState(false);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const [reqRes, statRes] = await Promise.all([
                requisitionApi.list(),
                requisitionApi.stats(),
            ]);
            if (reqRes.data.success) {
                setRequests(reqRes.data.data || []);
            }
            if (statRes.data.success) {
                setStats(statRes.data.data || null);
            }
        } catch (err) {
            console.error('Failed to load requisition data', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadData();
    }, [loadData]);

    const handleApprove = async (id) => {
        if (isGuest) {
            showAuthModal('Sign in to approve stock requisitions.');
            return;
        }
        setActionLoading(id);
        try {
            const res = await requisitionApi.approve(id, {
                approver_name: approverName || 'Store Admin',
            });
            if (res.data.success) {
                await loadData();
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Approval failed');
        } finally {
            setActionLoading(null);
        }
    };

    const handleReject = async (id) => {
        if (isGuest) {
            showAuthModal('Sign in to reject stock requisitions.');
            return;
        }
        setActionLoading(id);
        try {
            const res = await requisitionApi.reject(id, {
                approver_name: approverName || 'Store Admin',
                reason: rejectReason || 'Stock unavailable',
            });
            if (res.data.success) {
                setShowRejectModal(null);
                setRejectReason('');
                await loadData();
            }
        } catch (err) {
            alert(err.response?.data?.detail || 'Rejection failed');
        } finally {
            setActionLoading(null);
        }
    };

    const filteredRequests = useMemo(() => {
        if (!filter) return requests;
        return requests.filter((r) => r.status === filter);
    }, [requests, filter]);

    return {
        requests,
        filteredRequests,
        stats,
        filter,
        setFilter,
        expandedId,
        setExpandedId,
        approverName,
        setApproverName,
        rejectReason,
        setRejectReason,
        actionLoading,
        showRejectModal,
        setShowRejectModal,
        loading,
        loadData,
        handleApprove,
        handleReject,
        isGuest,
        showAuthModal,
    };
}

export default useRequisitions;
