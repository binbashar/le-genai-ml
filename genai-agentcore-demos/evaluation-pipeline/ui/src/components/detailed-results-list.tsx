"use client";

import { useState, useMemo, useEffect } from "react";
import { DetailedEvaluationResults, QuestionResult } from "@/types";
import { isNegativeMetric, normalizeScore } from "@/metrics-config";
import { MultiSelectDropdown } from "./multi-select-dropdown";
import { ScoreBadge } from "./score-badge";

interface DetailedResultsListProps {
    data: DetailedEvaluationResults;
}

type SortField = "prompt" | "score";
type SortDirection = "asc" | "desc";

export function DetailedResultsList({ data }: DetailedResultsListProps) {
    const [expandedRows, setExpandedRows] = useState<Set<number>>(new Set());
    const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);
    const [sortField, setSortField] = useState<SortField>("score");
    const [sortDirection, setSortDirection] = useState<SortDirection>("desc");

    // Get unique metrics from data
    const availableMetrics = useMemo(() => {
        const metrics = new Set<string>();
        data.questions.forEach(q => q.scores.forEach(s => metrics.add(s.metric)));
        return Array.from(metrics);
    }, [data.questions]);

    // Initialize selected metrics with all available metrics
    useEffect(() => {
        if (availableMetrics.length > 0 && selectedMetrics.length === 0) {
            setSelectedMetrics(availableMetrics);
        }
    }, [availableMetrics]);

    const formatMetricName = (name: string) => name.replace("Builtin.", "");

    // Calculate general score for a question (1-10) based on SELECTED metrics
    const calculateGeneralScore = (question: QuestionResult): number => {
        const relevantScores = question.scores.filter(s => selectedMetrics.includes(s.metric));

        if (relevantScores.length === 0) return 0;

        const totalNormalizedScore = relevantScores.reduce((sum, s) => {
            return sum + normalizeScore(s.metric, s.score);
        }, 0);

        // Average normalized score (0-1) * 10
        return (totalNormalizedScore / relevantScores.length) * 10;
    };

    // Filter and sort questions
    const filteredQuestions = useMemo(() => {
        let result = [...data.questions];

        // Filter by metric: Keep question if it has AT LEAST ONE of the selected metrics
        if (selectedMetrics.length > 0 && selectedMetrics.length < availableMetrics.length) {
            result = result.filter(q =>
                q.scores.some(s => selectedMetrics.includes(s.metric))
            );
        } else if (selectedMetrics.length === 0) {
            // If no metrics selected, show no questions (or maybe show all but with no scores? 
            // Better to show none to avoid confusion)
            return [];
        }

        // Sort
        result.sort((a, b) => {
            if (sortField === "prompt") {
                const cmp = a.prompt.localeCompare(b.prompt);
                return sortDirection === "asc" ? cmp : -cmp;
            } else {
                // Sort by general score (calculated based on selected metrics)
                const scoreA = calculateGeneralScore(a);
                const scoreB = calculateGeneralScore(b);
                return sortDirection === "asc" ? scoreA - scoreB : scoreB - scoreA;
            }
        });

        return result;
    }, [data.questions, selectedMetrics, availableMetrics.length, sortField, sortDirection]);

    const toggleRow = (index: number) => {
        const newExpanded = new Set(expandedRows);
        if (newExpanded.has(index)) {
            newExpanded.delete(index);
        } else {
            newExpanded.add(index);
        }
        setExpandedRows(newExpanded);
    };

    const metricOptions = availableMetrics.map(m => ({
        label: formatMetricName(m),
        value: m
    }));

    return (
        <div className="space-y-6">
            {/* Filters */}
            <div className="flex flex-wrap gap-4 p-4 bg-gray-50 rounded-lg items-end">
                <div className="w-64">
                    <MultiSelectDropdown
                        label="Metrics"
                        options={metricOptions}
                        selected={selectedMetrics}
                        onChange={setSelectedMetrics}
                    />
                </div>

                <div className="flex items-center gap-2 mb-1">
                    <label className="text-sm font-medium text-gray-700">Sort:</label>
                    <select
                        value={`${sortField} -${sortDirection} `}
                        onChange={(e) => {
                            const [field, dir] = e.target.value.split("-");
                            setSortField(field as SortField);
                            setSortDirection(dir as SortDirection);
                        }}
                        className="text-sm border border-gray-300 rounded-md px-2 py-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                        <option value="score-desc">Score (High to Low)</option>
                        <option value="score-asc">Score (Low to High)</option>
                        <option value="prompt-asc">Prompt (A-Z)</option>
                        <option value="prompt-desc">Prompt (Z-A)</option>
                    </select>
                </div>

                <div className="text-sm text-gray-500 ml-auto mb-2">
                    Showing {filteredQuestions.length} of {data.questions.length} questions
                </div>
            </div>

            {/* Questions List */}
            <div className="space-y-3">
                {filteredQuestions.map((question, index) => (
                    <QuestionCard
                        key={index}
                        question={question}
                        isExpanded={expandedRows.has(index)}
                        onToggle={() => toggleRow(index)}
                        formatMetricName={formatMetricName}
                        generalScore={calculateGeneralScore(question)}
                        selectedMetrics={selectedMetrics}
                    />
                ))}
            </div>

            {filteredQuestions.length === 0 && (
                <div className="text-center py-8 text-gray-500">
                    No questions match the current filters
                </div>
            )}
        </div>
    );
}

