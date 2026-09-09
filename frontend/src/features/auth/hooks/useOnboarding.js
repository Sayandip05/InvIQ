import { useState, useCallback } from 'react';
import { useAuth } from '@/context/AuthContext';
import { authApi } from '@/features/auth/api';
import { useNavigate } from 'react-router-dom';

export function useOnboarding({ externalIsOpen, externalOnClose } = {}) {
    const { user, updateUser } = useAuth();
    const navigate = useNavigate();
    const [step, setStep] = useState(1);

    // Derive or lazy-initialize open state without cascading renders
    const [internalOpen, setInternalOpen] = useState(() => {
        if (externalIsOpen !== undefined) return Boolean(externalIsOpen);
        if (typeof window === 'undefined' || !user) return false;
        const hasCompleted = localStorage.getItem(`inviq_onboarding_completed_${user.id || user.username}`);
        return !hasCompleted;
    });

    const isOpen = externalIsOpen !== undefined ? Boolean(externalIsOpen) : internalOpen;

    const [fullName, setFullName] = useState(() => user?.full_name || '');
    const [pharmacyName, setPharmacyName] = useState(
        () => user?.organization_name || (user ? `${user.full_name || user.username}'s Pharmacy & Medical Store` : '')
    );
    const [primaryCounter, setPrimaryCounter] = useState('Main Market Counter');
    const [planType, setPlanType] = useState('single_pharmacy');
    const [fefoAlertsEnabled, setFefoAlertsEnabled] = useState(true);
    const [error, setError] = useState('');
    const [saving, setSaving] = useState(false);

    const handleClose = useCallback(() => {
        setInternalOpen(false);
        if (user) {
            localStorage.setItem(`inviq_onboarding_completed_${user.id || user.username}`, 'true');
        }
        if (externalOnClose) externalOnClose();
    }, [user, externalOnClose]);

    const handleComplete = (targetRoute) => {
        handleClose();
        if (targetRoute) {
            navigate(targetRoute);
        }
    };

    const handleNext = async () => {
        setError('');
        if (step === 1) {
            if (!fullName.trim()) {
                setError('Your Full Name is required to personalize your workspace and AI assistant.');
                return;
            }
            if (!pharmacyName.trim()) {
                setError('Pharmacy / Store Name is required.');
                return;
            }

            setSaving(true);
            try {
                await authApi.updateProfile({ full_name: fullName.trim() });
                updateUser({ full_name: fullName.trim() });
            } catch (e) {
                console.warn('Failed to update full name during onboarding:', e);
            }

            if (user?.role === 'admin') {
                try {
                    await fetch('/api/admin/organization', {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'include',
                        body: JSON.stringify({
                            name: pharmacyName.trim(),
                            settings: {
                                fefo_alerts_enabled: fefoAlertsEnabled,
                                primary_counter_name: primaryCounter.trim() || 'Main Counter',
                                plan_type: planType,
                            },
                        }),
                    });
                } catch (e) {
                    console.warn('Failed to save profile during onboarding step 1:', e);
                }
            }
            setSaving(false);
        }

        if (step < 4) {
            setStep(s => s + 1);
        } else {
            handleComplete();
        }
    };

    const handleBack = () => {
        setError('');
        if (step > 1) {
            setStep(s => s - 1);
        }
    };

    return {
        step,
        setStep,
        isOpen,
        setInternalOpen,
        user,
        fullName,
        setFullName,
        pharmacyName,
        setPharmacyName,
        primaryCounter,
        setPrimaryCounter,
        planType,
        setPlanType,
        fefoAlertsEnabled,
        setFefoAlertsEnabled,
        error,
        setError,
        saving,
        handleNext,
        handleBack,
        handleClose,
        handleComplete,
        navigate,
    };
}

export default useOnboarding;
