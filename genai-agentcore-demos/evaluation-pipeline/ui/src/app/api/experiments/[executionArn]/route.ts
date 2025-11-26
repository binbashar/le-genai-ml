import { NextRequest, NextResponse } from "next/server";
import { DescribeExecutionCommand } from "@aws-sdk/client-sfn";
import { getSFNClient } from "@/lib/aws";
import type { ExecutionStatus, ExperimentResults } from "@/types";

interface RouteParams {
  params: Promise<{
    executionArn: string;
  }>;
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { executionArn } = await params;
    const decodedArn = decodeURIComponent(executionArn);

    // Validate ARN format
    if (!decodedArn.startsWith("arn:aws:states:")) {
      return NextResponse.json(
        {
          error: "ValidationError",
          message: "Invalid execution ARN format",
        },
        { status: 400 }
      );
    }

    // Get execution details
    const client = getSFNClient();
    const command = new DescribeExecutionCommand({
      executionArn: decodedArn,
    });

    const response = await client.send(command);

    // Map Step Functions status to our status type
    const status = response.status as ExecutionStatus;

    // Parse output if execution succeeded
    let results: ExperimentResults | undefined;
    if (status === "SUCCEEDED" && response.output) {
      try {
        const output = JSON.parse(response.output);
        // Step Functions output structure: { final_results: { ... } }
        if (output.final_results) {
          results = output.final_results;
        } else {
          // Handle case where output is directly the results
          results = output;
        }
      } catch (parseError) {
        console.error("Failed to parse execution output:", parseError);
      }
    }

    // Parse error if execution failed
    let error: { cause: string; error: string } | undefined;
    if (status === "FAILED" || status === "TIMED_OUT" || status === "ABORTED") {
      error = {
        cause: response.cause || "Unknown error",
        error: response.error || "ExecutionFailed",
      };
    }

    return NextResponse.json({
      status,
      startDate: response.startDate?.toISOString(),
      stopDate: response.stopDate?.toISOString(),
      results,
      error,
    });
  } catch (err) {
    console.error("Failed to get experiment status:", err);

    if (err instanceof Error) {
      if (err.name === "ExecutionDoesNotExist") {
        return NextResponse.json(
          {
            error: "NotFound",
            message: "Execution not found",
          },
          { status: 404 }
        );
      }

      if (err.name === "AccessDeniedException") {
        return NextResponse.json(
          {
            error: "AccessDenied",
            message:
              "AWS credentials lack permission to describe Step Functions execution",
          },
          { status: 403 }
        );
      }
    }

    return NextResponse.json(
      {
        error: "InternalError",
        message: "Failed to get experiment status",
      },
      { status: 500 }
    );
  }
}