interface QuestionCardProps {
    question: QuestionResult;
    isExpanded: boolean;
    onToggle: () => void;
    formatMetricName: (name: string) => string;
    generalScore: number;
    selectedMetrics: string[];
}

function QuestionCard({
    question,
    isExpanded,
    onToggle,
    formatMetricName,
    generalScore,
    selectedMetrics
}: QuestionCardProps) {
    const [showReasoning, setShowReasoning] = useState(false);

    const truncate = (text: string, maxLength: number) => {
        if (!text) return "";
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + "...";
    };



    // Filter scores to display based on selected metrics
    const displayScores = question.scores.filter(s => selectedMetrics.includes(s.metric));

    return (
        <div className="border rounded-lg overflow-hidden bg-white shadow-sm">
            {/* Header */}
            <div
                className="p-4 cursor-pointer hover:bg-gray-50"
                onClick={onToggle}
            >
                <div className="flex items-start gap-3">
                    <span className="text-gray-400 mt-1">
                        {isExpanded ? "▼" : "▶"}
                    </span>
                    <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-start">
                            <div className="text-sm font-medium text-gray-900">
                                Q: {question.prompt ? (isExpanded ? question.prompt : truncate(question.prompt, 100)) : <span className="text-gray-400 italic">No prompt available</span>}
                            </div>
                            {displayScores.length > 0 && (
                                <div className="ml-4">
                                    <ScoreBadge score={generalScore} />
                                </div>
                            )}
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                            A: {question.response ? (isExpanded ? question.response : truncate(question.response, 150)) : <span className="text-gray-400 italic">No response available</span>}
                        </div>
                    </div>
                </div>

                {/* Scores Pills */}
                <div className="flex flex-wrap gap-2 mt-3 ml-6">
                    {displayScores.length > 0 ? (
                        displayScores.map((score, idx) => (
                            <MetricPill
                                key={idx}
                                score={score.score}
                                metric={score.metric}
                                formatMetricName={formatMetricName}
                            />
                        ))
                    ) : (
                        <span className="text-xs text-gray-400 italic">No scores available for selected metrics</span>
                    )}
                </div>
            </div>

            {/* Expanded Reasoning */}
            {isExpanded && (
                <div className="border-t bg-gray-50 p-4">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            setShowReasoning(!showReasoning);
                        }}
                        className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                        {showReasoning ? "▼ Hide Reasoning" : "▶ Show Reasoning"}
                    </button>

                    {showReasoning && (
                        <div className="mt-3 space-y-3">
                            {displayScores.map((score, idx) => (
                                <div key={idx} className="bg-white p-3 rounded border">
                                    <div className="flex items-center gap-2 mb-2">
                                        <MetricPill
                                            score={score.score}
                                            metric={score.metric}
                                            formatMetricName={formatMetricName}
                                        />
                                    </div>
                                    <p className="text-sm text-gray-700 whitespace-pre-wrap">
                                        {score.reasoning || "No reasoning provided"}
                                    </p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

function MetricPill({ score, metric, formatMetricName }: { score: number, metric: string, formatMetricName: (n: string) => string }) {
    const normalized = normalizeScore(metric, score);
    const percentage = Math.round(score * 100);

    // Determine colors based on normalized score (goodness)
    let colorClass = "text-red-800 border-red-200";
    let bgClass = "bg-red-50";
    let progressClass = "bg-red-200";

    if (normalized >= 0.8) {
        colorClass = "text-green-800 border-green-200";
        bgClass = "bg-green-50";
        progressClass = "bg-green-200";
    } else if (normalized >= 0.5) {
        colorClass = "text-yellow-800 border-yellow-200";
        bgClass = "bg-yellow-50";
        progressClass = "bg-yellow-200";
    }

    // For 0% and 100%, use solid background
    if (percentage === 0 || percentage === 100) {
        return (
            <span className={`text - xs px - 2 py - 1 rounded - full font - medium border ${colorClass} ${bgClass} `}>
                {formatMetricName(metric)}: {percentage}%
            </span>
        );
    }

    // For other values, use progress bar background
    return (
        <div className={`relative text - xs rounded - full font - medium border overflow - hidden ${colorClass} ${bgClass} `}>
            {/* Progress Bar Background */}
            <div
                className={`absolute top - 0 left - 0 h - full ${progressClass} opacity - 50`}
                style={{ width: `${percentage}% ` }}
            />

            {/* Content */}
            <div className="relative px-2 py-1 z-10">
                {formatMetricName(metric)}: {percentage}%
            </div>
        </div>
    );
}
