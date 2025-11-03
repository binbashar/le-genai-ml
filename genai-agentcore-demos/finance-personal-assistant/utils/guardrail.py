# Configure AWS clients
import boto3

bedrock_client = boto3.client("bedrock")
bedrock_runtime = boto3.client("bedrock-runtime")


def create_gambling_guardrail():
    """
    Create a production-grade guardrail to prevent gambling-related content.

    Implements AWS best practices:
    - Content policy filters (SEXUAL, VIOLENCE, HATE, INSULTS, MISCONDUCT, PROMPT_ATTACK)
    - Word policy for gambling terms + PROFANITY managed list
    - PII protection with automatic redaction (EMAIL, PHONE, NAME, ADDRESS → ANONYMIZE; SSN, CREDIT_DEBIT_CARD_NUMBER → BLOCK)
    - Contextual grounding for hallucination prevention (GROUNDING, RELEVANCE)
    - Both input and output blocking (HIGH strength)

    Returns:
        tuple: (guardrail_id, guardrail_arn) if created or found
    """
    guardrail_name = "guardrail-no-gambling-advice"

    # Check if guardrail already exists
    try:
        existing_guardrails = bedrock_client.list_guardrails()
        for guardrail in existing_guardrails.get("guardrails", []):
            if guardrail.get("name") == guardrail_name:
                print(
                    f"Guardrail '{guardrail_name}' already exists. Returning existing guardrail."
                )
                return (guardrail.get("id"), guardrail.get("arn"))
    except Exception as e:
        print(f"Error checking existing guardrails: {e}")

    # Create new guardrail with AWS best practices
    print(
        f"Creating new guardrail '{guardrail_name}' with PII protection and contextual grounding..."
    )
    response = bedrock_client.create_guardrail(
        name=guardrail_name,
        description="Prevents gambling-related content with automatic PII redaction and hallucination prevention. Follows AWS Bedrock best practices for financial advisory applications.",
        # Content Policy: Block harmful content (AWS recommended filters)
        contentPolicyConfig={
            "filtersConfig": [
                {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
                {
                    "type": "MISCONDUCT",
                    "inputStrength": "HIGH",
                    "outputStrength": "HIGH",
                },
                {
                    "type": "PROMPT_ATTACK",
                    "inputStrength": "HIGH",  # Block prompt injection attempts
                    "outputStrength": "NONE",  # Don't filter model outputs for prompt attacks
                },
            ]
        },
        # Word Policy: Block gambling-related terms
        wordPolicyConfig={
            "wordsConfig": [
                # Gambling activities
                {"text": "gambling"},
                {"text": "casino"},
                {"text": "betting"},
                {"text": "poker"},
                {"text": "blackjack"},
                {"text": "roulette"},
                {"text": "slot machine"},
                {"text": "sports betting"},
                {"text": "online gambling"},
                {"text": "gaming tables"},
                # Gambling advice
                {"text": "gambling strategy"},
                {"text": "betting tips"},
                {"text": "casino advice"},
                {"text": "poker strategy"},
                {"text": "how to gamble"},
                {"text": "gambling recommendations"},
                # Gambling-related financial terms
                {"text": "gambling winnings"},
                {"text": "betting odds"},
                {"text": "casino stocks"},
                {"text": "gambling investment"},
            ],
            "managedWordListsConfig": [
                {"type": "PROFANITY"}
            ],  # AWS-managed profanity filter
        },
        # PII Protection: Automatic redaction (AWS best practice)
        sensitiveInformationPolicyConfig={
            "piiEntitiesConfig": [
                # ANONYMIZE: Replace with placeholder tags like [EMAIL-1], [PHONE-1], [NAME-1]
                {"type": "EMAIL", "action": "ANONYMIZE"},
                {"type": "PHONE", "action": "ANONYMIZE"},
                {"type": "NAME", "action": "ANONYMIZE"},
                {"type": "ADDRESS", "action": "ANONYMIZE"},
                # BLOCK: Reject entire request/response if detected
                {"type": "US_SOCIAL_SECURITY_NUMBER", "action": "BLOCK"},
                {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
                {"type": "US_BANK_ACCOUNT_NUMBER", "action": "BLOCK"},
                {"type": "US_BANK_ROUTING_NUMBER", "action": "BLOCK"},
            ]
        },
        # Contextual Grounding: Prevent hallucinations (AWS best practice for RAG/financial apps)
        contextualGroundingPolicyConfig={
            "filtersConfig": [
                {
                    "type": "GROUNDING",  # Ensures responses are grounded in provided context
                    "threshold": 0.7,  # Block responses with grounding score below 0.7 (70%)
                },
                {
                    "type": "RELEVANCE",  # Ensures responses are relevant to the query
                    "threshold": 0.7,  # Block responses with relevance score below 0.7 (70%)
                },
            ]
        },
        # Custom messages for blocked content
        blockedInputMessaging="I apologize, but I'm not able to provide advice or information about that topic. As a financial advisor, I can help with budgeting, investing, savings, and other responsible financial planning topics. How can I assist you with your financial goals?",
        blockedOutputsMessaging="I apologize, but I cannot provide information related to that topic. For your safety and responsible financial management, please ask about other financial topics such as budgeting, investing, or savings strategies.",
    )

    print(
        f"✅ Successfully created guardrail '{guardrail_name}' with ID: {response.get('guardrailId')}"
    )
    print(
        "   - Content filters: SEXUAL, VIOLENCE, HATE, INSULTS, MISCONDUCT, PROMPT_ATTACK (all HIGH)"
    )
    print("   - Word policy: 19 gambling terms + PROFANITY managed list")
    print(
        "   - PII protection: EMAIL, PHONE, NAME, ADDRESS (ANONYMIZE); SSN, CREDIT_DEBIT_CARD_NUMBER (BLOCK)"
    )
    print("   - Contextual grounding: GROUNDING, RELEVANCE (threshold: 0.7)")

    return (response.get("guardrailId"), response.get("guardrailArn"))


def get_gambling_guardrail_id():
    """
    Get the guardrail ID for the gambling guardrail.
    Verifies the guardrail exists and is usable in Bedrock before returning its ID.

    Returns:
        str or None: The guardrail ID if found and verified, None otherwise
    """
    guardrail_name = "guardrail-no-gambling-advice"

    try:
        # First, list guardrails to find by name
        existing_guardrails = bedrock_client.list_guardrails()
        guardrail_id = None

        for guardrail in existing_guardrails.get("guardrails", []):
            if guardrail.get("name") == guardrail_name:
                guardrail_id = guardrail.get("id")
                break

        if not guardrail_id:
            print(f"Guardrail '{guardrail_name}' not found in list")
            return None

        # Verify the guardrail actually exists by fetching its details
        try:
            bedrock_client.get_guardrail(guardrailIdentifier=guardrail_id)
            print(
                f"Found and verified guardrail '{guardrail_name}' with ID: {guardrail_id}"
            )
            return guardrail_id
        except bedrock_client.exceptions.ResourceNotFoundException:
            print(
                f"Guardrail '{guardrail_name}' (ID: {guardrail_id}) was found in list but doesn't actually exist in Bedrock"
            )
            return None
        except Exception as verify_error:
            print(
                f"Error verifying guardrail '{guardrail_name}' (ID: {guardrail_id}): {verify_error}"
            )
            return None

    except Exception as e:
        print(f"Error finding guardrail: {e}")
        return None


def delete_gambling_guardrail(guardrail_id=None):
    """
    Delete the gambling guardrail by ID, or find and delete by name if no ID provided.

    Args:
        guardrail_id: The ID of the guardrail to delete (optional)

    Returns:
        bool: True if deletion was successful, False otherwise
    """
    guardrail_name = "guardrail-no-gambling-advice"

    try:
        # If no ID provided, find it by name
        if not guardrail_id:
            existing_guardrails = bedrock_client.list_guardrails()
            for guardrail in existing_guardrails.get("guardrails", []):
                if guardrail.get("name") == guardrail_name:
                    guardrail_id = guardrail.get("id")
                    break

            if not guardrail_id:
                print(f"Guardrail '{guardrail_name}' not found")
                return False

        # Delete the guardrail
        print(f"Deleting guardrail '{guardrail_name}' with ID: {guardrail_id}")
        bedrock_client.delete_guardrail(guardrailIdentifier=guardrail_id)
        print(f"Successfully deleted guardrail: {guardrail_name}")
        return True

    except Exception as e:
        print(f"Error deleting guardrail: {e}")
        return False


def create_guardrail_version(guardrail_id: str, description: str = None):
    """
    Create an immutable production version from DRAFT guardrail.

    AWS best practice: Use DRAFT for testing, create numbered versions for production.
    Numbered versions are immutable and can be used for stable deployments.

    Args:
        guardrail_id: The ID of the guardrail to version
        description: Optional description for the version (default: auto-generated)

    Returns:
        str: The version number (e.g., "1", "2") if successful, None otherwise
    """
    try:
        if not description:
            description = "Production version with PII protection, contextual grounding, and gambling content filtering"

        print(f"Creating production version for guardrail {guardrail_id}...")
        response = bedrock_client.create_guardrail_version(
            guardrailIdentifier=guardrail_id, description=description
        )

        version = response.get("version")
        print(f"✅ Successfully created guardrail version: {version}")
        print(f"   Use this version in production: guardrail_version='{version}'")
        return version

    except Exception as e:
        print(f"Error creating guardrail version: {e}")
        return None
