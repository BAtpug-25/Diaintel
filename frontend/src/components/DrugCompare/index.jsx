// DrugCompare component placeholder — implemented in Step 12
import React from 'react';

export default function DrugCompare({ drug1, drug2 }) {
    return (
        <div className="di-card">
            <h2 className="di-section-title">Comparison</h2>
            <p className="text-di-text-secondary text-sm">
                {drug1} vs {drug2} — Step 12
            </p>
        </div>
    );
}
