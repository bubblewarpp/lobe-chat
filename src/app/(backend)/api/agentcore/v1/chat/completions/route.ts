import {
  createCompletionId,
  getAgentCoreModelId,
  getAuthError,
  getCreatedAt,
  getRuntimeSessionId,
  invokeHarnessTextStream,
  jsonResponse,
  toAgentCorePrompt,
  validateAgentCoreEnv,
} from '../../_utils';
import type { OpenAIChatRequest } from '../../_utils';

export const runtime = 'nodejs';

const encoder = new TextEncoder();

const toSseMessage = (body: unknown) => encoder.encode(`data: ${JSON.stringify(body)}\n\n`);

const toDoneMessage = () => encoder.encode('data: [DONE]\n\n');

const createChunk = (id: string, model: string, content: string) => ({
  choices: [{ delta: { content }, finish_reason: null, index: 0 }],
  created: getCreatedAt(),
  id,
  model,
  object: 'chat.completion.chunk',
});

const createStopChunk = (id: string, model: string) => ({
  choices: [{ delta: {}, finish_reason: 'stop', index: 0 }],
  created: getCreatedAt(),
  id,
  model,
  object: 'chat.completion.chunk',
});

const createCompletion = (id: string, model: string, content: string) => ({
  choices: [
    {
      finish_reason: 'stop',
      index: 0,
      message: { content, role: 'assistant' },
    },
  ],
  created: getCreatedAt(),
  id,
  model,
  object: 'chat.completion',
});

const streamCompletion = (prompt: string, runtimeSessionId: string, id: string, model: string) =>
  new Response(
    new ReadableStream({
      async start(controller) {
        try {
          for await (const text of invokeHarnessTextStream(prompt, runtimeSessionId)) {
            controller.enqueue(toSseMessage(createChunk(id, model, text)));
          }

          controller.enqueue(toSseMessage(createStopChunk(id, model)));
          controller.enqueue(toDoneMessage());
        } catch (error) {
          const message =
            error instanceof Error ? error.message : 'AgentCore Harness invocation failed.';

          controller.enqueue(toSseMessage(createChunk(id, model, `AgentCore error: ${message}`)));
          controller.enqueue(toSseMessage(createStopChunk(id, model)));
          controller.enqueue(toDoneMessage());
        } finally {
          controller.close();
        }
      },
    }),
    {
      headers: {
        'cache-control': 'no-cache, no-transform',
        'connection': 'keep-alive',
        'content-type': 'text/event-stream; charset=utf-8',
      },
    },
  );

export const POST = async (request: Request) => {
  const authError = getAuthError(request);
  if (authError) return authError;

  const envError = validateAgentCoreEnv();
  if (envError) return envError;

  let body: OpenAIChatRequest;

  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: { message: 'Invalid JSON request body.' } }, { status: 400 });
  }

  const prompt = toAgentCorePrompt(body.messages);

  if (!prompt) {
    return jsonResponse(
      { error: { message: 'No chat message content was provided.' } },
      { status: 400 },
    );
  }

  const id = createCompletionId();
  const model = body.model || getAgentCoreModelId();
  const runtimeSessionId = getRuntimeSessionId(request, body);

  if (body.stream) return streamCompletion(prompt, runtimeSessionId, id, model);

  try {
    const chunks: string[] = [];

    for await (const text of invokeHarnessTextStream(prompt, runtimeSessionId)) {
      chunks.push(text);
    }

    return jsonResponse(createCompletion(id, model, chunks.join('')));
  } catch (error) {
    const message = error instanceof Error ? error.message : 'AgentCore Harness invocation failed.';

    return jsonResponse({ error: { message } }, { status: 502 });
  }
};
