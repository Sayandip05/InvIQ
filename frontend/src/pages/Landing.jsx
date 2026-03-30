/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Sparkles, Search, Bell, Download, RefreshCw, Plus, ChevronDown, ArrowUpRight, ArrowDownRight, MapPin, Box, Layers, AlertTriangle, Maximize2, Check, ArrowLeft, ArrowRight, Phone, TrendingUp, Play, HelpCircle, Star, Activity, Zap, Network, LineChart, Lock, Globe, PanelLeftClose, Ship, Truck, CreditCard, Calendar, Clock, LayoutDashboard, BarChart3, Users } from 'lucide-react';

const LogoIcon = () => (
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="28" height="28" rx="8" fill="#3B82F6" />
    <path d="M10 8H18M14 8V20M10 20H18" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export default function Landing() {
  const [openFaq, setOpenFaq] = React.useState(0);
  const [currentTestimonial, setCurrentTestimonial] = React.useState(0);

  const testimonials = [
    {
      quote: "Our business experienced a significant transformation thanks to this team's digital marketing expertise. They delivered tangible improvements in our online visibility.",
      name: "Amanda Holly",
      role: "Nursing Assistant",
      image: "https://i.pravatar.cc/150?img=47"
    },
    {
      quote: "The inventory management features are unparalleled. We've reduced our stockouts by 80% and improved our overall efficiency across all warehouses.",
      name: "Marcus Chen",
      role: "Operations Director",
      image: "https://i.pravatar.cc/150?img=11"
    },
    {
      quote: "Switching to this platform was the best decision we made this year. The automated restocking alone has saved us countless hours of manual work.",
      name: "Sarah Jenkins",
      role: "E-commerce Manager",
      image: "https://i.pravatar.cc/150?img=32"
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
      question: "What is Inviq, and how does it work?",
      answer: "Inviq is an AI-powered inventory management system designed to simplify stock tracking. It uses artificial intelligence to handle tasks like demand forecasting, low stock alerts, and automated reordering. Simply connect your sales channels, and Inviq takes care of the rest."
    },
    {
      question: "Can I use Inviq without prior inventory management experience?",
      answer: "Yes, our platform is designed with an intuitive interface that makes it easy for anyone to start managing inventory like a pro."
    },
    {
      question: "What file formats does Inviq support?",
      answer: "We support CSV, Excel, and direct API integrations with major e-commerce platforms and accounting software."
    },
    {
      question: "How does the AI generation feature work?",
      answer: "Our AI analyzes historical sales data and seasonal trends to generate accurate demand forecasts and automated purchase orders."
    },
    {
      question: "Can I collaborate with my team on Inviq?",
      answer: "Absolutely! You can invite team members, assign specific roles, and control access levels for different parts of your inventory."
    },
    {
      question: "What are the cloud storage limits?",
      answer: "Storage limits vary by plan. Our Starter plan includes 10GB, while Professional and Enterprise plans offer unlimited storage."
    }
  ];

  return (
    <div className="min-h-screen bg-[#FAFAFA] relative overflow-hidden font-sans text-slate-900">
      {/* Background Gradients & Grid */}
      <div className="absolute inset-0 z-0 pointer-events-none flex justify-center">
        <div className="absolute top-[-10%] left-[-10%] w-[50vw] h-[50vw] bg-indigo-100/40 rounded-full blur-[100px]" />
        <div className="absolute top-[20%] right-[-10%] w-[60vw] h-[60vw] bg-blue-50/40 rounded-full blur-[120px]" />
        
        {/* Grid lines */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:100px_100px] [mask-image:radial-gradient(ellipse_80%_50%_at_50%_0%,#000_70%,transparent_100%)]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-24">
        {/* Navbar */}
        <nav className="flex items-center justify-between px-6 py-3 bg-white/80 backdrop-blur-md rounded-full border border-slate-200/60 shadow-sm mb-20">
          <div className="flex items-center gap-2">
            <LogoIcon />
            <span className="font-semibold text-lg tracking-tight">Inviq</span>
          </div>
          <div className="hidden md:flex items-center gap-8 text-sm font-medium text-slate-600">
            {['features', 'process', 'pricing', 'faq', 'customers'].map((id) => (
              <button 
                key={id}
                onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' })} 
                className="hover:text-slate-900 transition-colors capitalize"
              >
                {id === 'faq' ? 'FAQ' : id}
              </button>
            ))}
          </div>
          <div>
            <button 
              onClick={() => window.location.href = '/signup'} 
              className="bg-black text-white px-5 py-2.5 rounded-full text-sm font-medium hover:bg-slate-800 transition-colors"
            >
              Sign up
            </button>
          </div>
        </nav>

        {/* Hero Section */}
        <div className="text-center max-w-4xl mx-auto mb-20">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-700 text-sm font-medium mb-8">
            <Sparkles className="w-4 h-4" />
            Trusted by 5,000+ teams
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-slate-900 mb-6 leading-[1.1]">
            Smarter Inventory,<br />Greater Precision
          </h1>
          <p className="text-lg md:text-xl text-slate-500 mb-10 max-w-2xl mx-auto leading-relaxed">
            Optimize stock levels, prevent shortages, cut excess inventory, and simplify your inventory management effortlessly.
          </p>
          <div className="flex items-center justify-center gap-4">
            <button 
              onClick={() => window.location.href = '/signup'}
              className="bg-blue-600 text-white px-8 py-3.5 rounded-full text-base font-medium hover:bg-blue-700 transition-colors shadow-lg shadow-blue-600/20"
            >
              Get started
            </button>
            <button className="bg-white text-slate-700 border border-slate-200 px-8 py-3.5 rounded-full text-base font-medium hover:bg-slate-50 transition-colors shadow-sm">
              Contact Us
            </button>
          </div>
        </div>

        {/* Dashboard Mockup */}
        <div className="relative mx-auto max-w-6xl">
          {/* Fade out gradient at the bottom */}
          <div className="absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-[#FAFAFA] to-transparent z-20 pointer-events-none" />
          
          <div className="bg-white rounded-3xl border border-slate-200/60 shadow-2xl overflow-hidden flex h-[700px]">
            {/* Sidebar */}
            <div className="w-64 border-r border-slate-100 flex flex-col bg-white shrink-0">
              <div className="p-6 flex items-center gap-2">
                <LogoIcon />
                <span className="font-bold text-xl tracking-tight text-slate-900">Inviq</span>
                <button className="ml-auto text-slate-400 hover:text-slate-600">
                  <PanelLeftClose className="w-5 h-5" />
                </button>
              </div>
              
              <div className="flex-1 px-4 py-2 space-y-1 overflow-y-auto">
                <button className="w-full flex items-center gap-3 px-3 py-2.5 bg-blue-50 text-blue-700 rounded-xl font-medium text-sm border border-blue-100/50">
                  <LayoutDashboard className="w-5 h-5" />
                  Dashboard
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <Ship className="w-5 h-5" />
                  Shipments
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <Box className="w-5 h-5" />
                  Orders
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <Truck className="w-5 h-5" />
                  Fleet Management
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <Users className="w-5 h-5" />
                  Drivers
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <Layers className="w-5 h-5" />
                  Inventory
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <BarChart3 className="w-5 h-5" />
                  Report & Analytics
                </button>
                <button className="w-full flex items-center gap-3 px-3 py-2.5 text-slate-500 hover:bg-slate-50 hover:text-slate-900 rounded-xl font-medium text-sm transition-colors">
                  <CreditCard className="w-5 h-5" />
                  Billing & Payments
                </button>
              </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex flex-col bg-[#FAFAFA] overflow-hidden">
              {/* Top Nav */}
              <div className="h-20 px-8 flex items-center justify-between bg-white border-b border-slate-100 shrink-0">
                <h1 className="text-xl font-bold text-slate-900">Overview</h1>
                
                <div className="flex items-center gap-4">
                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input 
                      type="text" 
                      placeholder="Search" 
                      className="pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-64 shadow-sm"
                      readOnly
                    />
                  </div>
                  <div className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 shadow-sm">
                    <Calendar className="w-4 h-4 text-slate-400" />
                    November 2024
                  </div>
                  <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-xl text-sm font-medium hover:bg-blue-700 shadow-sm shadow-blue-600/20">
                    <Plus className="w-4 h-4" />
                    Add Shipment
                  </button>
                </div>
              </div>

              {/* Dashboard Content Scrollable */}
              <div className="flex-1 overflow-y-auto p-8">
                {/* 4 Stat Cards */}
                <div className="grid grid-cols-4 gap-6 mb-6">
                  {/* Card 1 */}
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="w-10 h-10 rounded-xl bg-red-50 flex items-center justify-center mb-4">
                      <Ship className="w-5 h-5 text-red-500" />
                    </div>
                    <div className="text-sm font-medium text-slate-500 mb-1">Total Shipments</div>
                    <div className="flex items-end gap-2">
                      <span className="text-2xl font-bold text-slate-900">6,524</span>
                      <span className="flex items-center text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100/50 mb-1">
                        <ArrowUpRight className="w-3 h-3 mr-0.5" /> 1.3%
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">vs Last Month</div>
                  </div>
                  {/* Card 2 */}
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center mb-4">
                      <Box className="w-5 h-5 text-emerald-500" />
                    </div>
                    <div className="text-sm font-medium text-slate-500 mb-1">Total Order</div>
                    <div className="flex items-end gap-2">
                      <span className="text-2xl font-bold text-slate-900">25,342</span>
                      <span className="flex items-center text-xs font-medium text-red-600 bg-red-50 px-1.5 py-0.5 rounded border border-red-100/50 mb-1">
                        <ArrowDownRight className="w-3 h-3 mr-0.5" /> 2.1%
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">vs Last Month</div>
                  </div>
                  {/* Card 3 */}
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center mb-4">
                      <CreditCard className="w-5 h-5 text-blue-500" />
                    </div>
                    <div className="text-sm font-medium text-slate-500 mb-1">Revenue</div>
                    <div className="flex items-end gap-2">
                      <span className="text-2xl font-bold text-slate-900">₹2,14,535</span>
                      <span className="flex items-center text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100/50 mb-1">
                        <ArrowUpRight className="w-3 h-3 mr-0.5" /> 1.3%
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">vs Last Month</div>
                  </div>
                  {/* Card 4 */}
                  <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center mb-4">
                      <Truck className="w-5 h-5 text-amber-500" />
                    </div>
                    <div className="text-sm font-medium text-slate-500 mb-1">Delivered</div>
                    <div className="flex items-end gap-2">
                      <span className="text-2xl font-bold text-slate-900">1,568</span>
                      <span className="flex items-center text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100/50 mb-1">
                        <ArrowUpRight className="w-3 h-3 mr-0.5" /> 4.3%
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 mt-1">vs Last Month</div>
                  </div>
                </div>

                {/* Charts Row */}
                <div className="grid grid-cols-3 gap-6 mb-6">
                  {/* Line Chart */}
                  <div className="col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="font-bold text-slate-900">Shipment Analytics</h3>
                      <div className="flex items-center gap-2 px-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer">
                        <Calendar className="w-4 h-4" />
                        Monthly
                        <ChevronDown className="w-4 h-4 ml-1" />
                      </div>
                    </div>
                    <div className="flex gap-6 mb-8">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">Total Delivery:</span>
                        <span className="font-bold text-slate-900">343,245</span>
                        <span className="flex items-center text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                          <ArrowUpRight className="w-3 h-3 mr-0.5" /> 1.3%
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">On Delivery:</span>
                        <span className="font-bold text-slate-900">2,162</span>
                        <span className="flex items-center text-xs font-medium text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded">
                          <ArrowUpRight className="w-3 h-3 mr-0.5" /> 4.25%
                        </span>
                      </div>
                    </div>
                    {/* SVG Line Chart Mockup */}
                    <div className="h-48 w-full relative">
                      {/* Grid lines */}
                      <div className="absolute inset-0 flex flex-col justify-between">
                        {[4000, 3000, 2000, 1000, 500, 100, 0].map((val, i) => (
                          <div key={i} className="flex items-center w-full">
                            <span className="text-[10px] text-slate-400 w-8 text-right mr-4">{val}</span>
                            <div className="flex-1 border-b border-slate-100 border-dashed"></div>
                          </div>
                        ))}
                      </div>
                      {/* Lines */}
                      <svg className="absolute inset-0 w-full h-full pl-12 pt-2" preserveAspectRatio="none" viewBox="0 0 100 100">
                        {/* Dashed Line */}
                        <path d="M 0 60 Q 15 70, 25 80 T 50 60 T 75 60 T 100 50" fill="none" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="4 4" />
                        {/* Solid Line */}
                        <path d="M 0 80 Q 15 90, 25 85 T 45 50 T 65 70 T 85 60 T 100 40" fill="none" stroke="#2563eb" strokeWidth="2" />
                        
                        {/* Tooltip point */}
                        <circle cx="45" cy="50" r="3" fill="white" stroke="#2563eb" strokeWidth="2" />
                      </svg>
                      {/* Tooltip */}
                      <div className="absolute top-10 left-[40%] bg-white border border-slate-200 shadow-lg rounded-lg p-3 text-xs z-10">
                        <div className="flex items-center gap-2 mb-1">
                          <div className="w-1.5 h-1.5 rounded-full bg-slate-400"></div>
                          <span className="text-slate-500">Delivery:</span>
                          <span className="font-semibold text-slate-900">120</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 rounded-full bg-blue-600"></div>
                          <span className="text-slate-500">On Delivery:</span>
                          <span className="font-semibold text-slate-900">343</span>
                        </div>
                      </div>
                      {/* X Axis */}
                      <div className="absolute bottom-0 left-12 right-0 flex justify-between text-[10px] text-slate-400 translate-y-6">
                        <span>Nov 1</span><span>Nov 2</span><span>Nov 3</span><span>Nov 4</span><span>Nov 5</span><span>Nov 6</span><span>Nov 7</span><span>Nov 8</span><span>Nov 9</span>
                      </div>
                    </div>
                  </div>

                  {/* Bar Chart */}
                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="font-bold text-slate-900">Cashflow Stat</h3>
                      <button className="flex items-center gap-2 px-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50">
                        Export <Download className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="flex items-center gap-4 mb-8 text-xs">
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-4 rounded-full bg-blue-600"></div>
                        <span className="text-slate-500">Income</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <div className="w-1.5 h-4 rounded-full bg-blue-200"></div>
                        <span className="text-slate-500">Expense</span>
                      </div>
                    </div>
                    {/* Bar Chart Mockup */}
                    <div className="h-48 flex items-end justify-between gap-2">
                      {[
                        { in: 30, out: 10, label: 'Nov 1' },
                        { in: 50, out: 20, label: 'Nov 2' },
                        { in: 80, out: 30, label: 'Nov 3' },
                        { in: 60, out: 25, label: 'Nov 4' },
                        { in: 45, out: 15, label: 'Nov 5' },
                        { in: 35, out: 10, label: 'Nov 6' },
                        { in: 40, out: 12, label: 'Nov 7' },
                      ].map((col, i) => (
                        <div key={i} className="flex flex-col items-center flex-1 gap-2 h-full">
                          <div className="w-full flex flex-col justify-end items-center h-full gap-1">
                            <div className="w-3/4 bg-blue-200 rounded-t-sm" style={{ height: `${col.out}%` }}></div>
                            <div className="w-3/4 bg-blue-600 rounded-t-sm" style={{ height: `${col.in}%` }}></div>
                          </div>
                          <span className="text-[10px] text-slate-400">{col.label}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bottom Row */}
                <div className="grid grid-cols-3 gap-6">
                  <div className="col-span-2 bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-4 mb-4">
                      <div className="flex gap-6 text-sm">
                        <button className="font-semibold text-blue-600 border-b-2 border-blue-600 pb-4 -mb-4">Followed Shipment</button>
                        <button className="font-medium text-slate-500 hover:text-slate-900 pb-4 -mb-4">Delay Shipment</button>
                        <button className="font-medium text-slate-500 hover:text-slate-900 pb-4 -mb-4">Last update</button>
                      </div>
                      <div className="flex items-center gap-2 px-3 py-1.5 border border-slate-200 rounded-lg text-sm text-slate-600 cursor-pointer">
                        <Calendar className="w-4 h-4" />
                        Monthly
                        <ChevronDown className="w-4 h-4 ml-1" />
                      </div>
                    </div>
                    
                    {/* Shipment Item */}
                    <div className="border border-slate-200 rounded-xl p-4 flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-bold text-slate-900">DEMO-C548783</span>
                          <span className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-100/50">
                            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500"></div>
                            In Transit
                          </span>
                        </div>
                        <div className="flex items-center gap-4 text-xs text-slate-500">
                          <div className="flex items-center gap-1">
                            <MapPin className="w-3.5 h-3.5 text-slate-400" />
                            Clarksville, US - Centere, US
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-3.5 h-3.5 text-slate-400" />
                            ETA: Nov 15 - Dec 20
                          </div>
                        </div>
                      </div>
                      <div className="w-16 h-12 bg-slate-50 border border-slate-100 rounded-lg flex items-center justify-center">
                        <Truck className="w-6 h-6 text-slate-400" />
                      </div>
                    </div>
                  </div>

                  <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
                    <h3 className="font-bold text-slate-900 mb-4">Map view</h3>
                    <div className="flex-1 bg-[#F8FAFC] rounded-xl relative overflow-hidden min-h-[150px] border border-slate-200">
                      {/* Map background pattern */}
                      <div className="absolute inset-0 opacity-30" style={{ backgroundImage: 'radial-gradient(#cbd5e1 1px, transparent 1px)', backgroundSize: '12px 12px' }} />
                      {/* Route line */}
                      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                        <path d="M 20 80 L 40 60 L 60 70 L 80 30" fill="none" stroke="#3B82F6" strokeWidth="2" strokeDasharray="4 4" />
                        <circle cx="20" cy="80" r="4" fill="#10B981" />
                        <circle cx="80" cy="30" r="4" fill="#3B82F6" />
                        <circle cx="80" cy="30" r="8" fill="none" stroke="#3B82F6" strokeWidth="1" opacity="0.5" />
                      </svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Footer Text */}
        <div className="mt-12 text-center text-sm font-medium text-slate-500">
          Companies that trust Inviq to build what's next:
        </div>

        {/* Features Section (Combined Design) */}
        <div id="features" className="py-32 mt-16 border-t border-slate-200/60 relative overflow-hidden">
          {/* Background Pattern */}
          <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:20px_20px] opacity-30" />
          
          <div className="text-center max-w-3xl mx-auto mb-20 relative z-10">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-white border border-indigo-100 shadow-[0_2px_10px_rgba(99,102,241,0.08)] text-slate-700 text-sm font-medium mb-6">
              <Star className="w-4 h-4 mr-2 text-[#5B65FF]" />
              Features
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
              Smarter Inventory Intelligence
            </h2>
            <p className="text-lg text-slate-500 leading-relaxed max-w-2xl mx-auto">
              Track inventory in real time, predict demand, and automate restocking with AI-driven precision.
            </p>
          </div>

          <div className="max-w-6xl mx-auto relative px-4 sm:px-6 lg:px-8 z-10">
            {/* Connecting Lines (Desktop) */}
            <div className="hidden lg:block absolute top-[25%] bottom-[25%] left-12 w-12 border-l-2 border-t-2 border-b-2 border-indigo-100 rounded-l-3xl z-0" />
            <div className="hidden lg:block absolute top-1/2 left-0 w-12 h-[2px] bg-indigo-100 -translate-y-1/2 z-0" />

            <div className="hidden lg:block absolute top-[25%] bottom-[25%] right-12 w-12 border-r-2 border-t-2 border-b-2 border-indigo-100 rounded-r-3xl z-0" />
            <div className="hidden lg:block absolute top-1/2 right-0 w-12 h-[2px] bg-indigo-100 -translate-y-1/2 z-0" />
            
            {/* Left Icon Node */}
            <div className="hidden lg:flex absolute top-1/2 left-0 w-12 h-12 bg-[#5B65FF] rounded-full items-center justify-center text-white shadow-lg shadow-indigo-200 -translate-y-1/2 -translate-x-1/2 z-20 ring-4 ring-white">
              <Lock className="w-5 h-5" />
            </div>
            
            {/* Right Icon Node */}
            <div className="hidden lg:flex absolute top-1/2 right-0 w-12 h-12 bg-[#5B65FF] rounded-full items-center justify-center text-white shadow-lg shadow-indigo-200 -translate-y-1/2 translate-x-1/2 z-20 ring-4 ring-white">
              <Globe className="w-5 h-5" />
            </div>

            {/* 2x2 Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 lg:gap-10 relative z-10 lg:px-24">
              
              {/* Card 1 */}
              <div className="bg-white/90 backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_40px_rgba(99,102,241,0.08)] transition-all group">
                <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 text-[#5B65FF] group-hover:scale-110 transition-transform">
                  <Activity className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Live Inventory Monitoring</h3>
                <p className="text-slate-500 leading-relaxed">
                  Monitor inventory live across every channel and location instantly.
                </p>
              </div>

              {/* Card 2 */}
              <div className="bg-white/90 backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_40px_rgba(99,102,241,0.08)] transition-all group">
                <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 text-[#5B65FF] group-hover:scale-110 transition-transform">
                  <Zap className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Smart Auto-Restocking</h3>
                <p className="text-slate-500 leading-relaxed">
                  Automatically detect low stock and trigger instant restocking powered by AI.
                </p>
              </div>

              {/* Card 3 */}
              <div className="bg-white/90 backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_40px_rgba(99,102,241,0.08)] transition-all group">
                <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 text-[#5B65FF] group-hover:scale-110 transition-transform">
                  <Network className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Unified Channel Sync</h3>
                <p className="text-slate-500 leading-relaxed">
                  Connect and sync inventory across online stores, POS systems, and warehouses effortlessly.
                </p>
              </div>

              {/* Card 4 */}
              <div className="bg-white/90 backdrop-blur-xl rounded-[2rem] p-8 md:p-10 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] hover:shadow-[0_8px_40px_rgba(99,102,241,0.08)] transition-all group">
                <div className="w-12 h-12 bg-indigo-50 rounded-2xl flex items-center justify-center mb-6 text-[#5B65FF] group-hover:scale-110 transition-transform">
                  <LineChart className="w-6 h-6" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-3">Predictive Forecasting</h3>
                <p className="text-slate-500 leading-relaxed">
                  Anticipate demand with AI powered forecasting and advanced analytics.
                </p>
              </div>

            </div>
          </div>
        </div>

        {/* Process Section */}
        <div id="process" className="py-32 border-t border-slate-200/60 relative">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-white border border-indigo-100 shadow-[0_2px_10px_rgba(99,102,241,0.08)] text-slate-700 text-sm font-medium mb-6">
              <TrendingUp className="w-4 h-4 mr-2 text-[#5B65FF]" />
              Process
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
              Get Started in 3 Simple Steps
            </h2>
            <p className="text-lg text-slate-500 leading-relaxed max-w-2xl mx-auto">
              Sign up in minutes and start automating your entire inventory workflow fast.
            </p>
          </div>

          <div className="max-w-5xl mx-auto relative px-4">
            {/* Connecting Line */}
            <div className="hidden md:block absolute top-6 left-[16.66%] right-[16.66%] h-px bg-indigo-200 z-0" />

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
              {/* Step 1 */}
              <div className="flex flex-col items-center text-center">
                <div className="w-12 h-12 bg-[#5B65FF] text-white rounded-xl flex items-center justify-center text-xl font-bold mb-8 shadow-md">
                  1
                </div>
                <div className="bg-white rounded-3xl p-8 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] w-full h-full">
                  <h3 className="text-lg font-bold text-slate-900 mb-3">Create Account</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">
                    Create your account and instantly access your smart inventory dashboard.
                  </p>
                </div>
              </div>

              {/* Step 2 */}
              <div className="flex flex-col items-center text-center">
                <div className="w-12 h-12 bg-[#5B65FF] text-white rounded-xl flex items-center justify-center text-xl font-bold mb-8 shadow-md">
                  2
                </div>
                <div className="bg-white rounded-3xl p-8 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] w-full h-full">
                  <h3 className="text-lg font-bold text-slate-900 mb-3">Sync Your Inventory</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">
                    Add items, sync stock, and connect your existing systems in one place.
                  </p>
                </div>
              </div>

              {/* Step 3 */}
              <div className="flex flex-col items-center text-center">
                <div className="w-12 h-12 bg-[#5B65FF] text-white rounded-xl flex items-center justify-center text-xl font-bold mb-8 shadow-md">
                  3
                </div>
                <div className="bg-white rounded-3xl p-8 border border-slate-100 shadow-[0_8px_30px_rgba(0,0,0,0.04)] w-full h-full">
                  <h3 className="text-lg font-bold text-slate-900 mb-3">Launch Your Operations</h3>
                  <p className="text-sm text-slate-500 leading-relaxed">
                    Track orders, manage shipments, and streamline deliveries effortlessly.
                  </p>
                </div>
              </div>
            </div>

            {/* Blank YouTube Video Section */}
            <div className="mt-24 max-w-4xl mx-auto">
              <div className="aspect-video bg-slate-100 rounded-[2rem] border border-slate-200 shadow-inner flex items-center justify-center relative overflow-hidden group cursor-pointer">
                <div className="absolute inset-0 bg-slate-900/5 group-hover:bg-slate-900/10 transition-colors" />
                <div className="w-20 h-20 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                  <Play className="w-8 h-8 text-[#5B65FF] ml-1" fill="currentColor" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Pricing Section */}
        <div id="pricing" className="py-32 border-t border-slate-200/60">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <div className="inline-flex items-center justify-center px-4 py-1.5 rounded-full bg-cyan-50 text-cyan-500 text-xs font-semibold mb-6 relative">
              {/* Decorative lines */}
              <div className="absolute top-1/2 -left-4 w-4 h-px bg-cyan-100" />
              <div className="absolute top-1/2 -right-4 w-4 h-px bg-cyan-100" />
              Pricing Plans
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight">
              Flexible plans for every stage<br />of growth
            </h2>
            <p className="text-lg text-slate-500 leading-relaxed max-w-2xl mx-auto">
              Our flexible plans fit every growth stage. Scale up or down anytime, paying only for the features and support you need to succeed.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {/* Starter Plan */}
            <div className="flex flex-col">
              <div className="bg-gradient-to-b from-slate-50 to-slate-50/50 rounded-[2rem] p-8 mb-8 relative overflow-hidden border border-slate-100/50">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-slate-900">Starter</h3>
                  <span className="text-xs font-medium text-slate-500 bg-white px-3 py-1 rounded-full shadow-sm border border-slate-100">Small Teams</span>
                </div>
                <div className="mb-4">
                  <div className="text-sm text-slate-500 mb-1">Start at</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-slate-900">₹999</span>
                    <span className="text-slate-500 font-medium">/month</span>
                  </div>
                </div>
                <p className="text-sm text-slate-600 mb-8 leading-relaxed min-h-[40px]">
                  Small teams and startups just getting started with bookings and management.
                </p>
                <button className="w-full py-3.5 px-4 bg-[#1D4ED8] hover:bg-blue-700 text-white rounded-xl font-medium transition-colors shadow-sm">
                  Try for Free
                </button>
              </div>
              <div className="px-2">
                <ul className="space-y-4">
                  {[
                    'Manage up to 10 bookings per month',
                    'Add up to 5 team members',
                    'Basic customer management tools',
                    'Email & chat support',
                    'Access to dashboard analytics (limited)',
                    'File uploads & basic document storage',
                    'Mobile & desktop app access',
                    'Integration with Google Calendar'
                  ].map((feature, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-600">
                      <Check className="w-4 h-4 text-slate-800 shrink-0 mt-0.5" strokeWidth={1.5} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Professional Plan */}
            <div className="flex flex-col">
              <div className="bg-gradient-to-b from-[#F0F9FF] to-[#F0F9FF]/50 rounded-[2rem] p-8 mb-8 relative overflow-hidden border border-blue-100/50">
                {/* Dot pattern background */}
                <div className="absolute inset-0 opacity-[0.15]" style={{ backgroundImage: 'radial-gradient(#3B82F6 1px, transparent 1px)', backgroundSize: '12px 12px' }} />
                
                <div className="relative z-10">
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="text-2xl font-bold text-slate-900">Professional</h3>
                    <span className="text-xs font-medium text-slate-500 bg-white px-3 py-1 rounded-full shadow-sm border border-slate-100">Growing Businesses</span>
                  </div>
                  <div className="mb-4">
                    <div className="text-sm text-slate-500 mb-1">Start at</div>
                    <div className="flex items-baseline gap-1">
                      <span className="text-5xl font-bold text-slate-900">₹2999</span>
                      <span className="text-slate-500 font-medium">/month</span>
                    </div>
                  </div>
                  <p className="text-sm text-slate-600 mb-8 leading-relaxed min-h-[40px]">
                    Large organizations managing multiple departments, locations, or service lines.
                  </p>
                  <button className="w-full py-3.5 px-4 bg-[#1D4ED8] hover:bg-blue-700 text-white rounded-xl font-medium transition-colors shadow-sm">
                    Contact Sales
                  </button>
                </div>
              </div>
              <div className="px-2">
                <ul className="space-y-4">
                  {[
                    'Unlimited bookings and customers',
                    'Add up to 25 team members',
                    'Automated reminders (Email & WhatsApp)',
                    'Reports & analytics dashboard',
                    'Multi-branch management',
                    'Advanced inventory tracking & low-stock alerts',
                    'Role-based access control',
                    'Priority email & chat support'
                  ].map((feature, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-600">
                      <Check className="w-4 h-4 text-slate-800 shrink-0 mt-0.5" strokeWidth={1.5} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Enterprise Plan */}
            <div className="flex flex-col">
              <div className="bg-gradient-to-b from-slate-50 to-slate-50/50 rounded-[2rem] p-8 mb-8 relative overflow-hidden border border-slate-100/50">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-slate-900">Enterprise</h3>
                  <span className="text-xs font-medium text-slate-500 bg-white px-3 py-1 rounded-full shadow-sm border border-slate-100">Large organizations</span>
                </div>
                <div className="mb-4">
                  <div className="text-sm text-slate-500 mb-1">Start at</div>
                  <div className="flex items-baseline gap-1">
                    <span className="text-5xl font-bold text-slate-900">₹5999</span>
                    <span className="text-slate-500 font-medium">/month</span>
                  </div>
                </div>
                <p className="text-sm text-slate-600 mb-8 leading-relaxed min-h-[40px]">
                  Small teams and startups just getting started with bookings and management.
                </p>
                <button className="w-full py-3.5 px-4 bg-[#1D4ED8] hover:bg-blue-700 text-white rounded-xl font-medium transition-colors shadow-sm">
                  Try for Free
                </button>
              </div>
              <div className="px-2">
                <ul className="space-y-4">
                  {[
                    'Custom user limits & branch setup',
                    'Dedicated account manager',
                    'White-label portal & custom branding',
                    'Custom integrations (ERP, CRM, or HR systems)',
                    'API access & developer tools',
                    'Advanced automation workflows',
                    '24/7 dedicated support',
                    'Onboarding & staff training'
                  ].map((feature, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm text-slate-600">
                      <Check className="w-4 h-4 text-slate-800 shrink-0 mt-0.5" strokeWidth={1.5} />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        </div>

        {/* Customers Section */}
        <div id="customers" className="py-32 border-t border-slate-200/60 relative bg-white">
          {/* Vertical lines matching the design */}
          <div className="hidden md:block absolute top-0 bottom-0 left-[10%] w-px bg-indigo-100/50" />
          <div className="hidden md:block absolute top-0 bottom-0 right-[10%] w-px bg-indigo-100/50" />

          <div className="text-center max-w-3xl mx-auto mb-12 relative z-10">
            <h2 className="text-4xl md:text-5xl font-medium text-slate-900 mb-4 tracking-tight">
              Hear From <span className="text-[#3B82F6]">Our Customers</span>
            </h2>
            <p className="text-[15px] text-slate-400 leading-relaxed max-w-xl mx-auto">
              Smarter inventory. Real impact. See how Inviq boosts<br className="hidden md:block" />efficiency and eliminates stock issues.
            </p>
          </div>

          <div className="max-w-2xl mx-auto relative z-10 px-4">
            <div className="bg-[#F8F9FF] rounded-2xl p-10 md:p-12 border border-indigo-100/60 mb-10 transition-all duration-300">
              <p className="text-slate-600 text-[15px] text-center leading-relaxed mb-8">
                "{testimonials[currentTestimonial].quote}"
              </p>
              <div className="flex items-center justify-center gap-4">
                <img src={testimonials[currentTestimonial].image} alt={testimonials[currentTestimonial].name} className="w-12 h-12 rounded-full object-cover shadow-sm" />
                <div className="text-left">
                  <div className="font-semibold text-slate-900 text-sm">{testimonials[currentTestimonial].name}</div>
                  <div className="text-sm text-slate-500">{testimonials[currentTestimonial].role}</div>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-center gap-4">
              <button 
                onClick={prevTestimonial}
                className="w-10 h-10 flex items-center justify-center rounded-xl border border-indigo-100 bg-white text-[#3B82F6] hover:bg-indigo-50 transition-all shadow-[0_2px_10px_rgba(99,102,241,0.05)]"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <button 
                onClick={nextTestimonial}
                className="w-10 h-10 flex items-center justify-center rounded-xl border border-indigo-100 bg-white text-[#3B82F6] hover:bg-indigo-50 transition-all shadow-[0_2px_10px_rgba(99,102,241,0.05)]"
              >
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* FAQ Section */}
      <div id="faq" className="py-24 relative bg-white border-t border-slate-200/60 overflow-hidden z-10">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:20px_20px] opacity-30" />
        <div className="absolute top-0 left-0 right-0 h-32 bg-gradient-to-b from-white to-transparent z-10" />
        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-white to-transparent z-10" />
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-96 h-96 bg-blue-50 rounded-full blur-3xl opacity-50 z-0" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-20">
          <div className="flex flex-col lg:flex-row gap-16 lg:gap-24">
            {/* Left Column */}
            <div className="lg:w-1/3 flex flex-col items-start">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white border border-slate-200 shadow-sm text-slate-700 text-sm font-medium mb-6">
                <HelpCircle className="w-4 h-4 text-[#5B65FF]" />
                FAQs
              </div>
              <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6 tracking-tight leading-tight">
                Frequently asked<br />question
              </h2>
              <p className="text-slate-500 mb-8 leading-relaxed">
                Some answers to common question we get asked. Feel free to reach out if you have any inquiries:
              </p>
              <button className="px-6 py-3 bg-[#5B65FF] text-white font-medium rounded-xl hover:bg-blue-600 transition-colors shadow-sm">
                Get started
              </button>
            </div>

            {/* Right Column */}
            <div className="lg:w-2/3 flex flex-col gap-4">
              {faqs.map((faq, index) => (
                <div 
                  key={index}
                  className="bg-white rounded-2xl border border-slate-100 shadow-[0_4px_20px_rgba(0,0,0,0.03)] overflow-hidden transition-all duration-300"
                >
                  <button 
                    onClick={() => setOpenFaq(openFaq === index ? -1 : index)}
                    className="w-full px-6 py-5 flex items-center justify-between text-left"
                  >
                    <span className="font-semibold text-slate-900 pr-8">{faq.question}</span>
                    {openFaq === index ? (
                      <ArrowDownRight className="w-5 h-5 text-[#5B65FF] flex-shrink-0" />
                    ) : (
                      <ArrowUpRight className="w-5 h-5 text-[#5B65FF] flex-shrink-0" />
                    )}
                  </button>
                  
                  <div 
                    className={`px-6 overflow-hidden transition-all duration-300 ease-in-out ${
                      openFaq === index ? 'max-h-48 pb-6 opacity-100' : 'max-h-0 opacity-0'
                    }`}
                  >
                    <div className="w-full h-px bg-slate-100 mb-4" />
                    <p className="text-slate-500 text-sm leading-relaxed">
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
        {/* Blue CTA Banner */}
        <div className="bg-[#5B65FF] text-white relative overflow-hidden">
          {/* Decorative shapes */}
          <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
          <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-white/10 rounded-full blur-2xl translate-y-1/3" />
          <div className="absolute top-1/2 left-0 w-80 h-80 bg-white/10 rounded-full blur-3xl -translate-x-1/2" />
          
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20 md:py-24 relative z-10">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-10">
              <div className="max-w-xl">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white text-slate-900 text-sm font-medium mb-6 shadow-sm">
                  <Phone className="w-4 h-4 text-blue-600" />
                  Contact
                </div>
                <h2 className="text-4xl md:text-5xl font-bold mb-4 leading-tight">
                  Expand Your Reach with<br />Brand's Smart Platform
                </h2>
                <p className="text-blue-100 text-lg">
                  Manage inventory, streamline operations, and scale your business anywhere in the world.
                </p>
              </div>
              
              <div className="w-full lg:w-auto flex flex-col sm:flex-row gap-3">
                <input 
                  type="email" 
                  placeholder="Enter your email" 
                  className="px-6 py-4 rounded-xl text-slate-900 w-full sm:w-80 focus:outline-none focus:ring-2 focus:ring-white/50 shadow-sm"
                />
                <button className="px-8 py-4 bg-white text-[#5B65FF] font-semibold rounded-xl hover:bg-blue-50 transition-colors shadow-sm whitespace-nowrap">
                  Contact Us
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Links */}
        <footer className="bg-white pt-20 pb-10 border-t border-slate-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-12 mb-16">
              <div className="lg:col-span-2">
                <div className="flex items-center gap-2 mb-6">
                  <LogoIcon />
                  <span className="font-semibold text-xl tracking-tight text-slate-900">Inviq</span>
                </div>
                <p className="text-slate-500 leading-relaxed max-w-sm">
                  We're here to help businesses evolve through tailored development, smart systems, and lasting impact.
                </p>
              </div>
              
              <div>
                <h4 className="font-semibold text-slate-900 mb-6">Menu</h4>
                <ul className="space-y-4">
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Home</a></li>
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Features</a></li>
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Process</a></li>
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Pricing</a></li>
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Changelog</a></li>
                </ul>
              </div>

              <div>
                <h4 className="font-semibold text-slate-900 mb-6">Company</h4>
                <ul className="space-y-4">
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">About Us</a></li>
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Contact Us</a></li>
                </ul>
              </div>

              <div>
                <h4 className="font-semibold text-slate-900 mb-6">Other Pages</h4>
                <ul className="space-y-4">
                  <li><a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Customers</a></li>
                </ul>
              </div>
            </div>

            <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-slate-200 gap-4">
              <p className="text-slate-500 text-sm">
                © 2026 Inviq. All rights reserved.
              </p>
              <div className="flex items-center gap-6 text-sm">
                <a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Privacy Policy</a>
                <a href="#" className="text-slate-500 hover:text-slate-900 transition-colors">Term of Use</a>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
}

