import React, { useState, useEffect } from 'react';
import {
    Sparkles,
    CheckCircle2,
    ArrowRight,
    ArrowLeft,
    Building2,
    Bot,
    Boxes,
    FileText,
    TrendingUp,
    Shield,
    Users,
    UploadCloud,
    Check,
    X,
    ThermometerSnowflake,
    Truck,
    Clock,
    User,
    AlertCircle,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { auth } from '../../services/api';

export default function OnboardingWizard({ isOpen: externalIsOpen, onClose: externalOnClose }) {
    const { user, updateUser } = useAuth();
    const navigate = useNavigate();
    const [step, setStep] = useState(1);
    const [isOpen, setIsOpen] = useState(false);

    // Form states for step 1
    const [fullName, setFullName] = useState('');
    const [pharmacyName, setPharmacyName] = useState('');
    const [primaryCounter, setPrimaryCounter] = useState('Main Market Counter');
    const [planType, setPlanType] = useState('single_pharmacy');
    const [fefoAlertsEnabled, setFefoAlertsEnabled] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        if (externalIsOpen !== undefined) {
            setIsOpen(externalIsOpen);
            return;
        }

        // Automatic trigger for new users who have not completed onboarding
        if (user) {
            setFullName(user.full_name || '');
            setPharmacyName(user.organization_name || `${user.full_name || user.username}'s Pharmacy & Medical Store`);
            const hasCompleted = localStorage.getItem(`inviq_onboarding_completed_${user.id || user.username}`);
            if (!hasCompleted) {
                setIsOpen(true);
            }
        }
    }, [user, externalIsOpen]);

    if (!isOpen || !user) {
        return null;
    }

    const handleClose = () => {
        setIsOpen(false);
        localStorage.setItem(`inviq_onboarding_completed_${user.id || user.username}`, 'true');
        if (externalOnClose) externalOnClose();
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

            // Save user full name & organization profile
            try {
                await auth.updateProfile({ full_name: fullName.trim() });
                updateUser({ full_name: fullName.trim() });
            } catch (e) {
                console.warn('Failed to update full name during onboarding:', e);
            }

            if (user.role === 'admin') {
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
        }

        if (step < 4) {
            setStep(step + 1);
        } else {
            handleComplete();
        }
    };

    const handleBack = () => {
        setError('');
        if (step > 1) {
            setStep(step - 1);
        }
    };

    const handleComplete = (targetRoute) => {
        handleClose();
        if (targetRoute) {
            navigate(targetRoute);
        }
    };

    const userRole = user.role || 'admin';
    const roleTitle = userRole.charAt(0).toUpperCase() + userRole.slice(1);
    const greetingName = fullName.trim() || user.full_name || user.username;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
            <div className="bg-card border border-border rounded-none shadow-2xl max-w-2xl w-full overflow-hidden flex flex-col max-h-[90vh]">
                
                {/* ── Modal Header ───────────────────────── */}
                <div className="p-5 border-b border-border flex items-center justify-between bg-accent/30">
                    <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-none bg-primary border border-primary flex items-center justify-center text-[#F26A4B] font-bold">
                            <Sparkles size={18} />
                        </div>
                        <div>
                            <h2 className="text-sm font-sans font-bold text-foreground tracking-tight">
                                InvIQ Chemist Setup &amp; Onboarding Guide
                            </h2>
                            <p className="text-xs text-muted-foreground">
                                Step {step} of 4 • Setting up your {roleTitle} workspace
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        {/* Step progress indicators */}
                        <div className="flex items-center gap-1.5 mr-2">
                            {[1, 2, 3, 4].map((i) => (
                                <div
                                    key={i}
                                    className={`h-1.5 rounded-none transition-all duration-200 ${
                                        i === step
                                            ? 'w-6 bg-primary'
                                            : i < step
                                            ? 'w-2 bg-[#5E5A52]'
                                            : 'w-2 bg-border'
                                    }`}
                                />
                            ))}
                        </div>

                        <button
                            onClick={handleClose}
                            className="text-muted-foreground hover:text-foreground p-1 rounded-none hover:bg-accent transition-colors cursor-pointer"
                            aria-label="Close onboarding modal"
                        >
                            <X size={18} />
                        </button>
                    </div>
                </div>

                {/* ── Modal Body ─────────────────────────── */}
                <div className="p-6 md:p-8 overflow-y-auto flex-1 space-y-5 bg-card">
                    
                    {error && (
                        <div className="p-3 bg-destructive/10 border border-destructive/30 text-destructive text-xs flex items-center gap-2 rounded-none">
                            <AlertCircle size={15} className="shrink-0 text-destructive" />
                            <span>{error}</span>
                        </div>
                    )}

                    {/* STEP 1: Admin Profile & Pharmacy Store Setup */}
                    {step === 1 && (
                        <div className="space-y-5 animate-in fade-in duration-200">
                            <div>
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-none text-xs font-semibold bg-accent text-foreground border border-border mb-2">
                                    👋 Chemist Administrator Profile
                                </span>
                                <h3 className="text-xl font-sans font-bold text-foreground tracking-tight">
                                    Welcome to InvIQ, {greetingName}!
                                </h3>
                                <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                                    Please verify your full name and store details. This personalizes your dashboard and your InvIQ AI Assistant.
                                </p>
                            </div>

                            <div className="bg-accent/20 border border-border rounded-none p-5 space-y-4">
                                
                                {/* Mandatory Full Name Input */}
                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                                        Your Full Name <span className="text-destructive">* (Mandatory)</span>
                                    </label>
                                    <div className="relative">
                                        <User className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
                                        <input
                                            type="text"
                                            required
                                            value={fullName}
                                            onChange={(e) => setFullName(e.target.value)}
                                            placeholder="e.g. Rahul Saha"
                                            className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary transition-all text-foreground font-medium"
                                        />
                                    </div>
                                    <p className="text-[11px] text-muted-foreground mt-1">Your personal name displayed in reports, audits, and chat.</p>
                                </div>

                                {/* Pharmacy Name */}
                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                                        Medical Store / Pharmacy Name <span className="text-destructive">*</span>
                                    </label>
                                    <div className="relative">
                                        <Building2 className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
                                        <input
                                            type="text"
                                            required
                                            value={pharmacyName}
                                            onChange={(e) => setPharmacyName(e.target.value)}
                                            placeholder="e.g. Sharma Medicos & Chemist"
                                            className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary transition-all text-foreground"
                                        />
                                    </div>
                                </div>

                                {/* Primary Counter */}
                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                                        Primary Counter / Shop Branch
                                    </label>
                                    <div className="relative">
                                        <Boxes className="absolute left-3 top-2.5 text-muted-foreground" size={16} />
                                        <input
                                            type="text"
                                            value={primaryCounter}
                                            onChange={(e) => setPrimaryCounter(e.target.value)}
                                            placeholder="e.g. Main Shop Counter"
                                            className="w-full pl-9 pr-3 py-2 text-sm bg-background border border-border rounded-none focus:outline-none focus:border-primary transition-all text-foreground"
                                        />
                                    </div>
                                </div>

                                {/* Operating Tier */}
                                <div>
                                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                                        Operating Tier
                                    </label>
                                    <div className="grid grid-cols-2 gap-3">
                                        <button
                                            type="button"
                                            onClick={() => setPlanType('single_pharmacy')}
                                            className={`p-3 rounded-none border text-left transition-all cursor-pointer ${
                                                planType === 'single_pharmacy'
                                                    ? 'border-primary bg-card border-l-4 border-l-primary font-semibold shadow-2xs'
                                                    : 'border-border bg-card hover:bg-accent/30'
                                            }`}
                                        >
                                            <div className="text-xs font-bold text-foreground">Single Pharmacy</div>
                                            <div className="text-[11px] text-muted-foreground mt-0.5">1 Shop counter (₹999/mo)</div>
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setPlanType('multi_pharmacy')}
                                            className={`p-3 rounded-none border text-left transition-all cursor-pointer ${
                                                planType === 'multi_pharmacy'
                                                    ? 'border-primary bg-card border-l-4 border-l-primary font-semibold shadow-2xs'
                                                    : 'border-border bg-card hover:bg-accent/30'
                                            }`}
                                        >
                                            <div className="text-xs font-bold text-foreground">Multiple Pharmacy Chain</div>
                                            <div className="text-[11px] text-muted-foreground mt-0.5">2+ Branches central sync (₹2,499/mo)</div>
                                        </button>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between pt-2 border-t border-border">
                                    <div>
                                        <p className="text-xs font-semibold text-foreground">FEFO Expiry &amp; Low-Stock Alerts</p>
                                        <p className="text-xs text-muted-foreground">Receive alerts for 30/60-day expiring batches and shortage warnings</p>
                                    </div>
                                    <input
                                        type="checkbox"
                                        checked={fefoAlertsEnabled}
                                        onChange={(e) => setFefoAlertsEnabled(e.target.checked)}
                                        className="h-4 w-4 rounded-none border-border text-primary focus:ring-0 cursor-pointer"
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* STEP 2: Core Capabilities Tour */}
                    {step === 2 && (
                        <div className="space-y-5 animate-in fade-in duration-200">
                            <div>
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-none text-xs font-semibold bg-accent text-foreground border border-border mb-2">
                                    ⚡ Core Capabilities
                                </span>
                                <h3 className="text-xl font-sans font-bold text-foreground tracking-tight">
                                    Explore InvIQ's Chemist OS Engine
                                </h3>
                                <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                                    Built specifically for retail medical stores, local pharmacy chains, and medicine distributors.
                                </p>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="p-4 rounded-none border border-border bg-card hover:border-foreground/40 transition-colors shadow-2xs">
                                    <div className="w-8 h-8 rounded-none bg-accent flex items-center justify-center text-foreground mb-2.5 border border-border">
                                        <Clock size={16} className="text-[#F26A4B]" />
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground">Zero Expiry Loss (FEFO)</h4>
                                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                        Automatic 30/60/90-day expiry queue to return near-expiry medicines to distributors for credit before loss.
                                    </p>
                                </div>

                                <div className="p-4 rounded-none border border-border bg-card hover:border-foreground/40 transition-colors shadow-2xs">
                                    <div className="w-8 h-8 rounded-none bg-accent flex items-center justify-center text-foreground mb-2.5 border border-border">
                                        <ThermometerSnowflake size={16} className="text-[#2E2E2E]" />
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground">Cold-Chain Fridge Compliance</h4>
                                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                        Live 2°C–8°C temperature tracking for Insulins, Vaccines, and biological injections with breach alerts.
                                    </p>
                                </div>

                                <div className="p-4 rounded-none border border-border bg-card hover:border-foreground/40 transition-colors shadow-2xs">
                                    <div className="w-8 h-8 rounded-none bg-accent flex items-center justify-center text-foreground mb-2.5 border border-border">
                                        <Bot size={16} className="text-[#F26A4B]" />
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground">Personalized AI Copilot</h4>
                                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                        Ask queries in plain English to look up stock, batches, and reorder levels in real time.
                                    </p>
                                </div>

                                <div className="p-4 rounded-none border border-border bg-card hover:border-foreground/40 transition-colors shadow-2xs">
                                    <div className="w-8 h-8 rounded-none bg-accent flex items-center justify-center text-foreground mb-2.5 border border-border">
                                        <Truck size={16} className="text-[#2E2E2E]" />
                                    </div>
                                    <h4 className="text-sm font-bold text-foreground">Distributor Portal &amp; POs</h4>
                                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                                        Connect pharmaceutical distributors and ingest delivery manifests automatically into your inventory.
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* STEP 3: Recommended First Actions */}
                    {step === 3 && (
                        <div className="space-y-5 animate-in fade-in duration-200">
                            <div>
                                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-none text-xs font-semibold bg-accent text-foreground border border-border mb-2">
                                    🚀 Tailored for {roleTitle}
                                </span>
                                <h3 className="text-xl font-sans font-bold text-foreground tracking-tight">
                                    Recommended First Actions
                                </h3>
                                <p className="text-xs sm:text-sm text-muted-foreground mt-1">
                                    Choose an action below to kickstart your daily chemist workflow:
                                </p>
                            </div>

                            <div className="space-y-2.5">
                                <div
                                    onClick={() => handleComplete('/admin/stock-acquisition')}
                                    className="p-3.5 rounded-none border border-border hover:border-primary bg-accent/20 hover:bg-accent/40 cursor-pointer flex items-center justify-between transition-all"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-none bg-primary text-[#F26A4B] flex items-center justify-center">
                                            <UploadCloud size={16} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-bold text-foreground flex items-center gap-2">
                                                <span>Guided First Medicine Catalog Import</span>
                                                <span className="px-1.5 py-0.2 bg-accent text-foreground text-[10px] rounded-none font-bold border border-border">Recommended</span>
                                            </p>
                                            <p className="text-xs text-muted-foreground">Import your existing stock CSV/Excel with auto-mapping &amp; validation preview.</p>
                                        </div>
                                    </div>
                                    <ArrowRight size={16} className="text-foreground shrink-0" />
                                </div>

                                <div
                                    onClick={() => handleComplete('/admin/organization')}
                                    className="p-3.5 rounded-none border border-border hover:border-primary bg-card hover:bg-accent/30 cursor-pointer flex items-center justify-between transition-all"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-none bg-accent text-foreground border border-border flex items-center justify-center">
                                            <Building2 size={16} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-foreground">Configure Pharmacy Branches &amp; Licenses</p>
                                            <p className="text-xs text-muted-foreground">Set Drug License numbers (DL), GSTIN, and retail counter locations.</p>
                                        </div>
                                    </div>
                                    <ArrowRight size={16} className="text-muted-foreground" />
                                </div>

                                <div
                                    onClick={() => handleComplete('/admin/inventory')}
                                    className="p-3.5 rounded-none border border-border hover:border-primary bg-card hover:bg-accent/30 cursor-pointer flex items-center justify-between transition-all"
                                >
                                    <div className="flex items-center gap-3">
                                        <div className="w-8 h-8 rounded-none bg-accent text-foreground border border-border flex items-center justify-center">
                                            <Boxes size={16} />
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-foreground">Inspect Medicine Catalog &amp; Stocks</p>
                                            <p className="text-xs text-muted-foreground">Review medicines, batch numbers, MRPs, and FEFO expiry queues.</p>
                                        </div>
                                    </div>
                                    <ArrowRight size={16} className="text-muted-foreground" />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* STEP 4: Ready to Launch */}
                    {step === 4 && (
                        <div className="space-y-5 text-center animate-in fade-in duration-200 py-4">
                            <div className="w-14 h-14 bg-primary text-[#F26A4B] rounded-none flex items-center justify-center mx-auto border border-primary shadow-xs">
                                <CheckCircle2 size={28} />
                            </div>

                            <div>
                                <h3 className="text-2xl font-sans font-bold text-foreground tracking-tight">
                                    Your Chemist OS is Ready!
                                </h3>
                                <p className="text-xs sm:text-sm text-muted-foreground max-w-md mx-auto mt-2">
                                    Welcome, <strong>{greetingName}</strong>. Your pharmacy profile is configured for <strong>{pharmacyName}</strong>.
                                </p>
                            </div>

                            <div className="bg-accent/20 border border-border rounded-none p-4 max-w-md mx-auto text-left text-xs text-foreground space-y-2">
                                <div className="flex items-center gap-2">
                                    <Check size={14} className="text-[#F26A4B] shrink-0 font-bold" />
                                    <span>Administrator: <strong>{greetingName}</strong></span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Check size={14} className="text-[#F26A4B] shrink-0 font-bold" />
                                    <span>Pharmacy Name: <strong>{pharmacyName}</strong></span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Check size={14} className="text-[#F26A4B] shrink-0 font-bold" />
                                    <span>Primary Counter: <strong>{primaryCounter}</strong></span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <Check size={14} className="text-[#F26A4B] shrink-0 font-bold" />
                                    <span>Plan: <strong>{planType === 'single_pharmacy' ? 'Single Pharmacy' : 'Multiple Pharmacy Chain'}</strong></span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* ── Modal Footer ───────────────────────── */}
                <div className="p-4 md:p-5 border-t border-border bg-accent/30 flex items-center justify-between">
                    <div>
                        {step > 1 ? (
                            <button
                                onClick={handleBack}
                                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-foreground bg-card border border-border rounded-none hover:bg-accent transition-colors cursor-pointer"
                            >
                                <ArrowLeft size={14} />
                                <span>Back</span>
                            </button>
                        ) : (
                            <button
                                onClick={handleClose}
                                className="text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                            >
                                Skip Tour
                            </button>
                        )}
                    </div>

                    <div className="flex items-center gap-2">
                        {step < 4 ? (
                            <button
                                onClick={handleNext}
                                className="inline-flex items-center gap-1.5 px-5 py-2 text-xs font-bold text-primary-foreground bg-primary rounded-none hover:bg-black transition-all shadow-xs cursor-pointer"
                            >
                                <span>Continue</span>
                                <ArrowRight size={14} />
                            </button>
                        ) : (
                            <button
                                onClick={() => handleComplete('/admin/dashboard')}
                                className="inline-flex items-center gap-1.5 px-6 py-2.5 text-xs font-bold text-primary-foreground bg-primary rounded-none hover:bg-black transition-all shadow-md cursor-pointer"
                            >
                                <span>Open Chemist Dashboard</span>
                                <ArrowRight size={14} />
                            </button>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}
