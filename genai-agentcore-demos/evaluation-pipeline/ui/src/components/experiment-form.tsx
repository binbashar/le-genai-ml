"use client";

import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { experimentFormSchema, type ExperimentFormSchema } from "@/lib/schemas";
import { DEFAULT_MAX_LIMIT, MIN_LIMIT, MAX_LIMIT } from "@/lib/constants";
import { AgentSelector } from "./agent-selector";
import { MetricsSelector } from "./metrics-selector";
import { DateTimeRangePicker } from "./datetime-range-picker";
import { cn } from "@/lib/utils";
import type { Agent } from "@/types";
import { useMemo } from "react";

interface ExperimentFormProps {
  agents: Agent[];
  isLoadingAgents: boolean;
  onSubmit: (data: ExperimentFormSchema) => void;
  isSubmitting: boolean;
  submitError?: string;
}

export function ExperimentForm({
  agents,
  isLoadingAgents,
  onSubmit,
  isSubmitting,
  submitError,
}: ExperimentFormProps) {
  const today = useMemo(() => new Date(), []);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<ExperimentFormSchema>({
    resolver: zodResolver(experimentFormSchema),
    defaultValues: {
      agentName: "",
      experimentName: "",
      startDate: today,
      endDate: today,
      maxLimit: DEFAULT_MAX_LIMIT,
      metrics: [],
      stripContext: true,
      includeContextAsReference: false,
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          New Evaluation Experiment
        </h2>

        {submitError && (
          <div className="mb-4 p-3 rounded-md bg-red-50 border border-red-200">
            <p className="text-sm text-red-700">{submitError}</p>
          </div>
        )}

        <div className="space-y-4">
          {/* Agent Selector */}
          <Controller
            name="agentName"
            control={control}
            render={({ field }) => (
              <AgentSelector
                agents={agents}
                value={field.value}
                onChange={field.onChange}
                isLoading={isLoadingAgents}
                error={errors.agentName?.message}
                disabled={isSubmitting}
              />
            )}
          />

          {/* Experiment Name */}
          <div className="space-y-1">
            <label htmlFor="experimentName" className="label">
              Experiment Name
            </label>
            <input
              type="text"
              id="experimentName"
              placeholder="e.g., weekly-finance-eval"
              {...register("experimentName")}
              disabled={isSubmitting}
              className={cn(
                "input",
                errors.experimentName &&
                "border-red-500 focus:border-red-500 focus:ring-red-500"
              )}
            />
            {errors.experimentName && (
              <p className="text-sm text-red-600">
                {errors.experimentName.message}
              </p>
            )}
          </div>

          {/* Date Range */}
          <Controller
            name="startDate"
            control={control}
            render={({ field: startField }) => (
              <Controller
                name="endDate"
                control={control}
                render={({ field: endField }) => (
                  <div className="space-y-1">
                    <DateTimeRangePicker
                      startDate={startField.value}
                      endDate={endField.value}
                      onRangeChange={(start, end) => {
                        console.log("Date Range Changed:", {
                          start: start.toISOString(),
                          end: end.toISOString(),
                          localStart: start.toString(),
                          localEnd: end.toString()
                        });
                        startField.onChange(start);
                        endField.onChange(end);
                      }}
                      disabled={isSubmitting}
                    />
                    {(errors.startDate || errors.endDate) && (
                      <p className="text-sm text-red-600">
                        {errors.startDate?.message || errors.endDate?.message}
                      </p>
                    )}
                  </div>
                )}
              />
            )}
          />

          {/* Max Limit */}
          <div className="space-y-1">
            <label htmlFor="maxLimit" className="label">
              Max Prompts to Evaluate
            </label>
            <input
              type="number"
              id="maxLimit"
              min={MIN_LIMIT}
              max={MAX_LIMIT}
              {...register("maxLimit", { valueAsNumber: true })}
              disabled={isSubmitting}
              className={cn(
                "input w-32",
                errors.maxLimit &&
                "border-red-500 focus:border-red-500 focus:ring-red-500"
              )}
            />
            <p className="text-xs text-gray-500">
              {MIN_LIMIT}-{MAX_LIMIT} prompts
            </p>
            {errors.maxLimit && (
              <p className="text-sm text-red-600">{errors.maxLimit.message}</p>
            )}
          </div>

          {/* Context Handling */}
          <div className="space-y-3 pt-2 border-t border-gray-100">
            <h3 className="text-sm font-medium text-gray-900">Context Handling</h3>

            <div className="flex items-start gap-3">
              <div className="flex h-5 items-center">
                <input
                  id="stripContext"
                  type="checkbox"
                  {...register("stripContext")}
                  disabled={isSubmitting}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </div>
              <div className="text-sm">
                <label htmlFor="stripContext" className="font-medium text-gray-700 flex items-center gap-2 group cursor-pointer">
                  Focus on User Question
                  <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-100 text-gray-500 text-[10px] font-bold cursor-help group-hover:bg-gray-200 transition-colors" title="Removes system tokens, memory, and reasoning to evaluate only the user's core question.">?</span>
                </label>
                <p className="text-gray-500">Remove system tokens and memory context</p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="flex h-5 items-center">
                <input
                  id="includeContextAsReference"
                  type="checkbox"
                  {...register("includeContextAsReference")}
                  disabled={isSubmitting}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
              </div>
              <div className="text-sm">
                <label htmlFor="includeContextAsReference" className="font-medium text-gray-700 flex items-center gap-2 group cursor-pointer">
                  Include Context in Reference
                  <span className="inline-flex items-center justify-center w-4 h-4 rounded-full bg-gray-100 text-gray-500 text-[10px] font-bold cursor-help group-hover:bg-gray-200 transition-colors" title="Moves the removed context to the reference field for 'Correctness' evaluation.">?</span>
                </label>
                <p className="text-gray-500">Use removed context as reference for evaluation</p>
              </div>
            </div>
          </div>

          {/* Metrics Selector */}
          <Controller
            name="metrics"
            control={control}
            render={({ field }) => (
              <MetricsSelector
                value={field.value}
                onChange={field.onChange}
                error={errors.metrics?.message}
                disabled={isSubmitting}
              />
            )}
          />
        </div>

        {/* Submit Button */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={isSubmitting || isLoadingAgents}
            className="btn-primary w-full"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-2">
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Starting Experiment...
              </span>
            ) : (
              "Start Experiment"
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
