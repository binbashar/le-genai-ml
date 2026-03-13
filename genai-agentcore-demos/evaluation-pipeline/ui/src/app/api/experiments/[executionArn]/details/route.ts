import { NextRequest, NextResponse } from "next/server";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { SFNClient, DescribeExecutionCommand } from "@aws-sdk/client-sfn";

const s3Client = new S3Client({ region: process.env.AWS_REGION || "us-west-2" });
const sfnClient = new SFNClient({ region: process.env.AWS_REGION || "us-west-2" });

interface QuestionResult {
    prompt: string;
    response: string;
    scores: { metric: string; score: number; reasoning: string }[];
}

export async function GET(
    request: NextRequest,
    props: { params: Promise<{ executionArn: string }> }
) {
    try {
        const params = await props.params;
        const decodedArn = decodeURIComponent(params.executionArn);

        // 1. Get execution output to find S3 URIs
        const execution = await sfnClient.send(
            new DescribeExecutionCommand({ executionArn: decodedArn })
        );

        if (execution.status !== "SUCCEEDED" || !execution.output) {
            return NextResponse.json(
                { error: "Execution not completed or no output" },
                { status: 400 }
            );
        }

        const output = JSON.parse(execution.output);
        const finalResults = output.final_results || output;
        const outputFiles = finalResults.results?.output_files || [];

        // 2. Fetch JSONL files from S3
        const questions: QuestionResult[] = [];

        for (const s3Uri of outputFiles) {
            if (!s3Uri.endsWith('.jsonl')) continue;

            // Parse s3://bucket/key format
            const match = s3Uri.match(/^s3:\/\/([^\/]+)\/(.+)$/);
            if (!match) continue;

            const [, bucket, key] = match;

            const response = await s3Client.send(
                new GetObjectCommand({ Bucket: bucket, Key: key })
            );

            const body = await response.Body?.transformToString();
            if (!body) continue;

            // Parse JSONL (newline-delimited JSON)
            const lines = body.trim().split('\n');
            for (const line of lines) {
                try {
                    const record = JSON.parse(line);
                    // console.log("Parsed record:", JSON.stringify(record, null, 2));

                    let scores = [];

                    // Try standard format
                    if (record.evaluationResults?.[0]?.metricResults) {
                        scores = record.evaluationResults[0].metricResults.map(
                            (m: any) => ({
                                metric: m.name,
                                score: m.score,
                                reasoning: m.reasoning || ""
                            })
                        );
                    }
                    // Try alternative format (e.g. flat evaluations list)
                    else if (record.evaluations) {
                        scores = record.evaluations.map((m: any) => ({
                            metric: m.name || m.metric,
                            score: m.score || m.value,
                            reasoning: m.reasoning || m.explanation || ""
                        }));
                    }
                    // Try automatedEvaluationResult format (Bedrock automated evaluation output)
                    else if (record.automatedEvaluationResult?.scores) {
                        scores = record.automatedEvaluationResult.scores.map((m: any) => ({
                            metric: m.metricName,
                            score: m.result,
                            reasoning: m.evaluatorDetails?.[0]?.explanation || ""
                        }));
                    }
                    // Try another alternative (metric_results at top level)
                    else if (record.metric_results) {
                        scores = record.metric_results.map((m: any) => ({
                            metric: m.name,
                            score: m.score,
                            reasoning: m.reasoning || ""
                        }));
                    }

                    const prompt = record.prompt ||
                        record.input ||
                        record.question ||
                        record.user_input ||
                        record.inputRecord?.prompt ||
                        "";

                    const response = record.modelResponses?.[0]?.response ||
                        record.response ||
                        record.output ||
                        record.model_output ||
                        record.answer ||
                        record.inputRecord?.modelResponses?.[0]?.response ||
                        "";

                    questions.push({
                        prompt,
                        response,
                        scores
                    });
                } catch (e) {
                    console.error("Failed to parse JSONL line:", e);
                }
            }
        }

        return NextResponse.json({
            summary: {
                job_arn: finalResults.job_arn,
                job_name: finalResults.job_name,
                agent_name: finalResults.agent_name,
                metrics: finalResults.results?.metrics || [],
                input_configuration: JSON.parse(execution.input || "{}")
            },
            questions
        });

    } catch (error) {
        console.error("Error fetching detailed results:", error);
        return NextResponse.json(
            { error: "Failed to fetch detailed results" },
            { status: 500 }
        );
    }
}
