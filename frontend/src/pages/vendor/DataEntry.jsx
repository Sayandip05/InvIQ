/**
 * Vendor DataEntry Page — Excel delivery upload portal.
 *
 * Vendors can:
 * - Download a blank Excel template
 * - Upload delivery manifests (.xlsx/.xls)
 * - View their upload history
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import api from '../../services/api';
import { Upload, Download, FileSpreadsheet, History, AlertCircle, CheckCircle, Loader2, LogOut, Package } from 'lucide-react';

export default function DataEntry() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState('');
  const [file, setFile] = useState(null);
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [dragOver, setDragOver] = useState(false);

  useEffect(() => {
    fetchLocations();
    fetchUploadHistory();
  }, []);

  const fetchLocations = async () => {
    try {
      const response = await api.get('/inventory/locations');
      setLocations(response.data.data || []);
    } catch (err) {
      console.error('Failed to fetch locations:', err);
    }
  };

  const fetchUploadHistory = async () => {
    try {
      const response = await api.get('/vendor/my-uploads');
      setUploads(response.data.data || []);
    } catch (err) {
      console.error('Failed to fetch upload history:', err);
    }
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/vendor/template', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'delivery_template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download template. Please try again.');
    }
  };

  const handleFileChange = (selectedFile) => {
    if (!selectedFile) return;
    if (!selectedFile.name.endsWith('.xlsx') && !selectedFile.name.endsWith('.xls')) {
      setError('Only .xlsx or .xls files are accepted');
      setFile(null);
      return;
    }
    if (selectedFile.size > 5 * 1024 * 1024) {
      setError('File size must be under 5MB');
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
    if (!selectedLocation) { setError('Please select a location'); return; }
    if (!file) { setError('Please select a file to upload'); return; }

    setLoading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/vendor/upload-delivery?location_id=${selectedLocation}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSuccess('Delivery uploaded successfully!');
      setFile(null);
      const fileInput = document.getElementById('file-upload');
      if (fileInput) fileInput.value = '';
      fetchUploadHistory();
    } catch (err) {
      const msg = err?.response?.data?.detail || err?.response?.data?.message || 'Upload failed. Please try again.';
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

  const statusStyles = {
    success: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200',
    partial: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200',
    failed: 'bg-red-50 text-red-700 ring-1 ring-red-200',
  };

  return (
    <div className="min-h-screen bg-slate-50">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="bg-blue-600 p-2 rounded-lg shadow-sm">
                <FileSpreadsheet className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-slate-800 leading-none">Vendor Portal</h1>
                <p className="text-xs text-slate-500 leading-none mt-0.5">InvIQ Supply Chain</p>
              </div>
            </div>

            {/* User info + logout */}
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2 bg-slate-100 rounded-full px-3 py-1.5">
                <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold uppercase">
                  {user?.username?.[0] || 'V'}
                </div>
                <span className="text-slate-700 text-sm font-medium">{user?.username}</span>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-red-500 transition-colors font-medium"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Page title ──────────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h2 className="text-2xl font-bold text-slate-800">Delivery Upload</h2>
          <p className="text-slate-500 text-sm mt-1">
            Submit your delivery manifest to update inventory stock levels.
          </p>
        </div>
      </div>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

          {/* ── Upload Section ─────────────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center">
                <Upload className="w-4 h-4 text-blue-600" />
              </div>
              <h3 className="text-base font-semibold text-slate-800">Upload Delivery</h3>
            </div>

            <div className="p-6 space-y-6">
              {/* Download template strip */}
              <div className="flex items-start justify-between gap-4 p-4 bg-blue-50 rounded-xl border border-blue-100">
                <div>
                  <p className="text-sm font-medium text-blue-800">Need a template?</p>
                  <p className="text-xs text-blue-600 mt-0.5">
                    Download the Excel template and fill in your delivery data.
                  </p>
                </div>
                <button
                  onClick={handleDownloadTemplate}
                  className="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-2 bg-white hover:bg-blue-50 text-blue-700 text-xs font-semibold rounded-lg border border-blue-200 transition-colors shadow-sm"
                >
                  <Download className="w-3.5 h-3.5" />
                  Download
                </button>
              </div>

              <form onSubmit={handleUpload} className="space-y-5">
                {/* Location selector */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Delivery Location <span className="text-red-500">*</span>
                  </label>
                  <select
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                    className="w-full bg-white border border-slate-300 text-slate-800 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition"
                  >
                    <option value="">Choose a location...</option>
                    {locations.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name} ({loc.type})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Drag-and-drop file zone */}
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Excel File <span className="text-red-500">*</span>
                  </label>
                  <input
                    id="file-upload"
                    type="file"
                    accept=".xlsx,.xls"
                    onChange={handleInputChange}
                    className="hidden"
                  />
                  <label
                    htmlFor="file-upload"
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    className={`flex flex-col items-center justify-center w-full px-4 py-10 border-2 border-dashed rounded-xl cursor-pointer transition-all ${
                      dragOver
                        ? 'border-blue-400 bg-blue-50'
                        : file
                        ? 'border-emerald-400 bg-emerald-50'
                        : 'border-slate-300 hover:border-slate-400 bg-slate-50 hover:bg-slate-100'
                    }`}
                  >
                    {file ? (
                      <>
                        <CheckCircle className="w-8 h-8 text-emerald-500 mb-2" />
                        <p className="text-sm font-medium text-emerald-700">{file.name}</p>
                        <p className="text-xs text-emerald-500 mt-1">
                          {(file.size / 1024).toFixed(1)} KB · Click to replace
                        </p>
                      </>
                    ) : (
                      <>
                        <Upload className="w-8 h-8 text-slate-400 mb-2" />
                        <p className="text-sm font-medium text-slate-600">
                          Drop your file here, or <span className="text-blue-600">browse</span>
                        </p>
                        <p className="text-xs text-slate-400 mt-1">.xlsx or .xls · Max 5 MB</p>
                      </>
                    )}
                  </label>
                </div>

                {/* Error banner */}
                {error && (
                  <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{error}</span>
                  </div>
                )}

                {/* Success banner */}
                {success && (
                  <div className="flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm rounded-lg px-4 py-3">
                    <CheckCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{success}</span>
                  </div>
                )}

                {/* Submit */}
                <button
                  type="submit"
                  disabled={loading || !file || !selectedLocation}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-colors shadow-sm text-sm"
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload Delivery
                    </>
                  )}
                </button>
              </form>
            </div>
          </div>

          {/* ── Upload History ─────────────────────────────────────────── */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center">
                  <History className="w-4 h-4 text-slate-600" />
                </div>
                <h3 className="text-base font-semibold text-slate-800">Upload History</h3>
              </div>
              {uploads.length > 0 && (
                <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full">
                  {uploads.length} record{uploads.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>

            <div className="p-6">
              {uploads.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                    <Package className="w-7 h-7 text-slate-400" />
                  </div>
                  <p className="text-sm font-medium text-slate-600">No uploads yet</p>
                  <p className="text-xs text-slate-400 mt-1">
                    Your delivery submissions will appear here.
                  </p>
                </div>
              ) : (
                <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                  {uploads.map((upload, index) => (
                    <div
                      key={index}
                      className="p-4 bg-slate-50 rounded-xl border border-slate-200 hover:border-slate-300 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-sm font-semibold text-slate-800 truncate">
                            {upload.filename || 'Unknown file'}
                          </p>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {upload.location_name || `Location ID: ${upload.location_id}`}
                          </p>
                          <p className="text-xs text-slate-400 mt-1">
                            {formatDate(upload.created_at)}
                          </p>
                        </div>
                        <span className={`flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-semibold ${
                          statusStyles[upload.status] || statusStyles.success
                        }`}>
                          {upload.status || 'completed'}
                        </span>
                      </div>
                      {upload.rows_processed != null && (
                        <div className="mt-3 pt-3 border-t border-slate-200 flex items-center gap-4 text-xs text-slate-500">
                          <span>
                            <span className="font-semibold text-slate-700">{upload.rows_processed}</span> rows processed
                          </span>
                          {upload.rows_failed > 0 && (
                            <span>
                              <span className="font-semibold text-red-600">{upload.rows_failed}</span> failed
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
