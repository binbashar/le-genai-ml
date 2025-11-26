"use client";

import { useState, useEffect, useRef } from "react";
import { format, subHours, subDays, subWeeks } from "date-fns";
import { cn } from "@/lib/utils";

interface DateTimeRangePickerProps {
    startDate: Date;
    endDate: Date;
    onRangeChange: (start: Date, end: Date) => void;
    disabled?: boolean;
}

type RelativeOption = {
    label: string;
    getValue: () => Date;
};

const RELATIVE_OPTIONS: RelativeOption[] = [
    { label: "Last 1 hour", getValue: () => subHours(new Date(), 1) },
    { label: "Last 3 hours", getValue: () => subHours(new Date(), 3) },
    { label: "Last 12 hours", getValue: () => subHours(new Date(), 12) },
    { label: "Last 1 day", getValue: () => subDays(new Date(), 1) },
    { label: "Last 3 days", getValue: () => subDays(new Date(), 3) },
    { label: "Last 1 week", getValue: () => subWeeks(new Date(), 1) },
];

export function DateTimeRangePicker({
    startDate,
    endDate,
    onRangeChange,
    disabled,
}: DateTimeRangePickerProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [mode, setMode] = useState<"relative" | "absolute">("relative");
    const [tempStart, setTempStart] = useState<string>("");
    const [tempEnd, setTempEnd] = useState<string>("");
    const [timezone, setTimezone] = useState<string>("UTC");
    const containerRef = useRef<HTMLDivElement>(null);

    // Initialize timezone on mount (client-only)
    useEffect(() => {
        setTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    }, []);

    // Initialize temp state when opening
    useEffect(() => {
        if (isOpen) {
            setTempStart(format(startDate, "yyyy-MM-dd'T'HH:mm"));
            setTempEnd(format(endDate, "yyyy-MM-dd'T'HH:mm"));
        }
    }, [isOpen, startDate, endDate]);

    // Close on click outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                containerRef.current &&
                !containerRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false);
            }
        };

        document.addEventListener("mousedown", handleClickOutside);
        return () => document.removeEventListener("mousedown", handleClickOutside);
    }, []);

    const handleRelativeClick = (option: RelativeOption) => {
        const end = new Date();
        const start = option.getValue();
        onRangeChange(start, end);
        setIsOpen(false);
    };

    const handleApplyAbsolute = () => {
        if (tempStart && tempEnd) {
            const start = new Date(tempStart);
            const end = new Date(tempEnd);
            if (!isNaN(start.getTime()) && !isNaN(end.getTime())) {
                onRangeChange(start, end);
                setIsOpen(false);
            }
        }
    };

    const formatDisplay = (date: Date) => {
        return format(date, "MMM d, yyyy HH:mm");
    };

    return (
        <div className="relative" ref={containerRef}>
            <label className="label mb-1 block">Time Range</label>

            <button
                type="button"
                onClick={() => {
                    console.log("Date picker clicked, disabled:", disabled, "isOpen:", isOpen);
                    if (!disabled) {
                        setIsOpen(!isOpen);
                    }
                }}
                disabled={disabled}
                className={cn(
                    "w-full flex items-center justify-between px-3 py-2 text-sm border rounded-md bg-white text-left",
                    disabled ? "bg-gray-100 text-gray-400 cursor-not-allowed" : "hover:border-gray-400",
                    isOpen ? "border-blue-500 ring-1 ring-blue-500" : "border-gray-300"
                )}
            >
                <span className="truncate">
                    {formatDisplay(startDate)} — {formatDisplay(endDate)} ({timezone})
                </span>
                <svg
                    className="h-4 w-4 text-gray-500 ml-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                </svg>
            </button>

            {isOpen && (
                <div className="absolute z-10 mt-1 w-full min-w-[320px] bg-white border border-gray-200 rounded-md shadow-lg p-4">
                    <div className="flex space-x-4 border-b border-gray-200 mb-4 pb-2">
                        <button
                            type="button"
                            onClick={() => setMode("relative")}
                            className={cn(
                                "text-sm font-medium pb-2 -mb-2.5 border-b-2 transition-colors",
                                mode === "relative"
                                    ? "border-blue-500 text-blue-600"
                                    : "border-transparent text-gray-500 hover:text-gray-700"
                            )}
                        >
                            Relative
                        </button>
                        <button
                            type="button"
                            onClick={() => setMode("absolute")}
                            className={cn(
                                "text-sm font-medium pb-2 -mb-2.5 border-b-2 transition-colors",
                                mode === "absolute"
                                    ? "border-blue-500 text-blue-600"
                                    : "border-transparent text-gray-500 hover:text-gray-700"
                            )}
                        >
                            Absolute
                        </button>
                    </div>

                    {mode === "relative" ? (
                        <div className="grid grid-cols-2 gap-2">
                            {RELATIVE_OPTIONS.map((option) => (
                                <button
                                    key={option.label}
                                    type="button"
                                    onClick={() => handleRelativeClick(option)}
                                    className="px-3 py-2 text-sm text-left hover:bg-gray-50 rounded-md transition-colors"
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>
                    ) : (
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-500">Start Time</label>
                                <input
                                    type="datetime-local"
                                    value={tempStart}
                                    onChange={(e) => setTempStart(e.target.value)}
                                    className="input w-full text-sm"
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs font-medium text-gray-500">End Time</label>
                                <input
                                    type="datetime-local"
                                    value={tempEnd}
                                    onChange={(e) => setTempEnd(e.target.value)}
                                    className="input w-full text-sm"
                                />
                            </div>
                            <div className="flex justify-end pt-2">
                                <button
                                    type="button"
                                    onClick={handleApplyAbsolute}
                                    className="btn-primary text-sm px-4 py-2"
                                >
                                    Apply
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
