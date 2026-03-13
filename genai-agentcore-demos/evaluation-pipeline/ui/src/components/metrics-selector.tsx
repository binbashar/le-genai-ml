"use client";

import { AVAILABLE_METRICS } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface MetricsSelectorProps {
  value: string[];
  onChange: (value: string[]) => void;
  error?: string;
  disabled?: boolean;
}

export function MetricsSelector({
  value,
  onChange,
  error,
  disabled,
}: MetricsSelectorProps) {
  const handleToggle = (metricValue: string) => {
    if (value.includes(metricValue)) {
      onChange(value.filter((v) => v !== metricValue));
    } else {
      onChange([...value, metricValue]);
    }
  };

  return (
    <div className="space-y-2">
      <label className="label">Evaluation Metrics</label>
      <div className="grid grid-cols-2 gap-2">
        {AVAILABLE_METRICS.map((metric) => (
          <label
            key={metric.value}
            className={cn(
              "flex items-start gap-2 rounded-md border p-3 cursor-pointer transition-colors",
              value.includes(metric.value)
                ? "border-blue-500 bg-blue-50"
                : "border-gray-200 hover:border-gray-300",
              disabled && "opacity-50 cursor-not-allowed"
            )}
          >
            <input
              type="checkbox"
              checked={value.includes(metric.value)}
              onChange={() => handleToggle(metric.value)}
              disabled={disabled}
              className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <div>
              <div className="text-sm font-medium text-gray-900">
                {metric.label}
              </div>
              <div className="text-xs text-gray-500">{metric.description}</div>
            </div>
          </label>
        ))}
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
