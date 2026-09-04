/**
 * Stock Acquisition & Delivery Ingest Page.
 *
 * Allows Admins, Superadmins, and Medicine Distributors to:
 * - Download standardized Excel delivery template (.xlsx)
 * - Upload medicine delivery manifests with automated batch mapping
 * - Track ingestion status across branches with real-time feedback
 * - Download generated official GST delivery invoices & receipts
 */

import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import {
  Upload, Download, FileSpreadsheet, History, AlertCircle, CheckCircle,
  Loader2, Building2, Package, RefreshCw, X, FileText, Check, Search, ArrowUpRight
} from 'lucide-react';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

export default function DataEntry() {
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [file, setFile] = useState(null);
  const [uploads, setUploads] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setFetching(true);
    try {
      await Promise.all([
        fetchLocations(),
        fetchUploadHistory(),
        fetchInvoices(),
      ]);
    } finally {
      setFetching(false);
    }
  };

  const fetchLocations = async () => {
    try {
      const response = await api.get('/inventory/locations');
      const locs = response.data?.data || [];
      setLocations(locs);
      if (locs.length > 0 && !selectedLocation) {
        setSelectedLocation(locs[0].id);
      }
    } catch (err) {
      console.error('Failed to fetch locations:', err);
    }
  };

  const fetchUploadHistory = async () => {
    try {
      const response = await api.get('/vendor/my-uploads');
      setUploads(response.data?.data || []);
    } catch (err) {
      console.error('Failed to fetch upload history:', err);
    }
  };

  const fetchInvoices = async () => {
    try {
      const response = await api.get('/vendor/invoices');
      setInvoices(response.data?.data?.invoices || response.data?.data || []);
    } catch (err) {
      // Invoices endpoint optional
      setInvoices([]);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/vendor/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'InvIQ_Medicine_Delivery_Template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download template. Please try again.');
    }
  };

  const handleDownloadInvoice = async (invoiceId, invoiceNumber) => {
    try {
      const response = await api.get(`/vendor/invoices/${invoiceId}/pdf`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Invoice_${invoiceNumber || invoiceId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download invoice PDF.');
    }
  };

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls') && !selectedFile.name.endsWith('.csv')) {
      setError('Only .xlsx, .xls, or .csv files are accepted');
      setFile(null);
      return;
    }
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size must be under 10MB');
      setFile(null);
      return;
    }
    setFile(selectedFile);
    setError('');
    setSuccess('');
  };

  const handleInputChange = (e) => handleFileChange(e.target.files[0]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFileChange(e.dataTransfer.files[0]);
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!selectedLocation) {
      setError('Please select a target pharmacy branch');
      return;
    }
    if (!file) {
      setError('Please select an Excel or CSV delivery file');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await api.post(`/vendor/upload-delivery?location_id=${selectedLocation}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const processedCount = res.data?.data?.rows_processed ?? res.data?.rows_processed ?? 'all';
      setSuccess(`Delivery manifest uploaded successfully! ${processedCount} medicine items ingested into inventory.`);
      setFile(null);
      const fileInput = document.getElementById('file-upload');
      if (fileInput) fileInput.value = '';
      fetchUploadHistory();
      fetchInvoices();
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Upload failed. Please check file format.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

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
    <div className="flex flex-col min-h-full bg-background">
      {/* ── Sticky Top Navbar (Identical to Inventory / Suppliers Layout) ─── */}
      <div className="sticky top-0 z-30 bg-card border-b border-border px-6 py-3.5 shadow-2xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">Stock Acquisition &amp; Ingest</h2>
            <p className="text-xs text-muted-foreground font-medium mt-0.5">
              Upload medicine delivery manifests (.xlsx / .csv) to auto-update branch stock
            </p>
          </div>

          <div className="flex items-center gap-2.5 flex-wrap">
            <button
              onClick={loadData}
              className="p-2 bg-accent/50 hover:bg-accent text-foreground rounded-none transition-colors border border-border cursor-pointer"
              title="Refresh Data"
            >
              <RefreshCw size={13} className={fetching ? 'animate-spin' : ''} />
            </button>

            <button
              onClick={handleDownloadTemplate}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-accent/50 hover:bg-accent text-foreground text-xs font-semibold rounded-none border border-border transition-colors cursor-pointer"
            >
              <Download size={14} className="text-[#F26A4B]" />
              <span>Excel Template</span>
            </button>

            {/* Notification Alerts Bell Dropdown */}
            <div className="pl-1 border-l border-border">
              <AlertsDropdown />
            </div>
          </div>
        </div>
      </div>

      {/* ── Page Content Container ────────────────────────────────────────── */}
      <div className="p-6 md:p-8 max-w-7xl mx-auto w-full space-y-6 flex-1">

        {/* ── Summary Statistics Cards ────────────────────────────────────── */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-card border border-border p-4 rounded-none shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Total Manifests</span>
              <FileSpreadsheet className="w-4 h-4 text-[#F26A4B]" />
            </div>
            <p className="text-2xl font-sans font-bold text-foreground mt-2">{uploads.length}</p>
            <p className="text-[11px] text-muted-foreground mt-1">Delivery batches submitted</p>
          </div>

          <div className="bg-card border border-border p-4 rounded-none shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Stock Units Ingested</span>
              <Package className="w-4 h-4 text-foreground" />
            </div>
            <p className="text-2xl font-sans font-bold text-foreground mt-2">{totalRowsProcessed.toLocaleString()}</p>
            <p className="text-[11px] text-muted-foreground font-medium mt-1">Auto-credited to inventory</p>
          </div>

          <div className="bg-card border border-border p-4 rounded-none shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Ingest Success Rate</span>
              <CheckCircle className="w-4 h-4 text-[#5E5A52]" />
            </div>
            <p className="text-2xl font-sans font-bold text-foreground mt-2">{successRate}%</p>
            <p className="text-[11px] text-muted-foreground mt-1">{successUploadsCount} successful uploads</p>
          </div>

          <div className="bg-card border border-border p-4 rounded-none shadow-2xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Active Branches</span>
              <Building2 className="w-4 h-4 text-foreground" />
            </div>
            <p className="text-2xl font-sans font-bold text-foreground mt-2">{locations.length}</p>
            <p className="text-[11px] text-muted-foreground mt-1">Ready for intake</p>
          </div>
        </div>

        {/* ── Notification Banners ────────────────────────────────────────── */}
        {error && (
          <div className="p-4 text-xs font-medium border border-destructive/30 bg-destructive/10 text-destructive flex items-center justify-between">
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
          <div className="p-4 text-xs font-medium border border-border bg-accent/60 text-foreground flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-[#F26A4B] shrink-0" />
              <span>{success}</span>
            </div>
            <button onClick={() => setSuccess('')} className="p-1 hover:opacity-75 cursor-pointer">
              <X size={14} />
            </button>
          </div>
        )}

        {/* ── Main 2-Column Layout ────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

          {/* ── Left Column: Upload Form (5 cols) ─────────────────────────── */}
          <div className="lg:col-span-5 bg-card border border-border p-5 rounded-none space-y-5 shadow-2xs">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-accent text-[#F26A4B] rounded-none border border-border">
                  <Upload size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-sans font-bold text-foreground">Upload Delivery Manifest</h3>
                  <p className="text-[11px] text-muted-foreground">Ingest wholesale invoices directly into stock</p>
                </div>
              </div>
            </div>

            {/* Template Download Prompt */}
            <div className="bg-accent/30 border border-border p-3.5 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold text-foreground">Need the standard format?</p>
                <p className="text-[11px] text-muted-foreground mt-0.5">Use our template with Item Name, Batch, and Qty columns.</p>
              </div>
              <button
                type="button"
                onClick={handleDownloadTemplate}
                className="shrink-0 flex items-center gap-1 text-xs font-semibold text-foreground bg-card border border-border px-2.5 py-1.5 hover:bg-accent transition-colors cursor-pointer"
              >
                <Download size={12} className="text-[#F26A4B]" />
                <span>Template</span>
              </button>
            </div>

            <form onSubmit={handleUpload} className="space-y-4">
              {/* Branch Selector */}
              <div>
                <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                  Receiving Branch / Store <span className="text-destructive">*</span>
                </label>
                <div className="relative flex items-center">
                  <Building2 size={14} className="absolute left-3 text-muted-foreground pointer-events-none" />
                  <select
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                    className="w-full text-xs font-medium bg-background border border-border text-foreground rounded-none pl-9 pr-8 py-2.5 hover:bg-accent/30 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
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

              {/* Drag & Drop File Zone */}
              <div>
                <label className="block text-xs font-bold text-foreground uppercase tracking-wider mb-1.5">
                  Delivery Manifest File <span className="text-destructive">*</span>
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
                  className={`flex flex-col items-center justify-center w-full px-4 py-8 border-2 border-dashed rounded-none cursor-pointer transition-all ${
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
                        Drop Excel/CSV manifest here, or <span className="text-[#F26A4B] font-bold">browse</span>
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-1">Supports .xlsx, .xls, .csv · Max 10MB</p>
                    </>
                  )}
                </label>
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading || !file || !selectedLocation}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-primary hover:bg-black disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed text-primary-foreground text-xs font-semibold rounded-none transition-colors shadow-2xs cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Processing &amp; Updating Inventory...</span>
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

          {/* ── Right Column: Manifest History & Receipts Table (7 cols) ──── */}
          <div className="lg:col-span-7 bg-card border border-border p-5 rounded-none space-y-4 shadow-2xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-accent text-foreground rounded-none border border-border">
                  <History size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-sans font-bold text-foreground">Recent Ingest History</h3>
                  <p className="text-[11px] text-muted-foreground">{uploads.length} total manifest submissions</p>
                </div>
              </div>

              {/* Search input */}
              <div className="relative w-full sm:w-56">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Filter by file or branch..."
                  className="w-full text-xs bg-background border border-border text-foreground placeholder:text-muted-foreground rounded-none pl-8 pr-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
            </div>

            {fetching ? (
              <div className="py-16 text-center text-muted-foreground flex flex-col items-center justify-center gap-2">
                <Loader2 size={20} className="animate-spin text-[#F26A4B]" />
                <span className="text-xs">Loading acquisition history...</span>
              </div>
            ) : filteredUploads.length === 0 ? (
              <div className="py-16 text-center flex flex-col items-center justify-center border border-dashed border-border p-6">
                <FileSpreadsheet className="w-10 h-10 text-muted-foreground/50 mb-2" />
                <h4 className="text-xs font-bold text-foreground">No Manifests Found</h4>
                <p className="text-[11px] text-muted-foreground mt-0.5 max-w-xs">
                  Upload an Excel or CSV manifest on the left to start auto-ingesting stock into your branches.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto border border-border">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-accent/40 border-b border-border text-[11px] font-bold text-foreground uppercase tracking-wider">
                      <th className="py-2.5 px-3">Manifest / File</th>
                      <th className="py-2.5 px-3">Branch</th>
                      <th className="py-2.5 px-3 text-center">Status</th>
                      <th className="py-2.5 px-3 text-right">Items Ingested</th>
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3 text-center">Invoice PDF</th>
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
                              <span className="truncate">{upload.filename || 'Manifest File'}</span>
                            </div>
                          </td>
                          <td className="py-3 px-3 text-muted-foreground">
                            {upload.location_name || `Branch #${upload.location_id}`}
                          </td>
                          <td className="py-3 px-3 text-center">
                            <span className={`inline-flex items-center px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider border ${
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
                                title="Download Official Tax Invoice PDF"
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
    </div>
  );
}

