import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AdminLayout from './components/layout/AdminLayout';
import Dashboard from './pages/admin/Dashboard';
import Inventory from './pages/admin/Inventory';
import Chatbot from './pages/admin/Chatbot';
import Requisitions from './pages/admin/Requisitions';
import DataEntry from './pages/vendor/DataEntry';
import StaffRequisition from './pages/staff/StaffRequisition';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Vendor Routes */}
        <Route path="/" element={<Navigate to="/vendor" replace />} />
        <Route path="/vendor" element={<DataEntry />} />

        {/* Staff Routes */}
        <Route path="/staff" element={<StaffRequisition />} />

        {/* Admin Routes */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="requisitions" element={<Requisitions />} />
          <Route path="chat" element={<Chatbot />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
