import React from 'react';
import AIAssistantInterface from '../../components/ui/ai-assistant-interface';

const Chatbot = () => {
    return (
        <div className="w-full h-full flex-1 bg-background overflow-hidden p-4 md:p-6">
            <AIAssistantInterface isPreview={false} />
        </div>
    );
};


export default Chatbot;
