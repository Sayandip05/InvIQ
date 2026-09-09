import React from 'react';
import AIAssistantInterface from '../../components/ui/ai-assistant-interface';
import AlertsDropdown from '../../components/layout/AlertsDropdown';

const Chatbot = () => {
    return (
        <div className="flex flex-col min-h-full bg-background font-sans text-foreground">
            {/* ── Full-Width Sticky Top Navbar (Identical to Dashboard / Inventory) ── */}
            <div className="sticky top-0 z-30 bg-card/90 backdrop-blur border-b border-border px-6 py-3.5 shadow-2xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-xl font-sans font-bold text-foreground tracking-tight">AI Assistant &amp; Copilot</h2>
                        <p className="text-xs text-muted-foreground mt-0.5">
                            Real-time pharmacological queries, inventory intelligence, and guidance
                        </p>
                    </div>

                    <div className="flex items-center gap-2.5">
                        <div className="pl-1 border-l border-border">
                            <AlertsDropdown />
                        </div>
                    </div>
                </div>
            </div>

            <div className="p-4 md:p-6 flex-1 overflow-hidden">
                <AIAssistantInterface isPreview={false} />
            </div>
        </div>
    );
};

export default Chatbot;
