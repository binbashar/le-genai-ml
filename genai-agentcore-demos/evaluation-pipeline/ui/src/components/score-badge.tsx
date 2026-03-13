import React from "react";

interface ScoreBadgeProps {
    score: number;
    max?: number;
    size?: number;
    strokeWidth?: number;
}

export function ScoreBadge({
    score,
    max = 10,
    size = 40,
    strokeWidth = 3
}: ScoreBadgeProps) {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const normalizedScore = Math.min(Math.max(score, 0), max);
    const percentage = normalizedScore / max;
    const offset = circumference - percentage * circumference;

    // Determine color based on score
    let colorClass = "text-red-500";
    if (normalizedScore >= 8) {
        colorClass = "text-green-500";
    } else if (normalizedScore >= 5) {
        colorClass = "text-yellow-500";
    }

    return (
        <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
            {/* Background Circle */}
            <svg
                className="transform -rotate-90 w-full h-full"
                viewBox={`0 0 ${size} ${size}`}
            >
                <circle
                    className="text-gray-200"
                    strokeWidth={strokeWidth}
                    stroke="currentColor"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
                {/* Progress Circle */}
                <circle
                    className={`${colorClass} transition-all duration-500 ease-out`}
                    strokeWidth={strokeWidth}
                    strokeDasharray={circumference}
                    strokeDashoffset={offset}
                    strokeLinecap="round"
                    stroke="currentColor"
                    fill="transparent"
                    r={radius}
                    cx={size / 2}
                    cy={size / 2}
                />
            </svg>

            {/* Score Text */}
            <div className={`absolute inset-0 flex items-center justify-center text-xs font-bold ${colorClass}`}>
                {score.toFixed(1)}
            </div>
        </div>
    );
}
