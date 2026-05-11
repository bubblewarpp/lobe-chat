import { BedrockAgentCoreClient, InvokeHarnessCommand } from '@aws-sdk/client-bedrock-agentcore';
import type { InvokeHarnessStreamOutput } from '@aws-sdk/client-bedrock-agentcore';

const DEFAULT_MODEL_ID = 'toki-chan-agentcore';

type OpenAIMessageContent =
  | string
  | Array<{
      text?: string;
      type?: string;
    }>;

export interface OpenAIMessage {
  content?: OpenAIMessageContent;
  role: string;
}

export interface OpenAIChatRequest {
  messages?: OpenAIMessage[];
  model?: string;
  stream?: boolean;
  user?: string;
}

export const getAgentCoreModelId = () => process.env.AGENTCORE_MODEL_ID || DEFAULT_MODEL_ID;

export const getCreatedAt = () => Math.floor(Date.now() / 1000);

export const createCompletionId = () => `chatcmpl-agentcore-${crypto.randomUUID()}`;

export const jsonResponse = (
  body: unknown,
  init?: { headers?: Record<string, string>; status?: number; statusText?: string },
) => {
  const headers = init?.headers
    ? {
        'content-type': 'application/json',
        ...init.headers,
      }
    : { 'content-type': 'application/json' };

  return new Response(JSON.stringify(body), {
    ...init,
    headers,
  });
};

export const getAuthError = (request: Request) => {
  const expectedToken = process.env.AGENTCORE_ADAPTER_API_KEY || process.env.OPENAI_API_KEY;

  if (!expectedToken) return;

  const authHeader = request.headers.get('authorization') || '';
  const actualToken = authHeader.replace(/^bearer\s+/i, '').trim();

  if (actualToken !== expectedToken) {
    return jsonResponse(
      { error: { message: 'Unauthorized AgentCore adapter request.' } },
      { status: 401 },
    );
  }
};

export const validateAgentCoreEnv = () => {
  const missing = [
    'AGENTCORE_HARNESS_ARN',
    'AWS_REGION',
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
  ].filter((key) => !process.env[key]);

  if (missing.length > 0) {
    return jsonResponse(
      {
        error: {
          message: `Missing required AgentCore environment variables: ${missing.join(', ')}`,
        },
      },
      { status: 500 },
    );
  }
};

const messageContentToText = (content?: OpenAIMessageContent) => {
  if (!content) return '';
  if (typeof content === 'string') return content;

  return content
    .map((part) => {
      if (part.type === 'text' || part.text) return part.text || '';
      return '';
    })
    .filter(Boolean)
    .join('\n');
};

export const toAgentCorePrompt = (messages: OpenAIMessage[] = []) => {
  return messages
    .map((message) => {
      const text = messageContentToText(message.content).trim();
      if (!text) return '';

      return `${message.role.toUpperCase()}:\n${text}`;
    })
    .filter(Boolean)
    .join('\n\n');
};

export const getRuntimeSessionId = (request: Request, body: OpenAIChatRequest) => {
  const headerSessionId =
    request.headers.get('x-agentcore-session-id') ||
    request.headers.get('x-lobe-session-id') ||
    request.headers.get('x-session-id');

  return headerSessionId || body.user || `lobe-${crypto.randomUUID()}`;
};

const getAgentCoreClient = () =>
  new BedrockAgentCoreClient({
    credentials: {
      accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
      secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!,
      sessionToken: process.env.AWS_SESSION_TOKEN,
    },
    region: process.env.AWS_REGION!,
  });

const getEventErrorMessage = (event: InvokeHarnessStreamOutput) => {
  if (event.runtimeClientError)
    return event.runtimeClientError.message || 'AgentCore runtime client error.';
  if (event.validationException)
    return event.validationException.message || 'AgentCore validation error.';
  if (event.internalServerException) {
    return event.internalServerException.message || 'AgentCore internal server error.';
  }
};

export async function* invokeHarnessTextStream(prompt: string, runtimeSessionId: string) {
  const response = await getAgentCoreClient().send(
    new InvokeHarnessCommand({
      harnessArn: process.env.AGENTCORE_HARNESS_ARN!,
      messages: [{ content: [{ text: prompt }], role: 'user' }],
      runtimeSessionId,
    }),
  );

  if (!response.stream) return;

  for await (const event of response.stream) {
    const text = event.contentBlockDelta?.delta?.text;

    if (text) {
      yield text;
      continue;
    }

    const errorMessage = getEventErrorMessage(event);
    if (errorMessage) throw new Error(errorMessage);
  }
}
