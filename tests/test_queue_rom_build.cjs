'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const queue = require('../scripts/queue-updated-rom-build.cjs');

function fixture({ changed = true, runs = [], sameHead = false, fork = false, moving = false } = {}) {
  const before = '1'.repeat(40), after = sameHead ? before : '2'.repeat(40);
  const dispatched = [];
  let reads = 0;
  const github = {
    rest: {
      git: { getRef: async () => ({ data: { object: { sha: moving && reads++ ? '3'.repeat(40) : after } } }) },
      repos: { getContent: async ({ path, ref }) => ({ data: {
        type: 'file', sha: changed && path === 'config/source-profile.json' && ref === after ? 'b'.repeat(40) : 'a'.repeat(40),
      } }) },
      actions: { listWorkflowRuns: async () => {}, createWorkflowDispatch: async args => { dispatched.push(args); } },
    },
    paginate: async () => runs,
  };
  return { args: { github, core: { notice: () => {} }, context: {
    repo: { owner: 'owner', repo: 'rom' }, payload: { workflow_run: {
      head_sha: before, head_branch: 'main', status: 'completed', conclusion: 'failure',
      head_repository: { full_name: fork ? 'another/rom' : 'owner/rom' },
    } },
  } }, dispatched, after };
}

test('a changed property recipe queues the updated build once', async () => {
  const f = fixture();
  const result = await queue(f.args);
  assert.equal(result.status, 'dispatched');
  assert.deepEqual(result.changed, ['config/source-profile.json']);
  assert.deepEqual(f.dispatched, [{ owner: 'owner', repo: 'rom', workflow_id: 'rom-build.yml', ref: 'main' }]);
});
test('same commit and documentation-only updates never retry a failed build', async () => {
  for (const options of [{ sameHead: true }, { changed: false }]) {
    const f = fixture(options);
    await queue(f.args);
    assert.equal(f.dispatched.length, 0);
  }
});
test('an existing attempt on the current recipe prevents duplicate builds', async () => {
  for (const status of ['queued', 'in_progress', 'completed']) {
    const f = fixture({ runs: [{ head_sha: '2'.repeat(40), status }] });
    assert.equal((await queue(f.args)).status, 'already-attempted');
    assert.equal(f.dispatched.length, 0);
  }
});
test('another repository cannot trigger this queue', async () => {
  const f = fixture({ fork: true });
  assert.equal((await queue(f.args)).status, 'ignored-event');
  assert.equal(f.dispatched.length, 0);
});
test('a cancelled attempt stays cancelled even if the recipe changed', async () => {
  const f = fixture();
  f.args.context.payload.workflow_run.conclusion = 'cancelled';
  assert.equal((await queue(f.args)).status, 'ignored-event');
  assert.equal(f.dispatched.length, 0);
});
test('missing or unreadable current inputs prevent a dispatch', async () => {
  for (const status of [404, 403]) {
    const f = fixture();
    f.args.github.rest.repos.getContent = async () => { throw Object.assign(new Error('unavailable'), { status }); };
    await assert.rejects(queue(f.args));
    assert.equal(f.dispatched.length, 0);
  }
});
test('a branch movement during comparison prevents a stale dispatch', async () => {
  const f = fixture({ moving: true });
  await assert.rejects(queue(f.args), /Main changed/);
  assert.equal(f.dispatched.length, 0);
});
