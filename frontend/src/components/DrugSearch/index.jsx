// DrugSearch component placeholder — implemented in Step 11
import React from 'react';

export default function DrugSearch({ onSelect }) {
    return (
        <div className="di-input flex items-center gap-2">
            <span>🔍</span>
            <input
                type="text"
                placeholder="Search drugs..."
                className="bg-transparent border-none outline-none flex-1 text-di-text"
                onChange={(e) => onSelect?.(e.target.value)}
            />
        </div>
    );
}
