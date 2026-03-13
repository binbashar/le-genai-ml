"use client";

import { useState, useRef, useEffect } from "react";

interface Option {
    label: string;
    value: string;
}

interface MultiSelectDropdownProps {
    label: string;
    options: Option[];
    selected: string[];
    onChange: (selected: string[]) => void;
}

export function MultiSelectDropdown({
    label,
    options,
    selected,
    onChange
}: MultiSelectDropdownProps) {
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, []);

    const handleToggle = (value: string) => {
        if (selected.includes(value)) {
            onChange(selected.filter(v => v !== value));
        } else {
            onChange([...selected, value]);
        }
    };

    const handleSelectAll = () => {
        if (selected.length === options.length) {
            onChange([]);
        } else {
            onChange(options.map(o => o.value));
        }
    };

    const selectedLabel = selected.length === 0
        ? "None selected"
        : selected.length === options.length
            ? "All Metrics"
            : `${selected.length} selected`;

    return (
        <div className="relative" ref={dropdownRef}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
                {label}
            </label>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full bg-white border border-gray-300 rounded-md py-2 px-3 flex items-center justify-between shadow-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
                <span className="block truncate">{selectedLabel}</span>
                <span className="ml-2 flex-shrink-0 text-gray-400">
                    ▼
                </span>
            </button>

            {isOpen && (
                <div className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
                    <div
                        className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-gray-100 border-b border-gray-100"
                        onClick={handleSelectAll}
                    >
                        <div className="flex items-center">
                            <input
                                type="checkbox"
                                checked={selected.length === options.length && options.length > 0}
                                readOnly
                                className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <span className="ml-3 block truncate font-medium">
                                Select All
                            </span>
                        </div>
                    </div>

                    {options.map((option) => (
                        <div
                            key={option.value}
                            className="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-gray-100"
                            onClick={() => handleToggle(option.value)}
                        >
                            <div className="flex items-center">
                                <input
                                    type="checkbox"
                                    checked={selected.includes(option.value)}
                                    readOnly
                                    className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                                />
                                <span className="ml-3 block truncate">
                                    {option.label}
                                </span>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
