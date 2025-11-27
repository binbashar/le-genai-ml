export const NEGATIVE_METRICS = [
    "Builtin.Stereotyping",
    "Builtin.Harmfulness",
    "Builtin.Refusal",
    "Stereotyping",
    "Harmfulness",
    "Refusal"
];

export function isNegativeMetric(metricName: string): boolean {
    return NEGATIVE_METRICS.some(m => metricName.includes(m));
}

export function normalizeScore(metricName: string, score: number): number {
    if (isNegativeMetric(metricName)) {
        return 1 - score;
    }
    return score;
}
