import {
  getRuntimeSessionId,
  invokeHarnessTextStream,
  jsonResponse,
  validateAgentCoreEnv,
} from '../../agentcore/v1/_utils';

export const runtime = 'nodejs';

const DEFAULT_INSTRUCTION =
  'You are Toki-chan, a helpful personal AI assistant with AgentCore Memory support. Help the user with general work, notes, summaries, drafts, planning, and safe memory-aware assistance. You may also help with AWS topics when asked, but do not force AWS framing. Keep answers concise, practical, and clear. Never store or expose secrets, credentials, tokens, passwords, private keys, or confidential data.';

type LiteMessage = {
  content: string;
  role: 'assistant' | 'user';
};

type LiteChatRequest = {
  context?: string;
  message?: string;
  messages?: LiteMessage[];
  sessionId?: string;
};

const encoder = new TextEncoder();

const buildPrompt = ({ context, message, messages = [] }: LiteChatRequest) => {
  const recentMessages = messages
    .slice(-8)
    .map((item) => `${item.role.toUpperCase()}:\n${item.content}`)
    .join('\n\n');

  return [
    `SYSTEM:\n${DEFAULT_INSTRUCTION}`,
    context ? `UPLOADED CONTEXT:\n${context.slice(0, 12_000)}` : '',
    recentMessages,
    message ? `USER:\n${message}` : '',
  ]
    .filter(Boolean)
    .join('\n\n');
};

export const POST = async (request: Request) => {
  const envError = validateAgentCoreEnv();
  if (envError) return envError;

  let body: LiteChatRequest;

  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: { message: 'Invalid JSON request body.' } }, { status: 400 });
  }

  const prompt = buildPrompt(body);
  if (!prompt.trim()) {
    return jsonResponse({ error: { message: 'No message was provided.' } }, { status: 400 });
  }

  const sessionId = getRuntimeSessionId(request, { user: body.sessionId });

  return new Response(
    new ReadableStream({
      async start(controller) {
        try {
          for await (const chunk of invokeHarnessTextStream(prompt, sessionId)) {
            controller.enqueue(encoder.encode(chunk));
          }
        } catch (error) {
          const message =
            error instanceof Error ? error.message : 'AgentCore Harness invocation failed.';

          controller.enqueue(encoder.encode(`\n\nAgentCore error: ${message}`));
        } finally {
          controller.close();
        }
      },
    }),
    {
      headers: {
        'cache-control': 'no-cache, no-transform',
        'content-type': 'text/plain; charset=utf-8',
      },
    },
  );
};
