"use client";

import { cn } from "@/lib/utils";
import { format } from "date-fns";

interface DateRangePickerProps {
  startDate: Date | undefined;
  endDate: Date | undefined;
  onStartDateChange: (date: Date | undefined) => void;
  onEndDateChange: (date: Date | undefined) => void;
  startError?: string;
  endError?: string;
  disabled?: boolean;
}

export function DateRangePicker({
  startDate,
  endDate,
  onStartDateChange,
  onEndDateChange,
  startError,
  endError,
  disabled,
}: DateRangePickerProps) {
  const formatForInput = (date: Date | undefined): string => {
    if (!date) return "";
    return format(date, "yyyy-MM-dd");
  };

  const parseFromInput = (value: string): Date | undefined => {
    if (!value) return undefined;
    return new Date(value + "T00:00:00");
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label htmlFor="startDate" className="label">
            Start Date
          </label>
          <input
            type="date"
            id="startDate"
            value={formatForInput(startDate)}
            onChange={(e) => onStartDateChange(parseFromInput(e.target.value))}
            disabled={disabled}
            className={cn(
              "input",
              startError &&
                "border-red-500 focus:border-red-500 focus:ring-red-500"
            )}
          />
          {startError && <p className="text-sm text-red-600">{startError}</p>}
        </div>

        <div className="space-y-1">
          <label htmlFor="endDate" className="label">
            End Date
          </label>
          <input
            type="date"
            id="endDate"
            value={formatForInput(endDate)}
            onChange={(e) => onEndDateChange(parseFromInput(e.target.value))}
            disabled={disabled}
            className={cn(
              "input",
              endError &&
                "border-red-500 focus:border-red-500 focus:ring-red-500"
            )}
          />
          {endError && <p className="text-sm text-red-600">{endError}</p>}
        </div>
      </div>
    </div>
  );
}
