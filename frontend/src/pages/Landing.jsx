/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { 
  Sparkles, Search, Download, Plus, ChevronDown, ArrowUpRight, ArrowDownRight, 
  MapPin, Box, Layers, Check, ArrowLeft, ArrowRight, Phone, PhoneCall, TrendingUp, Play, 
  HelpCircle, Star, Activity, Zap, Network, LineChart, Lock, Globe, PanelLeftClose, 
  Ship, Truck, CreditCard, Calendar, Clock, LayoutDashboard, BarChart3, Users, 
  Menu, X, AlertTriangle, Building2, Tag, MoveRight
} from 'lucide-react';

import { ShineBorder } from '../components/ui/shine-border';
import { DotPattern } from '../components/ui/dot-pattern';
import { Typewriter } from '../components/ui/typewriter';

const LogoIcon = () => (
  <img src="/logo.png" alt="InvIQ Logo" className="w-8 h-8 object-contain" />
);

export default function Landing() {
  const [openFaq, setOpenFaq] = React.useState(0);
  const [currentTestimonial, setCurrentTestimonial] = React.useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [isScrolled, setIsScrolled] = React.useState(false);

  React.useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 30);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const testimonials = [
    {
      quote: "Before InvIQ, we lost ₹25,000 every quarter to expired medicine batches sitting on our back shelves. With InvIQ's 30-day FEFO alerts, we return them to the distributor on time. It paid for itself in week one.",
      name: "Rajesh Sharma",
      role: "Owner, Sharma Medicos (Durgapur)",
      image: "https://i.pravatar.cc/150?img=11"
    },
    {
      quote: "I run 2 medical stores 5 km apart. I used to call my shop boy 15 times a day to check stock. Now I just open InvIQ on my mobile and see live stock for both branches instantly.",
      name: "Amit Verma",
      role: "Proprietor, City Care Chemist (Siliguri)",
      image: "https://i.pravatar.cc/150?img=33"
    },
    {
      quote: "As a medicine distributor, uploading delivery Excel bills to InvIQ saves me 2 hours every evening. The chemist gets their stock updated automatically without manual typing.",
      name: "Priya Sen",
      role: "Shree Pharma Wholesale Distributors",
      image: "https://i.pravatar.cc/150?img=47"
    }
  ];

  const nextTestimonial = () => {
    setCurrentTestimonial((prev) => (prev + 1) % testimonials.length);
  };

  const prevTestimonial = () => {
    setCurrentTestimonial((prev) => (prev - 1 + testimonials.length) % testimonials.length);
  };

  const faqs = [
    {
      question: "How does InvIQ stop medicine expiry losses?",
      answer: "InvIQ uses First-Expiry-First-Out (FEFO) intelligence. It tracks batch numbers and expiration dates, sending you advance notifications 30 and 60 days before a batch expires so you can sell it first or return it to your distributor for a credit note."
    },
    {
      question: "Can I manage multiple medical store branches?",
      answer: "Yes! You can add and monitor multiple pharmacy shops (e.g. Market Branch and Station Road Branch) in one unified dashboard on your phone or laptop."
    },
    {
      question: "Can I upload delivery bills from my medicine distributor?",
      answer: "Yes. InvIQ supports Excel (.xlsx) and CSV files from all major medicine distributors. Our AI automatically maps medicine names, batches, quantities, and MRP."
    },
    {
      question: "Do I need to replace my existing billing counter machine?",
      answer: "No. InvIQ works alongside your existing setup as a smart inventory intelligence, expiry prevention, and multi-branch tracking system on any phone, tablet, or PC."
    },
    {
      question: "Can my medicine supplier/distributor access InvIQ?",
      answer: "Yes. You can give your medicine distributor access to the dedicated Vendor Portal where they can view your purchase orders and upload delivery manifests."
    },
    {
      question: "How does the AI assistant help my pharmacy?",
      answer: "You can ask natural questions like 'How many strips of Paracetamol 650 left in Branch 2?' or 'Which batches expire next month?' and get instant answers without searching through complex tables."
    }
  ];

  return (
    <div className="min-h-screen bg-background relative overflow-hidden font-poppins text-foreground">
      {/* Background Gradients & Grid */}
      <div className="absolute inset-0 z-0 pointer-events-none flex justify-center">
        <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-accent/50 rounded-full blur-[100px]" />
        <div className="absolute top-[20%] right-[-10%] w-[60vw] h-[60vw] bg-[#F26A4B]/5 rounded-full blur-[120px]" />
        
        {/* Grid lines */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e1e1e0a_1px,transparent_1px),linear-gradient(to_bottom,#1e1e1e0a_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
      </div>

      {/* Sticky Expanding Navbar */}
      <header className="fixed top-2 sm:top-3 inset-x-0 z-50 px-3 sm:px-6 pointer-events-none flex justify-center transition-all duration-300">
        <nav className={`pointer-events-auto flex items-center justify-between transition-all duration-300 ease-in-out ${
          isScrolled
            ? 'w-full max-w-6xl px-4 sm:px-8 py-2.5 sm:py-3 bg-card/95 backdrop-blur-xl shadow-md border border-border rounded-2xl sm:rounded-full'
            : 'w-full max-w-4xl px-4 sm:px-6 py-2 sm:py-2.5 bg-card/85 backdrop-blur-md shadow-xs border border-border/70 rounded-full'
        }`}>
          <div className="flex items-center gap-2 cursor-pointer group" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
            <div className="group-hover:scale-110 transition-transform duration-200">
              <LogoIcon />
            </div>
            <span className="font-poppins font-bold text-lg sm:text-xl tracking-tight text-foreground group-hover:text-[#F26A4B] transition-colors">InvIQ</span>
          </div>
          <div className="hidden md:flex items-center gap-1 lg:gap-2 text-sm font-medium text-muted-foreground">
            {['features', 'process', 'pricing', 'faq', 'customers'].map((id) => (
              <button 
                key={id}
                onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })} 
                className="px-3 py-1.5 rounded-full hover:text-foreground hover:bg-accent transition-all duration-200 capitalize cursor-pointer"
              >
                {id === 'faq' ? 'FAQ' : id}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <button 
              onClick={() => window.location.href = '/signin'} 
              className="hidden md:inline-flex text-muted-foreground px-3 sm:px-4 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-semibold hover:text-foreground hover:bg-accent hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer"
            >
              Log In
            </button>
            <button 
              onClick={() => window.location.href = '/signup'} 
              className="hidden md:inline-flex bg-primary hover:bg-black text-primary-foreground px-3.5 sm:px-5 py-1.5 sm:py-2 rounded-full text-xs sm:text-sm font-semibold hover:shadow-md hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer"
            >
              Sign up
            </button>
            <button
              className="md:hidden p-1.5 rounded-full hover:bg-accent text-foreground transition-colors pointer-events-auto cursor-pointer"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle Menu"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </nav>
      </header>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-x-3 top-16 z-50 bg-card/98 backdrop-blur-2xl rounded-3xl border border-border shadow-2xl p-5 flex flex-col gap-3 animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <LogoIcon />
              <span className="font-poppins font-bold text-lg text-foreground">InvIQ Menu</span>
            </div>
            <button onClick={() => setMobileMenuOpen(false)} className="p-1 rounded-full text-muted-foreground hover:bg-accent cursor-pointer">
              <X className="w-5 h-5" />
            </button>
          </div>
          {['features', 'process', 'pricing', 'faq', 'customers'].map((id) => (
            <button
              key={id}
              onClick={() => { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }); setMobileMenuOpen(false); }}
              className="text-left py-2 px-3 rounded-xl text-foreground font-medium capitalize hover:bg-accent transition-colors cursor-pointer"
            >
              {id === 'faq' ? 'FAQ' : id.charAt(0).toUpperCase() + id.slice(1)}
            </button>
          ))}
          <div className="pt-2 border-t border-border flex flex-col gap-2">
            <button
              onClick={() => window.location.href = '/signin'}
              className="w-full border border-border text-foreground py-2.5 rounded-full text-sm font-semibold hover:bg-accent active:scale-98 transition-all cursor-pointer"
            >
              Log In
            </button>
            <button
              onClick={() => window.location.href = '/signup'}
              className="w-full bg-primary text-primary-foreground py-2.5 rounded-full text-sm font-semibold hover:bg-black hover:shadow-md active:scale-98 transition-all cursor-pointer"
            >
              Sign up
            </button>
          </div>
        </div>
      )}

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 sm:pt-28 pb-20">

        {/* Hero Section */}
        <div className="text-center max-w-4xl mx-auto mb-10 sm:mb-16 md:mb-20 px-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-card border border-border text-foreground text-xs sm:text-sm font-medium mb-6 hover:bg-accent hover:scale-105 transition-all duration-200 cursor-default shadow-xs">
            <Sparkles className="w-3.5 h-3.5 text-[#F26A4B]" />
            <span>Built for Medical Store &amp; Pharmacy Owners</span>
          </div>

          <h1 className="text-3xl sm:text-5xl md:text-7xl font-poppins font-bold tracking-tight text-foreground mb-5 md:mb-7 leading-[1.15] cursor-default">
            Never Lose Money on<br />
            <span className="text-[#F26A4B] inline-block min-h-[1.2em]">
              <Typewriter
                words={[
                  "Expired Medicines",
                  "Missed Reorders",
                  "Low-Stock Surprises",
                ]}
                speed={75}
                deleteSpeed={40}
                delayBetweenWords={2200}
                cursor={true}
                cursorChar="|"
              />
            </span>
          </h1>

          <p className="text-sm sm:text-base md:text-lg text-muted-foreground mb-8 sm:mb-10 max-w-xl mx-auto leading-relaxed">
            Know what's running low, return expiring batches on time, and manage every shop from your phone.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-5">
            <button
              onClick={() => window.location.href = '/signup'}
              className="w-full sm:w-auto bg-primary hover:bg-black text-primary-foreground px-8 py-3.5 rounded-full text-sm sm:text-base font-semibold hover:shadow-xl hover:-translate-y-1 hover:scale-105 active:scale-95 transition-all duration-200 cursor-pointer flex items-center justify-center gap-2 group"
            >
              <span>Get started</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform duration-200" />
            </button>

            <button
              onClick={() => window.location.href = '/preview'}
              className="w-full sm:w-auto bg-card text-foreground border border-border px-8 py-3.5 rounded-full text-sm sm:text-base font-semibold hover:bg-accent hover:border-primary/40 hover:shadow-md hover:-translate-y-1 hover:scale-105 active:scale-95 transition-all duration-200 flex items-center justify-center gap-2 cursor-pointer group"
            >
              <Play className="w-4 h-4 fill-foreground text-foreground group-hover:fill-[#F26A4B] group-hover:text-[#F26A4B] group-hover:scale-125 transition-all duration-200" />
              <span>Preview Demo</span>
            </button>
          </div>
        </div>

        {/* Dashboard Mockup */}
        <div className="relative mx-auto max-w-6xl mt-4 mb-10 group cursor-default">
          <div className="absolute -inset-1.5 bg-gradient-to-r from-[#F26A4B]/15 via-primary/10 to-[#A89F8F]/20 rounded-3xl blur-2xl opacity-70 group-hover:opacity-100 group-hover:blur-3xl transition-all duration-500 -z-10" />

          <ShineBorder
            borderRadius={24}
            borderWidth={1.5}
            duration={12}
            color={["#F26A4B", "#2E2E2E", "#D8D2C4", "#A89F8F"]}
            className="w-full p-0 overflow-hidden shadow-2xl group-hover:-translate-y-1.5 rounded-2xl md:rounded-3xl border border-border group-hover:border-primary/40 transition-all duration-500"
          >
            <div className="w-full bg-card select-none pointer-events-none cursor-default overflow-hidden aspect-[2684/1870]">
              <img
                src="/PreviewCard.png"
                alt="InvIQ Smart Pharmacy Dashboard Preview"
                width={2684}
                height={1870}
                className="w-full h-full object-contain select-none pointer-events-none block group-hover:scale-[1.01] transition-transform duration-500"
                loading="eager"
                decoding="async"
              />
            </div>
          </ShineBorder>
        </div>
      </div>

      {/* Features Section */}
      <div id="features" className="py-24 border-t border-border relative overflow-hidden bg-card/60">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e1e1e0a_1px,transparent_1px),linear-gradient(to_bottom,#1e1e1e0a_1px,transparent_1px)] bg-[size:80px_80px] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" />
        
        <div className="text-center max-w-3xl mx-auto mb-20 relative z-10 px-4">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-card border border-border shadow-xs text-foreground text-sm font-medium mb-6">
            <Star className="w-4 h-4 mr-2 text-[#F26A4B]" />
            Features
          </div>
          <h2 className="text-4xl md:text-5xl font-poppins font-bold text-foreground mb-6 tracking-tight">
            Smart Pharmacy Inventory Intelligence
          </h2>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            Track medicines live across branches, prevent costly expiry losses with FEFO, and automate distributor reordering with AI.
          </p>
        </div>

        <div className="max-w-6xl mx-auto relative px-6 sm:px-10 lg:px-12 z-10">
          {/* Connecting Lines (Desktop) */}
          <div className="hidden lg:block absolute top-[25%] bottom-[25%] left-12 w-12 border-l-2 border-t-2 border-b-2 border-border rounded-l-3xl z-0" />
          <div className="hidden lg:block absolute top-1/2 left-0 w-12 h-[2px] bg-border -translate-y-1/2 z-0" />

          <div className="hidden lg:block absolute top-[25%] bottom-[25%] right-12 w-12 border-r-2 border-t-2 border-b-2 border-border rounded-r-3xl z-0" />
          <div className="hidden lg:block absolute top-1/2 right-0 w-12 h-[2px] bg-border -translate-y-1/2 z-0" />
          
          {/* Left Icon Node */}
          <div className="hidden lg:flex absolute top-1/2 left-0 w-12 h-12 bg-primary rounded-full items-center justify-center text-primary-foreground shadow-md -translate-y-1/2 -translate-x-1/2 z-20 ring-4 ring-card">
            <Lock className="w-5 h-5" />
          </div>
          
          {/* Right Icon Node */}
          <div className="hidden lg:flex absolute top-1/2 right-0 w-12 h-12 bg-primary rounded-full items-center justify-center text-primary-foreground shadow-md -translate-y-1/2 translate-x-1/2 z-20 ring-4 ring-card">
            <Globe className="w-5 h-5" />
          </div>

          {/* 2x2 Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-10 relative z-10 lg:px-20">
            
            {/* Card 1 */}
            <div className="bg-card backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 group cursor-default">
              <div className="w-12 h-12 bg-accent rounded-2xl flex items-center justify-center mb-6 text-[#F26A4B] group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                <Activity className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">Zero-Expiry Loss (FEFO)</h3>
              <p className="text-muted-foreground leading-relaxed">
                30 and 60 day advance alerts on expiring medicine batches so you can sell them first or return to your distributor for credit.
              </p>
            </div>

            {/* Card 2 */}
            <div className="bg-card backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 group cursor-default">
              <div className="w-12 h-12 bg-accent rounded-2xl flex items-center justify-center mb-6 text-[#F26A4B] group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                <Zap className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">Predictive Low-Stock Alerts</h3>
              <p className="text-muted-foreground leading-relaxed">
                Never turn away a customer. AI predicts running-out medicines based on daily sales and tells you what to reorder today.
              </p>
            </div>

            {/* Card 3 */}
            <div className="bg-card backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 group cursor-default">
              <div className="w-12 h-12 bg-accent rounded-2xl flex items-center justify-center mb-6 text-[#F26A4B] group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                <Network className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">Multi-Shop Branch Tracking</h3>
              <p className="text-muted-foreground leading-relaxed">
                Manage 2 or 3 medicine store branches from your phone with unified live stock sync without calling staff.
              </p>
            </div>

            {/* Card 4 */}
            <div className="bg-card backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 group cursor-default">
              <div className="w-12 h-12 bg-accent rounded-2xl flex items-center justify-center mb-6 text-[#F26A4B] group-hover:scale-110 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                <LineChart className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">1-Click Distributor Excel Ingest</h3>
              <p className="text-muted-foreground leading-relaxed">
                Upload wholesaler delivery manifests (Excel/CSV) to automatically update batch numbers, quantities, and MRP.
              </p>
            </div>

          </div>
        </div>
      </div>

      {/* Process Section */}
      <div id="process" className="py-28 border-t border-border relative bg-background overflow-hidden">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#1e1e1e0a_1px,transparent_1px),linear-gradient(to_bottom,#1e1e1e0a_1px,transparent_1px)] bg-[size:80px_80px] [mask-image:radial-gradient(ellipse_80%_60%_at_50%_50%,#000_70%,transparent_100%)] pointer-events-none" />
        <div className="text-center max-w-3xl mx-auto mb-16 px-4">
          <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-card border border-border shadow-xs text-foreground text-sm font-medium mb-6 hover:scale-105 transition-transform cursor-default">
            <TrendingUp className="w-4 h-4 mr-2 text-[#F26A4B]" />
            Process
          </div>
          <h2 className="text-4xl md:text-5xl font-poppins font-bold text-foreground mb-6 tracking-tight">
            Get Started in 3 Simple Steps
          </h2>
          <p className="text-lg text-muted-foreground leading-relaxed max-w-2xl mx-auto">
            Set up your medical store inventory in minutes and automate stock tracking effortlessly.
          </p>
        </div>

        <div className="max-w-5xl mx-auto relative px-6 sm:px-10">
          {/* Connecting Line */}
          <div className="hidden md:block absolute top-6 left-[16.66%] right-[16.66%] h-px bg-border z-0" />

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
            {/* Step 1 */}
            <div className="flex flex-col items-center text-center group cursor-default">
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-xl flex items-center justify-center text-xl font-bold mb-8 shadow-md group-hover:scale-115 group-hover:bg-[#F26A4B] transition-all duration-300">
                1
              </div>
              <div className="bg-card rounded-3xl p-8 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 w-full h-full">
                <h3 className="text-lg font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">Register Your Shop</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Create your chemist account in 60 seconds and configure your medical store branches.
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex flex-col items-center text-center group cursor-default">
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-xl flex items-center justify-center text-xl font-bold mb-8 shadow-md group-hover:scale-115 group-hover:bg-[#F26A4B] transition-all duration-300">
                2
              </div>
              <div className="bg-card rounded-3xl p-8 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 w-full h-full">
                <h3 className="text-lg font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">Upload Distributor Bills</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Upload your medicine distributor Excel/CSV invoices or add stock manually in seconds.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex flex-col items-center text-center group cursor-default">
              <div className="w-12 h-12 bg-primary text-primary-foreground rounded-xl flex items-center justify-center text-xl font-bold mb-8 shadow-md group-hover:scale-115 group-hover:bg-[#F26A4B] transition-all duration-300">
                3
              </div>
              <div className="bg-card rounded-3xl p-8 border border-border shadow-xs hover:shadow-xl hover:border-primary/50 hover:-translate-y-2 transition-all duration-300 w-full h-full">
                <h3 className="text-lg font-bold text-card-foreground mb-3 group-hover:text-[#F26A4B] transition-colors">Automate Restock &amp; Expiries</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Get predictive reorder alerts, track expiring batches, and send 1-click orders to suppliers.
                </p>
              </div>
            </div>
          </div>

          {/* Blank YouTube Video Section */}
          <div className="mt-24 max-w-4xl mx-auto">
            <div className="aspect-video bg-card rounded-[2rem] border border-border shadow-inner flex items-center justify-center relative overflow-hidden group cursor-pointer hover:border-primary/40 hover:scale-[1.01] transition-all duration-300">
              <div className="absolute inset-0 bg-primary/5 group-hover:bg-primary/10 transition-colors" />
              <div className="w-20 h-20 bg-accent rounded-full flex items-center justify-center shadow-lg group-hover:scale-115 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-300">
                <Play className="w-8 h-8 text-[#F26A4B] group-hover:text-primary-foreground group-hover:fill-primary-foreground ml-1 transition-colors" fill="currentColor" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Pricing Section */}
      <div id="pricing" className="py-28 border-t border-b border-border relative overflow-hidden bg-card">
        <DotPattern
          width={18}
          height={18}
          cx={1}
          cy={1}
          cr={0.75}
          className="[mask-image:radial-gradient(800px_circle_at_center,white,transparent)] fill-foreground/[0.05]"
        />

        {/* Section Header */}
        <div className="relative z-10 text-center max-w-3xl mx-auto mb-16 px-4">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-border bg-background shadow-xs text-foreground text-sm font-medium mb-6">
            <CreditCard className="w-3.5 h-3.5 text-[#F26A4B]" />
            Pricing
          </div>
          <h2 className="text-4xl md:text-5xl font-poppins font-bold text-foreground mb-4 tracking-tight">
            Prices that make sense!
          </h2>
          <p className="text-lg leading-relaxed text-muted-foreground max-w-xl mx-auto">
            Simple, transparent pricing built for local chemist shops and growing pharmacy networks in India.
          </p>
        </div>

        {/* 3 Cards */}
        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-3 w-full gap-8 max-w-6xl mx-auto px-6 sm:px-10 lg:px-12 text-left">

          {/* Card 1: Starter Chemist */}
          <div className="rounded-xl border border-border bg-background shadow-xs hover:-translate-y-1.5 hover:shadow-xl hover:border-primary/40 transition-all duration-300 flex flex-col">
            <div className="p-6 pb-0 flex flex-col gap-1.5">
              <h3 className="text-2xl font-poppins font-semibold text-foreground tracking-tight">Starter Chemist</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Perfect for small retail counters starting digital stock management at zero cost.
              </p>
            </div>
            <div className="p-6 flex flex-col gap-8 flex-1">
              <p className="flex flex-row items-center gap-2">
                <span className="text-5xl font-poppins font-bold text-foreground tracking-tight">₹0</span>
                <span className="text-sm text-muted-foreground"> / forever</span>
              </p>
              <div className="flex flex-col gap-4">
                {[
                  { title: '1 Pharmacy Counter', desc: 'Single shop management with full stock visibility.' },
                  { title: 'Up to 500 Medicine SKUs', desc: 'Start digitizing your medicine catalogue instantly.' },
                  { title: 'Basic FEFO Expiry Alerts', desc: 'Get notified before batches expire and lose value.' },
                  { title: 'Quick Barcode Dispensing', desc: 'Scan and dispense medicines faster at the counter.' },
                  { title: 'Daily Stock Dashboard', desc: 'Clean overview of your inventory every morning.' },
                ].map((f, i) => (
                  <div key={i} className="flex flex-row gap-3">
                    <Check className="w-4 h-4 mt-1 text-foreground shrink-0" strokeWidth={2.5} />
                    <div className="flex flex-col">
                      <p className="text-sm font-medium text-foreground">{f.title}</p>
                      <p className="text-sm text-muted-foreground">{f.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => window.location.href = '/signup'}
                className="mt-auto w-full h-11 px-4 inline-flex items-center justify-center gap-2 rounded-full border border-border bg-accent text-sm font-semibold text-foreground hover:bg-primary hover:text-primary-foreground active:scale-98 transition-all duration-200 cursor-pointer group"
              >
                Get Started Free
                <MoveRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          {/* Card 2: Single Pharmacy — highlighted */}
          <div className="rounded-xl border-2 border-primary bg-background shadow-2xl hover:-translate-y-2 transition-all duration-300 flex flex-col relative">
            <div className="absolute -top-3 right-6 bg-[#F26A4B] text-white text-[11px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full shadow-sm">
              Popular
            </div>
            <div className="p-6 pb-0 flex flex-col gap-1.5">
              <h3 className="text-2xl font-poppins font-semibold text-foreground tracking-tight">Single Pharmacy</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Ideal for standalone chemist shops wanting live stock tracking and expiry loss prevention.
              </p>
            </div>
            <div className="p-6 flex flex-col gap-8 flex-1">
              <p className="flex flex-row items-center gap-2">
                <span className="text-5xl font-poppins font-bold text-foreground tracking-tight">₹999</span>
                <span className="text-sm text-muted-foreground"> / month</span>
              </p>
              <div className="flex flex-col gap-4">
                {[
                  { title: 'Manage 1 Medical Store Branch', desc: 'Full control of one pharmacy with live stock sync.' },
                  { title: 'Up to 3,000 Medicine SKUs', desc: 'Handle a large catalogue with batch-level tracking.' },
                  { title: 'FEFO Alerts (30 / 60 / 90 days)', desc: 'Return expiring batches to distributors for credit.' },
                  { title: 'Distributor Excel / CSV Ingest', desc: 'Upload delivery manifests to update stock in 1 click.' },
                  { title: 'Low-Stock Auto Reorder Alerts', desc: 'AI predicts and alerts before you run out of medicine.' },
                  { title: 'WhatsApp & Email Support', desc: 'Get human support on WhatsApp within business hours.' },
                ].map((f, i) => (
                  <div key={i} className="flex flex-row gap-3">
                    <Check className="w-4 h-4 mt-1 text-foreground shrink-0" strokeWidth={2.5} />
                    <div className="flex flex-col">
                      <p className="text-sm font-medium text-foreground">{f.title}</p>
                      <p className="text-sm text-muted-foreground">{f.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => window.location.href = '/signup'}
                className="mt-auto w-full h-11 px-4 inline-flex items-center justify-center gap-2 rounded-full bg-primary text-sm font-semibold text-primary-foreground hover:bg-black hover:shadow-xl hover:scale-[1.02] active:scale-98 transition-all duration-200 cursor-pointer group"
              >
                Start Free Trial
                <MoveRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
              </button>
            </div>
          </div>

          {/* Card 3: Multiple Pharmacy Chain */}
          <div className="rounded-xl border border-border bg-background shadow-xs hover:-translate-y-1.5 hover:shadow-xl hover:border-primary/40 transition-all duration-300 flex flex-col">
            <div className="p-6 pb-0 flex flex-col gap-1.5">
              <h3 className="text-2xl font-poppins font-semibold text-foreground tracking-tight">Pharmacy Chain</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                For chemist owners managing 2+ branches with central supplier ordering and live sync.
              </p>
            </div>
            <div className="p-6 flex flex-col gap-8 flex-1">
              <p className="flex flex-row items-center gap-2">
                <span className="text-5xl font-poppins font-bold text-foreground tracking-tight">₹2499</span>
                <span className="text-sm text-muted-foreground"> / month</span>
              </p>
              <div className="flex flex-col gap-4">
                {[
                  { title: 'Multiple Medical Store Branches', desc: 'Manage all branches from one unified dashboard.' },
                  { title: 'Unlimited Medicine SKUs', desc: 'No cap on catalogue size — scale without limits.' },
                  { title: 'Multi-Branch Live Stock Sync', desc: 'See real-time stock across every shop instantly.' },
                  { title: 'Branch-to-Branch Transfers', desc: 'Move stock between locations in one tap.' },
                  { title: 'Cold-Chain Fridge Monitoring', desc: 'Track vaccine fridge temperatures in real time.' },
                  { title: 'Priority WhatsApp & Phone Support', desc: 'Dedicated account manager and phone helpline.' },
                ].map((f, i) => (
                  <div key={i} className="flex flex-row gap-3">
                    <Check className="w-4 h-4 mt-1 text-foreground shrink-0" strokeWidth={2.5} />
                    <div className="flex flex-col">
                      <p className="text-sm font-medium text-foreground">{f.title}</p>
                      <p className="text-sm text-muted-foreground">{f.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button
                onClick={() => window.location.href = '/signup'}
                className="mt-auto w-full h-11 px-4 inline-flex items-center justify-center gap-2 rounded-full border border-border bg-accent text-sm font-semibold text-foreground hover:bg-primary hover:text-primary-foreground active:scale-98 transition-all duration-200 cursor-pointer group"
              >
                Book a Meeting
                <PhoneCall className="w-4 h-4" />
              </button>
            </div>
          </div>

        </div>
      </div>

      {/* Customers Section */}
      <div id="customers" className="py-28 border-b border-border relative bg-background overflow-hidden">
        <DotPattern
          width={18}
          height={18}
          cx={1}
          cy={1}
          cr={0.75}
          className="[mask-image:radial-gradient(900px_circle_at_center,white,transparent)] fill-foreground/[0.05]"
        />

        <div className="text-center max-w-3xl mx-auto mb-12 relative z-10 px-4">
          <h2 className="text-4xl md:text-5xl font-poppins font-bold text-foreground mb-4 tracking-tight">
            Hear From <span className="text-[#F26A4B]">Our Customers</span>
          </h2>
          <p className="text-[15px] text-muted-foreground leading-relaxed max-w-xl mx-auto">
            Smarter inventory. Real impact. See how InvIQ boosts<br className="hidden md:block" />efficiency and eliminates stock issues.
          </p>
        </div>

        <div className="max-w-2xl mx-auto relative z-10 px-6 sm:px-10">
          <div className="bg-card rounded-2xl p-10 md:p-12 border border-border shadow-xs hover:shadow-xl hover:border-primary/40 transition-all duration-300 mb-10">
            <p className="text-card-foreground text-[15px] text-center leading-relaxed mb-8">
              "{testimonials[currentTestimonial].quote}"
            </p>
            <div className="flex items-center justify-center gap-4">
              <img src={testimonials[currentTestimonial].image} alt={testimonials[currentTestimonial].name} className="w-12 h-12 rounded-full object-cover shadow-sm ring-2 ring-border" />
              <div className="text-left">
                <div className="font-semibold text-card-foreground text-sm">{testimonials[currentTestimonial].name}</div>
                <div className="text-sm text-muted-foreground">{testimonials[currentTestimonial].role}</div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center gap-4">
            <button 
              onClick={prevTestimonial}
              className="w-10 h-10 flex items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-primary hover:text-primary-foreground hover:border-primary hover:scale-110 active:scale-90 transition-all duration-200 shadow-xs cursor-pointer"
              aria-label="Previous Testimonial"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <button 
              onClick={nextTestimonial}
              className="w-10 h-10 flex items-center justify-center rounded-xl border border-border bg-card text-foreground hover:bg-primary hover:text-primary-foreground hover:border-primary hover:scale-110 active:scale-90 transition-all duration-200 shadow-xs cursor-pointer"
              aria-label="Next Testimonial"
            >
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div id="faq" className="py-24 relative bg-card border-b border-border overflow-hidden z-10">
        <div className="absolute inset-0 bg-[radial-gradient(#1e1e1e0a_0.75px,transparent_0.75px)] [background-size:24px_24px] opacity-25" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-20">
          <div className="flex flex-col lg:flex-row gap-16 lg:gap-24">
            {/* Left Column */}
            <div className="lg:w-1/3 flex flex-col items-start">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-background border border-border shadow-xs text-foreground text-sm font-medium mb-6 hover:scale-105 transition-transform cursor-default">
                <HelpCircle className="w-4 h-4 text-[#F26A4B]" />
                FAQs
              </div>
              <h2 className="text-4xl md:text-5xl font-poppins font-bold text-foreground mb-6 tracking-tight leading-tight">
                Frequently asked<br />questions
              </h2>
              <p className="text-muted-foreground mb-8 leading-relaxed">
                Some answers to common questions we get asked. Feel free to reach out if you have any inquiries:
              </p>
              <button 
                onClick={() => window.location.href = '/signup'}
                className="px-8 py-3.5 bg-primary hover:bg-black text-primary-foreground font-semibold rounded-full hover:shadow-xl hover:scale-105 active:scale-95 transition-all duration-200 shadow-md cursor-pointer"
              >
                Get started
              </button>
            </div>

            {/* Right Column */}
            <div className="lg:w-2/3 flex flex-col gap-4">
              {faqs.map((faq, index) => (
                <div 
                  key={index}
                  className="bg-background rounded-2xl border border-border hover:border-primary/50 shadow-xs hover:shadow-md hover:-translate-y-0.5 overflow-hidden transition-all duration-300"
                >
                  <button 
                    onClick={() => setOpenFaq(openFaq === index ? -1 : index)}
                    className="w-full px-6 py-5 flex items-center justify-between text-left cursor-pointer group"
                  >
                    <span className="font-semibold text-foreground group-hover:text-[#F26A4B] transition-colors pr-8">{faq.question}</span>
                    {openFaq === index ? (
                      <ArrowDownRight className="w-5 h-5 text-[#F26A4B] group-hover:scale-110 flex-shrink-0 transition-transform" />
                    ) : (
                      <ArrowUpRight className="w-5 h-5 text-[#F26A4B] group-hover:scale-110 flex-shrink-0 transition-transform" />
                    )}
                  </button>
                  
                  <div 
                    className={`px-6 overflow-hidden transition-all duration-300 ease-in-out ${
                      openFaq === index ? 'max-h-48 pb-6 opacity-100' : 'max-h-0 opacity-0'
                    }`}
                  >
                    <div className="w-full h-px bg-border mb-4" />
                    <p className="text-muted-foreground text-sm leading-relaxed">
                      {faq.answer}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* CTA & Footer Section */}
      <div className="relative z-10 w-full">
        {/* Dark Warm Editorial CTA Banner */}
        <div className="bg-[#1E1E1E] text-[#E9E4D8] relative overflow-hidden">
          {/* Decorative shapes */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-white/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-[#F26A4B]/10 rounded-full blur-2xl translate-y-1/3" />
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-24 relative z-10">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-10">
              <div className="max-w-xl">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 text-[#E9E4D8] text-sm font-medium mb-6 shadow-xs cursor-default">
                  <Phone className="w-4 h-4 text-[#F26A4B]" />
                  Contact
                </div>
                <h2 className="text-4xl md:text-5xl font-poppins font-bold mb-4 leading-tight">
                  Expand Your Reach with<br />InvIQ's Smart Platform
                </h2>
                <p className="text-[#A89F8F] text-lg">
                  Manage inventory, streamline operations, and scale your business anywhere in the world.
                </p>
              </div>
              
              <div className="w-full lg:w-auto flex flex-col sm:flex-row gap-3">
                <input 
                  type="email" 
                  placeholder="Enter your email" 
                  className="px-6 py-4 rounded-xl text-foreground w-full sm:w-80 focus:outline-none focus:ring-2 focus:ring-[#F26A4B] shadow-sm bg-card border border-border"
                />
                <button 
                  onClick={() => alert("Thank you! Our pharmacy onboarding specialist will contact you shortly.")}
                  className="px-8 py-4 bg-[#F26A4B] hover:bg-[#e05b3d] text-white font-semibold rounded-xl hover:shadow-xl hover:scale-105 active:scale-95 transition-all duration-200 shadow-sm whitespace-nowrap cursor-pointer"
                >
                  Contact Us
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Links */}
        <footer className="bg-card pt-20 pb-10 border-t border-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 md:grid-cols-5 gap-8 mb-16">
              <div className="col-span-2">
                <div className="flex items-center gap-2 mb-4 group cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
                  <div className="group-hover:scale-110 transition-transform duration-200">
                    <LogoIcon />
                  </div>
                  <span className="font-poppins font-bold text-xl tracking-tight text-foreground group-hover:text-[#F26A4B] transition-colors">InvIQ</span>
                </div>
                <p className="text-muted-foreground text-sm max-w-sm mb-6 leading-relaxed">
                  Next-generation smart pharmacy inventory management with real-time tracking, AI-powered forecasting, and cold-chain compliance.
                </p>
              </div>
              
              <div>
                <h4 className="font-semibold text-foreground mb-6">Menu</h4>
                <ul className="space-y-3.5">
                  <li><a href="#" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Home</a></li>
                  <li><a href="#features" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Features</a></li>
                  <li><a href="#process" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Process</a></li>
                  <li><a href="#pricing" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Pricing</a></li>
                  <li><a href="/preview" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Live Demo</a></li>
                </ul>
              </div>

              <div>
                <h4 className="font-semibold text-foreground mb-6">Company</h4>
                <ul className="space-y-3.5">
                  <li><a href="#" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">About Us</a></li>
                  <li><a href="#faq" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Contact Us</a></li>
                </ul>
              </div>

              <div>
                <h4 className="font-semibold text-foreground mb-6">Other Pages</h4>
                <ul className="space-y-3.5">
                  <li><a href="#customers" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Customers</a></li>
                  <li><a href="/signin" className="text-muted-foreground hover:text-foreground hover:translate-x-1 transition-all duration-150 inline-block">Pharmacist Portal</a></li>
                </ul>
              </div>
            </div>

            <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-border gap-4">
              <p className="text-muted-foreground text-sm">
                © 2026 InvIQ. All rights reserved.
              </p>
              <div className="flex items-center gap-6 text-sm">
                <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">Privacy Policy</a>
                <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">Terms of Service</a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}
