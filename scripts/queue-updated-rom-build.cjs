'use strict';

// A completed attempt can be obsolete after a source fix. Queue the updated
// recipe once; an unchanged recipe is never automatically retried in a loop.
const INPUTS = [
  '.github/workflows/rom-build.yml', 'scripts/run-github-rom-build.py',
  'scripts/build-workflow.py', 'scripts/build-ctz.py', 'scripts/source_manifest.py',
  'scripts/prepare-gsi-source.py', 'scripts/inspect-system-image.py',
  'config/source-profile.json', 'config/source-provenance.json',
  'manifest/ctz-android10.xml', 'gsi/suiram_ctz10.mk', 'gsi/ctz_locale.mk',
];

module.exports = async function queueUpdatedRecipe({ github, context, core }) {
  const run = context.payload.workflow_run;
  const { owner, repo } = context.repo;
  if (!run || run.head_repository?.full_name !== `${owner}/${repo}` ||
      run.head_branch !== 'main' || run.status !== 'completed' ||
      !['success', 'failure', 'timed_out'].includes(run.conclusion)) {
    return { status: 'ignored-event' };
  }
  if (!/^[0-9a-f]{40}$/.test(run.head_sha)) throw new Error('Invalid producer commit');
  const head = async () => (await github.rest.git.getRef({ owner, repo, ref: 'heads/main' })).data.object.sha;
  const latest = await head();
  if (!/^[0-9a-f]{40}$/.test(latest)) throw new Error('Invalid main commit');
  if (latest === run.head_sha) return { status: 'unchanged-commit' };
  const readBlob = async (path, ref) => {
    try {
      const { data } = await github.rest.repos.getContent({ owner, repo, path, ref });
      if (data.type !== 'file' || !/^[0-9a-f]{40}$/.test(data.sha)) {
        throw new Error('Expected a regular recipe file: ' + path);
      }
      return data.sha;
    } catch (error) {
      if (error.status === 404) return null;
      throw error;
    }
  };
  const cache = new Map();
  const blob = (path, ref) => {
    const key = ref + '\0' + path;
    if (!cache.has(key)) cache.set(key, readBlob(path, ref));
    return cache.get(key);
  };
  const changed = [];
  const current = [];
  for (const path of INPUTS) {
    const [before, after] = await Promise.all([blob(path, run.head_sha), blob(path, latest)]);
    if (after === null) throw new Error('Current recipe input is missing: ' + path);
    current.push(after);
    if (before !== after) changed.push(path);
  }
  if (!changed.length) return { status: 'unchanged-recipe' };
  const runs = (await github.paginate(github.rest.actions.listWorkflowRuns, {
    owner, repo, workflow_id: 'rom-build.yml', branch: 'main', per_page: 100,
  })).filter(candidate => candidate.head_branch === 'main' &&
                         candidate.head_repository?.full_name === `${owner}/${repo}`);
  if (runs.some(candidate => candidate.head_sha === latest)) {
    return { status: 'already-attempted', sha: latest };
  }
  // A documentation-only commit can move main beyond an already-running
  // corrected build. Commit identity alone would queue the same recipe again
  // when an older attempt ends. Compare every build input, including the
  // manifest, rather than treating a changed source-profile as the whole recipe.
  for (const candidate of runs) {
    if (!/^[0-9a-f]{40}$/.test(candidate.head_sha)) throw new Error('Invalid attempted commit');
    let equivalent = true;
    for (let index = 0; index < INPUTS.length; index++) {
      if (await blob(INPUTS[index], candidate.head_sha) !== current[index]) {
        equivalent = false;
        break;
      }
    }
    if (equivalent) {
      return { status: 'already-attempted-recipe', sha: latest,
               matchingCommit: candidate.head_sha, matchingRun: candidate.id };
    }
  }
  if (await head() !== latest) throw new Error('Main changed while checking the follow-up recipe');
  await github.rest.actions.createWorkflowDispatch({ owner, repo, workflow_id: 'rom-build.yml', ref: 'main' });
  core.notice(`Queued updated ROM recipe ${latest}; changed inputs: ${changed.join(', ')}`);
  return { status: 'dispatched', sha: latest, changed };
};
