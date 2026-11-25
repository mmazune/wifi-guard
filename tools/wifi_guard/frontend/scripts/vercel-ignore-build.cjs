#!/usr/bin/env node
'use strict';
// Vercel Ignored Build Step (cost guard, 2026-11-26). Wired in vercel.json as  "ignoreCommand": "node scripts/vercel-ignore-build.cjs"
// (vercel.json overrides the dashboard setting; Vercel runs the command in the project's Root Directory).
// Vercel contract: exit 1 = run the build, exit 0 = skip it. ANY doubt or error builds (exit 1).
//   * production / main always builds (production deploys are never touched)
//   * backup/* branches never build
//   * a preview builds only when the branch has an open PR (VERCEL_GIT_PULL_REQUEST_ID is non-empty)
//   * a push whose changed files (since the last built commit, VERCEL_GIT_PREVIOUS_SHA) are all docs / reports / screenshots / progress notes is skipped
//   * "[deploy]" in the commit message forces a build (use it to get a preview of a branch before its PR, or of a docs-only change)
// Canonical copy: ~/.claude-router/templates/vercel-ignore-build.cjs (tested by test/vercel-ignore.test.js). Copy it verbatim, do not edit per repo.
const { spawnSync } = require('child_process');

const BUILD = 1, SKIP = 0;
const TOP_DIRS = new Set(['docs', 'reports', 'report', 'progress', 'screenshots', '.claude', '.github']);   // only at the repo top or the root directory top
const ANY_DEPTH_DIRS = new Set(['screenshots', 'screenshot']);                                                  // anywhere, unless under a served-assets dir
const SERVED = new Set(['public', 'static', 'assets']);
const ROOT_FILES = new Set(['.gitignore', '.gitattributes', 'LICENSE', 'CODEOWNERS', 'lefthook.yml']);
const UPPER_NOTE = /^[A-Z0-9_.-]+\.(md|markdown|txt|log|json)$/;                                                // README.md, H4_PROGRESS.md, BATCH_A_REPORT.json
const NOTE_WORD = /(PROGRESS|REPORT|HANDOFF|STATUS|CHANGELOG|README)/;

// path is relative to the repo top; prefix is the root directory relative to the repo top ('' or 'web/')
function isIgnorable(p, prefix = '') {
  const parts = String(p).split('/'), base = parts[parts.length - 1];
  const rel = prefix && p.startsWith(prefix) ? p.slice(prefix.length) : null;
  for (const q of rel === null ? [parts] : [parts, rel.split('/')]) {
    if (q.length > 1 && TOP_DIRS.has(q[0])) return true;
    if (q.length === 1 && (ROOT_FILES.has(q[0]) || /\.(md|markdown)$/i.test(q[0]))) return true;   // a note at the top of the repo or root directory
  }
  const dirs = parts.slice(0, -1);
  if (dirs.some((d) => SERVED.has(d))) return false;                                                // never skip files that are served as they are
  if (dirs.some((d) => ANY_DEPTH_DIRS.has(d))) return true;
  if (/\.log$/.test(base)) return true;
  if (/\.(md|markdown)$/.test(base) && UPPER_NOTE.test(base)) return true;                          // SHOUTING.md convention: a note, not site content
  if (UPPER_NOTE.test(base) && NOTE_WORD.test(base)) return true;
  return false;
}

function git(args) {
  const r = spawnSync('git', args, { encoding: 'utf8', timeout: 20000 });
  return r.status === 0 ? String(r.stdout) : null;
}

// -> {build: bool, why}
function decide(env, run = git) {
  const ref = env.VERCEL_GIT_COMMIT_REF || '';
  if (env.VERCEL_ENV === 'production' || ref === 'main' || ref === 'master') return { build: true, why: 'production / main always builds' };
  if (/^backup\//.test(ref)) return { build: false, why: 'backup/* branches never build' };
  if (/\[(deploy|vercel build|force build)\]/i.test(env.VERCEL_GIT_COMMIT_MESSAGE || '')) return { build: true, why: '[deploy] in the commit message' };
  const pr = env.VERCEL_GIT_PULL_REQUEST_ID;
  if (pr === undefined) return { build: true, why: 'no pull request information: cannot tell, building' };
  if (pr === '') return { build: false, why: `branch ${ref || '(unknown)'} has no open pull request` };
  const base = env.VERCEL_GIT_PREVIOUS_SHA || '';
  if (!/^[0-9a-f]{7,64}$/i.test(base)) return { build: true, why: 'no previous build to compare with: building' };
  if (run(['cat-file', '-e', `${base}^{commit}`]) === null) return { build: true, why: 'previous build commit is not in the clone: building' };
  const names = run(['diff', '--name-only', '-z', base, 'HEAD']);
  const top = run(['rev-parse', '--show-prefix']);
  if (names === null || top === null) return { build: true, why: 'git diff failed: building' };
  const prefix = top.trim(), files = names.split('\0').filter(Boolean);
  if (!files.length) return { build: false, why: 'nothing changed since the last build' };
  const code = files.filter((f) => !isIgnorable(f, prefix));
  if (code.length) return { build: true, why: `${code.length} file(s) need a build, e.g. ${code[0]}` };
  return { build: false, why: `only docs / reports / screenshots / notes changed (${files.length} file(s))` };
}

if (require.main === module) {
  let d;
  try { d = decide(process.env); } catch (e) { d = { build: true, why: `error: ${e && e.message}` }; }
  console.log(`vercel-ignore-build: ${d.build ? 'BUILD' : 'SKIP'}: ${d.why}`);
  process.exit(d.build ? BUILD : SKIP);
}
module.exports = { decide, isIgnorable };
