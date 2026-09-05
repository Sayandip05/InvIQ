import React, { useState } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

/**
 * InvIQ Theme & Domain Palette for "Mono Rounded" Arc:
 * - HEALTHY: Deep Onyx / Charcoal (#1E1E1E) - Dominant monochrome anchor for compliant stock
 * - WARNING: Warm Taupe / Slate (#7A7268) - Mid-tone mono for near-expiry & reorder thresholds
 * - CRITICAL: Signature Brand Coral (#F26A4B) - InvIQ theme accent for stockouts & breaches
 */
const STATUS_THEME_COLORS = {
  HEALTHY: '#1E1E1E',
  WARNING: '#7A7268',
  CRITICAL: '#F26A4B',
};

const MONO_THEME_PALETTE = ['#1E1E1E', '#F26A4B', '#5E5A52', '#7A7268', '#A89F91', '#C2BBB0'];

const STATUS_LABELS = {
  HEALTHY: 'Optimal Batches',
  WARNING: 'Near Expiry',
  CRITICAL: 'Critical Alerts',
};

export default function MonoRoundedDonut({
  data = [],
  title = 'Stock Health',
  height = 250,
  innerRadius = 70,
  outerRadius = 95,
  cornerRadius = 8,
  paddingAngle = 6,
}) {
  const [hoveredIndex, setHoveredIndex] = useState(null);

  // Filter and sanitize valid items
  const validData = Array.isArray(data) ? data.filter((d) => Number(d.value) > 0) : [];
  const total = validData.reduce((acc, curr) => acc + (Number(curr.value) || 0), 0);

  // Calculate domain health metric (% of non-critical items)
  const criticalEntry = validData.find((d) => String(d.name).toUpperCase() === 'CRITICAL');
  const criticalVal = criticalEntry ? Number(criticalEntry.value) : 0;
  const overallHealthPct = total > 0 ? (((total - criticalVal) / total) * 100).toFixed(1) : '100';

  // Fallback placeholder if no data is available
  const displayData =
    validData.length > 0
      ? validData
      : [{ name: 'HEALTHY', value: 1, label: 'Optimal Stock' }];

  const isPlaceholder = validData.length === 0;

  // Active slice values for center label
  const activeEntry = hoveredIndex !== null && validData[hoveredIndex] ? validData[hoveredIndex] : null;

  const centerValue = activeEntry
    ? `${total > 0 ? ((Number(activeEntry.value) / total) * 100).toFixed(1) : 0}%`
    : `${overallHealthPct}%`;

  const centerLabel = activeEntry
    ? STATUS_LABELS[String(activeEntry.name).toUpperCase()] || activeEntry.name
    : title;

  const getColor = (entry, index) => {
    if (isPlaceholder) return '#D2CBBB';
    const key = String(entry.name).toUpperCase();
    return (
      entry.color ||
      STATUS_THEME_COLORS[key] ||
      MONO_THEME_PALETTE[index % MONO_THEME_PALETTE.length]
    );
  };

  return (
    <div className="flex flex-col items-center w-full">
      {/* Donut Ring Container */}
      <div className="relative w-full flex items-center justify-center" style={{ height }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={displayData}
              cx="50%"
              cy="50%"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              cornerRadius={cornerRadius}
              paddingAngle={displayData.length > 1 ? paddingAngle : 0}
              dataKey="value"
              stroke="none"
              onMouseEnter={(_, index) => !isPlaceholder && setHoveredIndex(index)}
              onMouseLeave={() => setHoveredIndex(null)}
              animationDuration={800}
            >
              {displayData.map((entry, index) => {
                const isHovered = hoveredIndex === index;
                const isFaded = hoveredIndex !== null && !isHovered;
                return (
                  <Cell
                    key={`slice-${index}`}
                    fill={getColor(entry, index)}
                    style={{
                      opacity: isFaded ? 0.4 : 1,
                      transition: 'opacity 0.2s ease, transform 0.2s ease',
                      cursor: isPlaceholder ? 'default' : 'pointer',
                    }}
                  />
                );
              })}
            </Pie>
            {!isPlaceholder && (
              <Tooltip
                contentStyle={{
                  backgroundColor: '#F4EFE4',
                  borderColor: '#D2CBBB',
                  borderRadius: '0.5rem',
                  color: '#1E1E1E',
                  fontSize: '0.75rem',
                  boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
                }}
                formatter={(val, name) => {
                  const pct = total > 0 ? ((Number(val) / total) * 100).toFixed(1) : 0;
                  const label = STATUS_LABELS[String(name).toUpperCase()] || name;
                  return [`${val} units (${pct}%)`, label];
                }}
              />
            )}
          </PieChart>
        </ResponsiveContainer>

        {/* Center Readout - "Mono Rounded" Style */}
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none text-center px-4">
          <span className="text-3xl font-sans font-bold tracking-tight text-foreground transition-all duration-200">
            {centerValue}
          </span>
          <span className="text-xs font-medium text-muted-foreground tracking-wide mt-0.5 transition-all duration-200 max-w-[120px] truncate">
            {centerLabel}
          </span>
        </div>
      </div>

      {/* Domain-Aligned Status Legend Chips */}
      {!isPlaceholder && validData.length > 0 && (
        <div className="flex items-center justify-center gap-2 pt-3 flex-wrap w-full px-2">
          {validData.map((entry, idx) => {
            const color = getColor(entry, idx);
            const pct = total > 0 ? ((Number(entry.value) / total) * 100).toFixed(1) : '0';
            const isHovered = hoveredIndex === idx;
            const displayName =
              STATUS_LABELS[String(entry.name).toUpperCase()] ||
              entry.name.charAt(0).toUpperCase() + entry.name.slice(1).toLowerCase();

            return (
              <div
                key={entry.name || idx}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs cursor-pointer transition-all duration-150 ${
                  isHovered
                    ? 'bg-accent border-foreground/30 shadow-xs scale-105'
                    : 'bg-card border-border/70 hover:border-border hover:bg-accent/50'
                }`}
              >
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: color }}
                />
                <span className="font-medium text-foreground">{displayName}</span>
                <span className="text-muted-foreground font-mono font-semibold">
                  {entry.value}
                </span>
                <span className="text-[11px] text-muted-foreground/80">({pct}%)</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
