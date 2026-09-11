import React, { useState, useMemo } from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { Calendar } from 'lucide-react';

const MONTH_NAMES = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/**
 * Dynamically computes clean, rounded Y-axis ticks for any scale
 * (from a tiny clinic with 5 medicines to a warehouse with 10,000 units).
 */
function getNiceYScale(maxVal) {
    if (!maxVal || maxVal <= 0) {
        return { domain: [0, 10], ticks: [0, 2, 5, 8, 10] };
    }
    const magnitude = Math.pow(10, Math.floor(Math.log10(maxVal)));
    const fraction = maxVal / magnitude;
    let niceFraction;
    if (fraction <= 1.2) niceFraction = 1.2;
    else if (fraction <= 2) niceFraction = 2;
    else if (fraction <= 2.5) niceFraction = 2.5;
    else if (fraction <= 5) niceFraction = 5;
    else niceFraction = 10;

    const niceMax = Math.round(niceFraction * magnitude);
    const step = niceMax / 4;
    const ticks = [0, step, step * 2, step * 3, niceMax].map(v => Math.round(v));
    return { domain: [0, niceMax], ticks };
}

/**
 * Builds versatile rolling month projections starting from current month.
 */
function generateRollingTimeline(count = 6) {
    const now = new Date();
    const currentMonth = now.getMonth();
    const sampleExpPattern = [25, 45, 38, 65, 52, 85, 40, 55, 30, 70, 48, 60];
    const sampleThreshPattern = [18, 32, 29, 48, 41, 61, 30, 40, 22, 50, 35, 45];

    return Array.from({ length: count }, (_, i) => {
        const mIdx = (currentMonth + i) % 12;
        const exp = sampleExpPattern[i % sampleExpPattern.length];
        const thresh = sampleThreshPattern[i % sampleThreshPattern.length];
        return {
            month: MONTH_NAMES[mIdx],
            expiring: exp,
            threshold: thresh,
            risk_level: exp >= 60 ? 'High' : exp >= 35 ? 'Medium' : 'Normal',
        };
    });
}

