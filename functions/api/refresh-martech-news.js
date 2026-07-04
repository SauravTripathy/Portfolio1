const OWNER = 'SauravTripathy';
const REPO = 'Portfolio1';
const WORKFLOW_FILE = 'refresh-news.yml';
const BRANCH = 'main';

const ACTIONS_URL = `https://github.com/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_FILE}`;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

export async function onRequest(context) {
  const { request, env } = context;

  if (request.method !== 'POST') {
    return json({ error: 'Use POST.' }, 405);
  }

  const expectedRefreshKey = env.REFRESH_RUN_KEY;
  const githubToken = env.GITHUB_REFRESH_TOKEN;

  if (!expectedRefreshKey || !githubToken) {
    return json(
      {
        error:
          'Cloudflare is missing REFRESH_RUN_KEY or GITHUB_REFRESH_TOKEN.',
      },
      500
    );
  }

  const suppliedRefreshKey = request.headers.get('x-refresh-key') || '';

  if (suppliedRefreshKey !== expectedRefreshKey) {
    return json({ error: 'Unauthorized.' }, 401);
  }

  const githubResponse = await fetch(
    `https://api.github.com/repos/${OWNER}/${REPO}/actions/workflows/${WORKFLOW_FILE}/dispatches`,
    {
      method: 'POST',
      headers: {
        Accept: 'application/vnd.github+json',
        Authorization: `Bearer ${githubToken}`,
        'X-GitHub-Api-Version': '2026-03-10',
        'Content-Type': 'application/json',
        'User-Agent': 'martech-news-refresh-button',
      },
      body: JSON.stringify({
        ref: BRANCH,
      }),
    }
  );

  const responseText = await githubResponse.text();

  let githubPayload = {};
  try {
    githubPayload = responseText ? JSON.parse(responseText) : {};
  } catch {
    githubPayload = {};
  }

  if (!githubResponse.ok) {
    return json(
      {
        error: `GitHub dispatch failed with status ${githubResponse.status}.`,
        details: responseText.slice(0, 700),
      },
      502
    );
  }

  return json({
    ok: true,
    runUrl: githubPayload.html_url || ACTIONS_URL,
    workflowRunId: githubPayload.workflow_run_id || null,
    message:
      'Refresh queued. The page will update after GitHub Actions finishes and Cloudflare redeploys.',
  });
}