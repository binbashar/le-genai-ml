import { NextResponse } from "next/server";
import { discoverAgents } from "@/lib/ssm";

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const agents = await discoverAgents();

    if (agents.length === 0) {
      return NextResponse.json(
        {
          agents: [],
          warning:
            "No agents found in SSM. Deploy an agent first using 'agentcore launch'.",
        },
        { status: 200 }
      );
    }

    return NextResponse.json({ agents });
  } catch (error) {
    console.error("Failed to discover agents:", error);

    // Check for specific AWS errors
    if (error instanceof Error) {
      if (error.name === "AccessDeniedException") {
        return NextResponse.json(
          {
            error: "AccessDenied",
            message:
              "AWS credentials lack permission to read SSM parameters. Ensure ssm:GetParametersByPath is allowed for /agentcore/*",
          },
          { status: 403 }
        );
      }

      if (
        error.name === "CredentialsProviderError" ||
        error.message.includes("credentials")
      ) {
        return NextResponse.json(
          {
            error: "CredentialsError",
            message:
              "AWS credentials not found. Configure credentials via environment variables or ~/.aws/credentials",
          },
          { status: 401 }
        );
      }
    }

    return NextResponse.json(
      {
        error: "InternalError",
        message: "Failed to discover agents from SSM",
      },
      { status: 500 }
    );
  }
}
