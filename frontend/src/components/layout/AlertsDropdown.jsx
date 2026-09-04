import React from 'react';
import { Bell, X, AlertTriangle, Package } from 'lucide-react';
import { useWebSocketAlerts } from '../../context/WebSocketContext';

const AlertsDropdown = () => {
    const { alerts, clearAlert, clearAllAlerts } = useWebSocketAlerts();
    const [isOpen, setIsOpen] = React.useState(false);

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="relative p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-md transition cursor-pointer"
            >
                <Bell size={20} />
                {alerts.length > 0 && (
                    <span className="absolute top-1 right-1 w-2 h-2 bg-destructive rounded-full animate-pulse" />
                )}
            </button>

            {isOpen && (
                <>
                    <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
                    <div className="absolute right-0 mt-2 w-80 bg-card rounded-lg shadow-xl border border-border z-20 overflow-hidden text-card-foreground">
                        <div className="p-3 border-b border-border flex items-center justify-between">
                            <span className="font-semibold text-foreground text-sm">Real-time Alerts</span>
                            {alerts.length > 0 && (
                                <button
                                    onClick={clearAllAlerts}
                                    className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
                                >
                                    Clear all
                                </button>
                            )}
                        </div>
                        <div className="max-h-80 overflow-y-auto">
                            {alerts.length === 0 ? (
                                <div className="p-4 text-center text-muted-foreground text-sm">
                                    No new alerts
                                </div>
                            ) : (
                                alerts.map((alert, index) => (
                                    <div
                                        key={index}
                                        className="p-3 border-b border-border/50 hover:bg-accent/40 transition relative"
                                    >
                                        <button
                                            onClick={() => clearAlert(index)}
                                            className="absolute top-2 right-2 text-muted-foreground hover:text-foreground cursor-pointer"
                                        >
                                            <X size={14} />
                                        </button>
                                        <div className="flex items-start gap-2 pr-6">
                                            {alert.type === 'fefo_expiry_alert' || alert.event_topic === 'expiry.critical' ? (
                                                <span className="p-1 bg-destructive/10 text-destructive rounded-md shrink-0 mt-0.5">
                                                    <AlertTriangle size={15} />
                                                </span>
                                            ) : alert.type === 'cold_chain_warning' || alert.event_topic === 'coldchain.warning' ? (
                                                <span className="p-1 bg-blue-500/10 text-blue-700 rounded-md shrink-0 mt-0.5">
                                                    <Package size={15} />
                                                </span>
                                            ) : (
                                                <span className="p-1 bg-amber-500/10 text-amber-700 rounded-md shrink-0 mt-0.5">
                                                    <AlertTriangle size={15} />
                                                </span>
                                            )}
                                            <div>
                                                <p className="text-sm font-medium text-foreground">
                                                    {alert.message || (alert.type === 'fefo_expiry_alert' ? 'Medicine expiring soon' : 'Stock alert')}
                                                </p>
                                                {alert.item_name && (
                                                    <p className="text-xs text-muted-foreground mt-0.5">
                                                        Item: {alert.item_name} {alert.batch_number ? `(Batch #${alert.batch_number})` : ''}
                                                    </p>
                                                )}
                                                {alert.location_name && (
                                                    <p className="text-xs text-muted-foreground">
                                                        Location: {alert.location_name}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default AlertsDropdown;