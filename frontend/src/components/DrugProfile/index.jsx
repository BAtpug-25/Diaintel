// DrugProfile component placeholder — implemented in Step 11
import React from 'react';

export default function DrugProfile({ drugName }) {
    return (
        <div className="di-card">
            <h2 className="text-xl font-bold text-di-text capitalize">{drugName}</h2>
            <p className="text-di-text-secondary text-sm mt-1">Profile — Step 11</p>
        </div>
    );
}
