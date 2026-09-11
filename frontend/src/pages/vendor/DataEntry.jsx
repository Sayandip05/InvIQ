/**
 * Stock Acquisition & Inbound Orders Page.
 *
 * Unified hub for all inbound inventory management:
 * 1. Upload Delivery Bills: Download Excel template, upload manifests (.xlsx / .csv), track batches, and download GST receipts.
 * 2. Branch Stock Orders: View and authorize internal stock replenishment requests from counters & branches.
 */

import React, { useState } from 'react';
import {
  Upload, Download, FileSpreadsheet, History, AlertCircle, CheckCircle,
  Loader2, Building2, Package, RefreshCw, X, FileText, Check, Search,
  ClipboardList, CheckCircle2, ChevronDown, ChevronUp, Clock, AlertTriangle
} from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';
import { useDeliveryUpload } from '@/features/inventory/hooks/useDeliveryUpload';
import { useRequisitions } from '@/features/requisitions/hooks/useRequisitions';

export default function DataEntry() {
  const [activeSubTab, setActiveSubTab] = useState('upload'); // 'upload' | 'requests'

  const {
    locations,
    selectedLocation,
    setSelectedLocation,
    file,
    uploads,
    invoices,
    loading,
    fetching,
    error,
    setError,
    success,
    setSuccess,
    dragOver,
    setDragOver,
    searchQuery,
    setSearchQuery,
    loadData,
    handleDownloadTemplate,
    handleDownloadInvoice,
    handleInputChange,
    handleDrop,
    handleUpload,
  } = useDeliveryUpload();

  const {
    stats: reqStats,
    filter: reqFilter,
    setFilter: setReqFilter,
    expandedId: reqExpandedId,
    setExpandedId: setReqExpandedId,
    approverName,
    setApproverName,
    actionLoading: reqActionLoading,
    handleApprove: handleApproveReq,
    handleReject: handleRejectReq,
    filteredRequests,
  } = useRequisitions();

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('en-IN', {
      dateStyle: 'medium',
      timeStyle: 'short',
    });
  };

  const totalRowsProcessed = uploads.reduce((acc, u) => acc + (u.rows_processed || 0), 0);
  const successUploadsCount = uploads.filter(u => u.status === 'completed' || u.status === 'success' || !u.status).length;
  const successRate = uploads.length > 0 ? Math.round((successUploadsCount / uploads.length) * 100) : 100;

  const filteredUploads = uploads.filter((u) => {
    const q = searchQuery.toLowerCase();
    const fname = (u.filename || '').toLowerCase();
    const loc = (u.location_name || '').toLowerCase();
    return fname.includes(q) || loc.includes(q);
  });

  return (
    <div className="flex flex-col min-h-full bg-background font-sans text-foreground">
      {/* ── Sticky Top Navbar ─── */}
      <div className="sticky top-0 z-30 bg-card border-b border-border px-6 py-3.5 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Stock Acquisition &amp; Orders</h2>
            <p className="text-xs text-muted-foreground font-medium mt-0.5">
              Upload supplier delivery bills or manage stock order requests from branch counters
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={loadData}
              className="p-2 bg-accent/50 hover:bg-accent text-foreground rounded-md transition-colors border border-border cursor-pointer"
              title="Refresh Data"
            >
              <RefreshCw size={13} className={fetching ? 'animate-spin' : ''} />
            </button>

            {activeSubTab === 'upload' && (
              <button
                onClick={handleDownloadTemplate}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-accent/50 hover:bg-accent text-foreground text-xs font-semibold rounded-md border border-border transition-colors cursor-pointer"
              >
                <Download size={14} className="text-[#F26A4B]" />
                <span>Excel Template</span>
              </button>
            )}

            {/* Notification Alerts Bell Dropdown */}
            <div className="pl-1 border-l border-border">
              <AlertsDropdown />
            </div>
          </div>
        </div>
      </div>

      {/* ── Page Content Container ─── */}
      <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">

        {/* ── Top Unified Sub-Tab Navigation ─── */}
        <div className="flex items-center gap-2 border-b border-border pb-3">
          <button
            type="button"
            onClick={() => setActiveSubTab('upload')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              activeSubTab === 'upload'
                ? 'bg-primary text-primary-foreground shadow-xs font-bold'
                : 'bg-card text-muted-foreground hover:text-foreground hover:bg-accent border border-border'
            }`}
          >
            <Upload size={14} />
            <span>Upload Delivery Bills</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveSubTab('requests')}
            className={`flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-md transition-colors cursor-pointer ${
              activeSubTab === 'requests'
                ? 'bg-primary text-primary-foreground shadow-xs font-bold'
                : 'bg-card text-muted-foreground hover:text-foreground hover:bg-accent border border-border'
            }`}
          >
            <ClipboardList size={14} />
            <span>Store Stock Orders &amp; Requests</span>
            {reqStats && reqStats.pending > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-[#F26A4B] text-white">
                {reqStats.pending}
              </span>
            )}
          </button>
        </div>

        {/* ── Notification Banners ─── */}
        {error && (
          <div className="p-4 text-xs font-medium border border-destructive/30 bg-destructive/10 text-destructive rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle size={16} className="text-destructive shrink-0" />
              <span>{error}</span>
            </div>
            <button onClick={() => setError('')} className="p-1 hover:opacity-75 cursor-pointer">
              <X size={14} />
            </button>
          </div>
        )}

        {success && (
          <div className="p-4 text-xs font-medium border border-border bg-accent/60 text-foreground rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-[#F26A4B] shrink-0" />
              <span>{success}</span>
            </div>
            <button onClick={() => setSuccess('')} className="p-1 hover:opacity-75 cursor-pointer">
              <X size={14} />
            </button>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 1: UPLOAD DELIVERY BILLS                                         */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {activeSubTab === 'upload' && (
          <div className="space-y-6">
            {/* Summary Statistics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-card border border-border p-4 rounded-xl shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Total Delivery Bills</span>
                  <FileSpreadsheet className="w-4 h-4 text-[#F26A4B]" />
                </div>
                <p className="text-2xl font-sans font-bold text-foreground mt-2">{uploads.length}</p>
                <p className="text-[11px] text-muted-foreground mt-1">Delivery batches submitted</p>
              </div>

              <div className="bg-card border border-border p-4 rounded-xl shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Stock Units Ingested</span>
                  <Package className="w-4 h-4 text-foreground" />
                </div>
                <p className="text-2xl font-sans font-bold text-foreground mt-2">{totalRowsProcessed.toLocaleString()}</p>
                <p className="text-[11px] text-muted-foreground font-medium mt-1">Auto-credited to inventory</p>
              </div>

              <div className="bg-card border border-border p-4 rounded-xl shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Success Rate</span>
                  <CheckCircle className="w-4 h-4 text-[#5E5A52]" />
                </div>
                <p className="text-2xl font-sans font-bold text-foreground mt-2">{successRate}%</p>
                <p className="text-[11px] text-muted-foreground mt-1">{successUploadsCount} successful uploads</p>
              </div>

              <div className="bg-card border border-border p-4 rounded-xl shadow-2xs">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Active Branches</span>
                  <Building2 className="w-4 h-4 text-foreground" />
                </div>
                <p className="text-2xl font-sans font-bold text-foreground mt-2">{locations.length}</p>
                <p className="text-[11px] text-muted-foreground mt-1">Ready for stock intake</p>
              </div>
            </div>

            {/* 2-Column Upload Form + History */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Upload Form */}
              <div className="lg:col-span-5 bg-card border border-border p-5 rounded-xl space-y-5 shadow-2xs">
                <div className="flex items-center justify-between pb-3 border-b border-border">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-accent text-[#F26A4B] rounded-md border border-border">
                      <Upload size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-sans font-bold text-foreground">Upload Delivery Bill</h3>
                      <p className="text-[11px] text-muted-foreground">Ingest supplier bills directly into branch stock</p>
                    </div>
                  </div>
                </div>

                {/* Template Download Prompt */}
                <div className="bg-accent/30 border border-border rounded-lg p-3.5 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold text-foreground">Need the standard template?</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">Use our template with Item Name, Batch, and Qty columns.</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleDownloadTemplate}
                    className="shrink-0 flex items-center gap-1 text-xs font-semibold text-foreground bg-card border border-border px-2.5 py-1.5 rounded-md hover:bg-accent transition-colors cursor-pointer"
                  >
                    <Download size={12} className="text-[#F26A4B]" />
                    <span>Template</span>
                  </button>
                </div>

                <form onSubmit={handleUpload} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                      Receiving Branch / Store <span className="text-destructive">*</span>
                    </label>
                    <div className="relative flex items-center">
                      <Building2 size={14} className="absolute left-3 text-muted-foreground pointer-events-none" />
                      <select
                        value={selectedLocation}
                        onChange={(e) => setSelectedLocation(e.target.value)}
                        className="w-full text-xs font-medium bg-background border border-border text-foreground rounded-md pl-9 pr-8 py-2.5 hover:bg-accent/30 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
                      >
                        <option value="">Select Destination Branch...</option>
                        {locations.map((loc) => (
                          <option key={loc.id} value={loc.id}>
                            {loc.name} {loc.type ? `(${loc.type})` : ''}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                      Delivery Bill File <span className="text-destructive">*</span>
                    </label>
                    <input
                      id="file-upload"
                      type="file"
                      accept=".xlsx,.xls,.csv"
                      onChange={handleInputChange}
                      className="hidden"
                    />
                    <label
                      htmlFor="file-upload"
                      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                      onDragLeave={() => setDragOver(false)}
                      onDrop={handleDrop}
                      className={`flex flex-col items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                        dragOver
                          ? 'border-[#F26A4B] bg-[#F26A4B]/10'
                          : file
                          ? 'border-primary bg-accent/40'
                          : 'border-border hover:border-foreground/40 bg-accent/20 hover:bg-accent/40'
                      }`}
                    >
                      {file ? (
                        <>
                          <div className="p-2 bg-card text-foreground border border-border rounded-full mb-2">
                            <Check size={18} strokeWidth={2.5} />
                          </div>
                          <p className="text-xs font-bold text-foreground text-center truncate max-w-xs">{file.name}</p>
                          <p className="text-[11px] text-muted-foreground mt-0.5">
                            {(file.size / 1024).toFixed(1)} KB · Click or drop to replace
                          </p>
                        </>
                      ) : (
                        <>
                          <div className="p-2.5 bg-card text-muted-foreground border border-border rounded-full mb-2">
                            <Upload size={18} />
                          </div>
                          <p className="text-xs font-medium text-foreground">
                            Drop Excel/CSV bill here, or <span className="text-[#F26A4B] font-bold">browse</span>
                          </p>
                          <p className="text-[11px] text-muted-foreground mt-1">Supports .xlsx, .xls, .csv · Max 10MB</p>
                        </>
                      )}
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={loading || !file || !selectedLocation}
                    className="w-full flex items-center justify-center gap-2 py-2.5 bg-primary hover:bg-black disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed text-primary-foreground text-xs font-semibold rounded-md transition-colors shadow-2xs cursor-pointer"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Processing &amp; Updating Stock...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5" />
                        <span>Confirm &amp; Ingest Stock</span>
                      </>
                    )}
                  </button>
                </form>
              </div>

              {/* Right Column: History */}
              <div className="lg:col-span-7 bg-card border border-border p-5 rounded-xl space-y-4 shadow-2xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-accent text-foreground rounded-md border border-border">
                      <History size={16} />
                    </div>
                    <div>
                      <h3 className="text-sm font-sans font-bold text-foreground">Recent Ingest History</h3>
                      <p className="text-[11px] text-muted-foreground">{uploads.length} total deliveries processed</p>
                    </div>
                  </div>

                  <div className="relative w-full sm:w-56">
                    <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Filter by file or branch..."
                      className="w-full text-xs bg-background border border-border text-foreground placeholder:text-muted-foreground rounded-md pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                </div>

                {fetching ? (
                  <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
                    <Loader2 size={20} className="animate-spin text-[#F26A4B]" />
                    <span className="text-xs">Loading acquisition history...</span>
                  </div>
                ) : filteredUploads.length === 0 ? (
                  <div className="py-16 text-center flex flex-col items-center justify-center border border-dashed border-border rounded-xl p-6">
                    <FileSpreadsheet className="w-10 h-10 text-muted-foreground/50 mb-2" />
                    <h4 className="text-xs font-bold text-foreground">No Delivery Bills Found</h4>
                    <p className="text-[11px] text-muted-foreground mt-0.5 max-w-xs">
                      Upload an Excel or CSV bill on the left to start auto-ingesting stock into your branches.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto border border-border rounded-lg">
                    <table className="w-full text-left border-collapse">
                      <thead>
                        <tr className="bg-accent/40 border-b border-border text-[11px] font-bold text-foreground uppercase tracking-wider">
                          <th className="py-2.5 px-3">File Name</th>
                          <th className="py-2.5 px-3">Branch</th>
                          <th className="py-2.5 px-3 text-center">Status</th>
                          <th className="py-2.5 px-3 text-right">Units</th>
                          <th className="py-2.5 px-3">Date</th>
                          <th className="py-2.5 px-3 text-center">Receipt PDF</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border/50 text-xs">
                        {filteredUploads.map((upload, idx) => {
                          const matchedInvoice = invoices.find(inv => inv.vendor_upload_id === upload.id);
                          return (
                            <tr key={upload.id || idx} className="hover:bg-accent/20 transition-colors">
                              <td className="py-3 px-3 font-medium text-foreground max-w-[140px] truncate" title={upload.filename}>
                                <div className="flex items-center gap-1.5">
                                  <FileSpreadsheet size={13} className="text-[#F26A4B] shrink-0" />
                                  <span className="truncate">{upload.filename || 'Delivery Bill'}</span>
                                </div>
                              </td>
                              <td className="py-3 px-3 text-muted-foreground">
                                {upload.location_name || `Branch #${upload.location_id}`}
                              </td>
                              <td className="py-3 px-3 text-center">
                                <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                                  upload.status === 'failed'
                                    ? 'bg-destructive/10 text-destructive border-destructive/30'
                                    : upload.status === 'partial'
                                    ? 'bg-amber-500/10 text-amber-700 border-amber-500/30'
                                    : 'bg-accent text-foreground border-border'
                                }`}>
                                  {upload.status || 'COMPLETED'}
                                </span>
                              </td>
                              <td className="py-3 px-3 text-right font-mono font-semibold text-foreground">
                                {upload.rows_processed != null ? upload.rows_processed : '—'}
                              </td>
                              <td className="py-3 px-3 text-[11px] text-muted-foreground whitespace-nowrap">
                                {formatDate(upload.created_at)}
                              </td>
                              <td className="py-3 px-3 text-center">
                                {matchedInvoice ? (
                                  <button
                                    onClick={() => handleDownloadInvoice(matchedInvoice.id, matchedInvoice.invoice_number)}
                                    className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#F26A4B] hover:underline cursor-pointer"
                                    title="Download Delivery Receipt PDF"
                                  >
                                    <FileText size={12} />
                                    <span>PDF</span>
                                  </button>
                                ) : (
                                  <span className="text-[11px] text-muted-foreground/50">—</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 2: BRANCH STOCK ORDERS & REQUESTS (MERGED REQUISITION FEATURE)     */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {activeSubTab === 'requests' && (
          <div className="space-y-5">
            {/* Approver config and quick stats */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-card p-4 rounded-xl border border-border shadow-xs">
              <div>
                <h3 className="text-sm font-sans font-bold text-foreground">Branch Stock Orders</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Authorize stock order requests created by store staff</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-foreground">Approver Name:</span>
                <input
                  type="text"
                  placeholder="Store Admin"
                  className="px-2.5 py-1.5 border border-input rounded-md text-xs bg-background text-foreground focus:outline-none focus:ring-1 focus:ring-primary w-32"
                  value={approverName}
                  onChange={(e) => setApproverName(e.target.value)}
                />
              </div>
            </div>

            {/* Quick status filter pills */}
            <div className="flex gap-1.5 bg-card rounded-lg p-1 border border-border overflow-x-auto">
              {['', 'PENDING', 'APPROVED', 'REJECTED'].map((s) => (
                <button
                  key={s}
                  onClick={() => setReqFilter(s)}
                  className={`flex-1 min-w-[70px] py-1.5 rounded-md text-xs font-semibold transition cursor-pointer ${
                    reqFilter === s
                      ? 'bg-primary text-primary-foreground shadow-2xs'
                      : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                  }`}
                >
                  {s || 'ALL'}
                </button>
              ))}
            </div>

            {/* Orders list */}
            <div className="space-y-3">
              {filteredRequests.length === 0 ? (
                <div className="bg-card border border-dashed border-border rounded-xl p-12 text-center text-muted-foreground">
                  <ClipboardList size={36} className="mx-auto mb-2 text-muted-foreground/60" />
                  <p className="text-sm font-semibold text-foreground">No stock orders found</p>
                  <p className="text-xs text-muted-foreground mt-1">Staff stock orders and reorder requests will appear here for intake.</p>
                </div>
              ) : (
                filteredRequests.map((req) => {
                  const isExpanded = reqExpandedId === req.id;
                  return (
                    <div
                      key={req.id}
                      className={`bg-card rounded-xl border transition shadow-xs ${
                        req.urgency === 'EMERGENCY' && req.status === 'PENDING'
                          ? 'border-[#F26A4B] ring-1 ring-[#F26A4B]/20'
                          : 'border-border'
                      }`}
                    >
                      <button
                        onClick={() => setReqExpandedId(isExpanded ? null : req.id)}
                        className="w-full p-4 flex items-center justify-between text-left cursor-pointer"
                      >
                        <div className="flex items-center gap-3 flex-wrap">
                          <span className="font-mono text-xs font-bold text-foreground bg-accent px-2 py-0.5 rounded-md border border-border">
                            {req.requisition_number}
                          </span>
                          <span className="text-sm font-bold text-foreground">{req.destination_location}</span>
                          <span className="text-xs text-muted-foreground">
                            Requested by: <strong className="text-foreground">{req.requested_by}</strong> ({req.department})
                          </span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md font-mono border ${
                            req.status === 'APPROVED'
                              ? 'bg-accent text-foreground border-border'
                              : req.status === 'REJECTED'
                              ? 'bg-destructive/10 text-destructive border-destructive/20'
                              : 'bg-amber-500/10 text-amber-700 border-amber-500/30'
                          }`}>
                            {req.status}
                          </span>
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>
                      </button>

                      {isExpanded && (
                        <div className="p-4 border-t border-border bg-accent/20 rounded-b-xl space-y-3">
                          <div className="text-xs text-muted-foreground">
                            Date: <span className="font-mono text-foreground">{formatDate(req.created_at)}</span>
                            {req.notes && <p className="mt-1">Notes: {req.notes}</p>}
                          </div>
                          {req.items && req.items.length > 0 && (
                            <div className="border border-border rounded-md overflow-hidden bg-card">
                              <table className="w-full text-xs">
                                <thead className="bg-accent/40 font-semibold border-b border-border">
                                  <tr>
                                    <th className="py-2 px-3 text-left">Item Name</th>
                                    <th className="py-2 px-3 text-right">Quantity</th>
                                    <th className="py-2 px-3 text-left">Unit</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                  {req.items.map((it, i) => (
                                    <tr key={i}>
                                      <td className="py-2 px-3 font-medium text-foreground">{it.item_name}</td>
                                      <td className="py-2 px-3 text-right font-mono font-bold">{it.quantity}</td>
                                      <td className="py-2 px-3 text-muted-foreground">{it.packaging_unit || 'Units'}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                          {req.status === 'PENDING' && (
                            <div className="flex items-center justify-end gap-2 pt-2">
                              <button
                                onClick={() => handleRejectReq(req.id, 'Declined by store manager')}
                                disabled={reqActionLoading === req.id}
                                className="px-3 py-1.5 text-xs font-semibold text-destructive bg-destructive/10 hover:bg-destructive/20 border border-destructive/20 rounded-md transition-colors cursor-pointer"
                              >
                                Decline Order
                              </button>
                              <button
                                onClick={() => handleApproveReq(req.id)}
                                disabled={reqActionLoading === req.id}
                                className="px-3 py-1.5 text-xs font-semibold text-primary-foreground bg-primary hover:bg-black rounded-md transition-colors shadow-xs cursor-pointer"
                              >
                                {reqActionLoading === req.id ? 'Approving...' : 'Approve & Prepare Ingest'}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
