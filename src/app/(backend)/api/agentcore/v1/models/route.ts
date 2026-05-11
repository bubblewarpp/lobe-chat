import {
  getAgentCoreModelId,
  getAuthError,
  getCreatedAt,
  jsonResponse,
  validateAgentCoreEnv,
} from '../_utils';

export const runtime = 'nodejs';

export const GET = async (request: Request) => {
  const authError = getAuthError(request);
  if (authError) return authError;

  const envError = validateAgentCoreEnv();
  if (envError) return envError;

  return jsonResponse({
    data: [
      {
        created: getCreatedAt(),
        id: getAgentCoreModelId(),
        object: 'model',
        owned_by: 'agentcore',
      },
    ],
    object: 'list',
  });
};