export default function ExpiryLineChart({ data, height = 240 }) {
    const [horizon, setHorizon] = useState(6);

    // Adapt to any incoming data structure or generate dynamic rolling timeline
    const chartData = useMemo(() => {
        if (Array.isArray(data) && data.length > 0) {
            if (data.length >= horizon) {
                return data.slice(0, horizon);
            }
            return data;
        }
        return generateRollingTimeline(horizon);
    }, [data, horizon]);

    // Calculate dynamic Y-axis scale based on actual data
    const maxVal = useMemo(() => {
        return Math.max(
            ...chartData.map(d => Math.max(Number(d.expiring) || 0, Number(d.threshold) || 0)),
            10
        );
    }, [chartData]);

    const { domain, ticks } = useMemo(() => getNiceYScale(maxVal), [maxVal]);

    return (
        <div className="flex flex-col justify-between h-full w-full">
            {/* Header: Title and Horizon Toggle (Replacing bulky badges to save vertical space) */}
            <div className="flex items-center justify-between gap-3 mb-2.5">
                <div>
                    <h3 className="text-base font-sans font-bold text-foreground flex items-center gap-1.5">
                        <Calendar size={16} className="text-[#F26A4B]" />
                        Medicine Expiry Forecast
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        Expected expiring medicines over the upcoming period.
                    </p>
                </div>

                {/* Horizon Selector: Replaces old badges with sleek 6/12 Months toggle */}
                <div className="inline-flex items-center bg-accent/60 p-0.5 rounded-md border border-border text-[11px] font-medium shrink-0">
                    <button
                        type="button"
                        onClick={() => setHorizon(6)}
                        className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                            horizon === 6
                                ? 'bg-card text-foreground font-bold shadow-xs'
                                : 'text-muted-foreground hover:text-foreground'
                        }`}
                    >
                        6 Months
                    </button>
                    <button
                        type="button"
                        onClick={() => setHorizon(12)}
                        className={`px-2.5 py-1 rounded transition-colors cursor-pointer ${
                            horizon === 12
                                ? 'bg-card text-foreground font-bold shadow-xs'
                                : 'text-muted-foreground hover:text-foreground'
                        }`}
                    >
                        12 Months
                    </button>
                </div>
            </div>

            {/* Dynamic Curve Container styled seamlessly in Theme Colors (Rounded Corners, Zero Black) */}
            <div className="w-full rounded-xl bg-card p-3 border border-border shadow-none">
                {/* Theme-aligned Legend with Rounded Indicators */}
                <div className="flex items-center justify-end gap-4 text-[11px] text-muted-foreground mb-2 px-1">
                    <div className="flex items-center gap-1.5">
                        <span className="w-2.5 h-2.5 rounded-full bg-[#1E1E1E] inline-block" />
                        <span className="text-foreground font-medium">Expiring Medicines</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                        <span className="w-4 h-0 border-t-2 border-dashed border-[#7A7268] inline-block" />
                        <span>Safety Alert Line</span>
                    </div>
                </div>

                <div style={{ height, width: '100%' }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                            data={chartData}
                            margin={{ top: 12, right: 16, left: -12, bottom: 4 }}
                        >
                            {/* Theme subtle horizontal grid lines */}
                            <CartesianGrid
                                strokeDasharray="3 3"
                                vertical={false}
                                stroke="#D2CBBB"
                                opacity={0.6}
                            />
                            <XAxis
                                dataKey="month"
                                stroke="#7A7268"
                                tick={{ fill: '#5E5A52', fontSize: 11 }}
                                tickLine={false}
                                axisLine={{ stroke: '#D2CBBB' }}
                                dy={4}
                            />
                            <YAxis
                                domain={domain}
                                ticks={ticks}
                                stroke="#7A7268"
                                tick={{ fill: '#5E5A52', fontSize: 11 }}
                                tickLine={false}
                                axisLine={false}
                                dx={-4}
                            />
                            <Tooltip
                                content={({ active, payload, label }) => {
                                    if (!active || !payload || !payload.length) return null;
                                    const expiringVal = payload.find(p => p.dataKey === 'expiring')?.value ?? 0;
                                    const threshVal = payload.find(p => p.dataKey === 'threshold')?.value ?? 0;
                                    const itemData = payload[0]?.payload;

                                    return (
                                        <div className="bg-card border border-border rounded-lg p-3 shadow-md text-xs min-w-[150px]">
                                            <div className="flex items-center justify-between border-b border-border pb-1.5 mb-2">
                                                <span className="font-bold text-foreground tracking-wide">{label} Expiration</span>
                                                <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                                    expiringVal >= (maxVal * 0.65)
                                                        ? 'bg-[#F26A4B]/15 text-[#F26A4B] border border-[#F26A4B]/30'
                                                        : 'bg-accent text-foreground'
                                                }`}>
                                                    {itemData?.risk_level || 'Normal'}
                                                </span>
                                            </div>
                                            <div className="space-y-1.5">
                                                <div className="flex items-center justify-between text-foreground">
                                                    <span className="flex items-center gap-1.5">
                                                        <span className="w-2 h-2 rounded-full bg-[#1E1E1E] inline-block" />
                                                        Expiring:
                                                    </span>
                                                    <strong className="font-mono text-foreground">{expiringVal} units</strong>
                                                </div>
                                                <div className="flex items-center justify-between text-muted-foreground">
                                                    <span className="flex items-center gap-1.5">
                                                        <span className="w-2.5 h-0 border-t border-dashed border-[#7A7268]" />
                                                        Safety Level:
                                                    </span>
                                                    <span className="font-mono text-foreground">{threshVal} units</span>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                }}
                            />

                            {/* Secondary Line: Dashed Taupe/Slate Spline Curve */}
                            <Line
                                type="natural"
                                dataKey="threshold"
                                stroke="#7A7268"
                                strokeWidth={2}
                                strokeDasharray="4 4"
                                dot={false}
                                activeDot={false}
                                name="Safety Alert Line"
                            />

                            {/* Primary Line: Solid Deep Onyx/Charcoal Spline Curve with Node Dots */}
                            <Line
                                type="natural"
                                dataKey="expiring"
                                stroke="#1E1E1E"
                                strokeWidth={3}
                                dot={{
                                    r: 4.5,
                                    fill: '#1E1E1E',
                                    stroke: '#F4EFE4',
                                    strokeWidth: 2,
                                }}
                                activeDot={{
                                    r: 6.5,
                                    fill: '#F26A4B',
                                    stroke: '#F4EFE4',
                                    strokeWidth: 2,
                                }}
                                name="Expiring Medicines"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    );
}
