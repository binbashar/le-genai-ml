import { NextRequest, NextResponse } from "next/server";
import { StartExecutionCommand } from "@aws-sdk/client-sfn";
import { getSFNClient, getStateMachineArn } from "@/lib/aws";
import { experimentInputSchema } from "@/lib/schemas";
import { z } from "zod";

export async function POST(request: NextRequest) {
  try {
    // Parse request body
    const body = await request.json();

    // Validate input
    const validated = experimentInputSchema.parse(body);

    // Build Step Functions input
    const sfnInput = {
      agent_name: validated.agent_name,
      start_date: validated.start_date,
      end_date: validated.end_date,
      limit: validated.limit,
      metrics: validated.metrics,
    };

    // Generate unique execution name
    const timestamp = Date.now();
    const executionName = `exp-${validated.agent_name.slice(0, 20)}-${timestamp}`;

    // Start Step Functions execution
    const client = getSFNClient();
    const command = new StartExecutionCommand({
      stateMachineArn: getStateMachineArn(),
      name: executionName,
      input: JSON.stringify(sfnInput),
    });

    const response = await client.send(command);

    if (!response.executionArn) {
      throw new Error("No executionArn returned from Step Functions");
    }

    return NextResponse.json({
      executionArn: response.executionArn,
      startDate: response.startDate?.toISOString(),
    });
  } catch (error) {
    console.error("Failed to start experiment:", error);

    // Handle Zod validation errors
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          error: "ValidationError",
          message: "Invalid input",
          details: error.flatten(),
        },
        { status: 400 }
      );
    }

    // Handle AWS errors
    if (error instanceof Error) {
      if (error.name === "AccessDeniedException") {
        return NextResponse.json(
          {
            error: "AccessDenied",
            message:
              "AWS credentials lack permission to start Step Functions execution",
          },
          { status: 403 }
        );
      }

      if (error.name === "StateMachineDoesNotExist") {
        return NextResponse.json(
          {
            error: "StateMachineNotFound",
            message:
              "State machine not found. Verify STATE_MACHINE_ARN is correct.",
          },
          { status: 404 }
        );
      }

      if (error.message.includes("STATE_MACHINE_ARN")) {
        return NextResponse.json(
          {
            error: "ConfigurationError",
            message: error.message,
          },
          { status: 500 }
        );
      }
    }

    return NextResponse.json(
      {
        error: "InternalError",
        message: "Failed to start experiment",
      },
      { status: 500 }
    );
  }
}
