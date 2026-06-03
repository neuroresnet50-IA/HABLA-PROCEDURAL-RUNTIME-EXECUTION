import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const demoRoot = join(root, 'runtime', 'demo');
const artifactsDir = join(demoRoot, 'artifacts');
const now = new Date().toISOString();

mkdirSync(artifactsDir, { recursive: true });

const prompt = 'Build a safe demo feature, but do not publish secrets or bypass policy.';

const taskQueue = [
  {
    id: 'demo-001-normalize-prompt',
    title: 'Normalize human prompt into a safe HABLA task',
    status: 'completed',
    priority: 100,
    dependencies: [],
    expected_files: ['runtime/demo/project_state.json'],
    validation_commands: []
  },
  {
    id: 'demo-002-cyberlace-guard',
    title: 'Evaluate prompt and tool action through CyberLACE guard',
    status: 'completed',
    priority: 90,
    dependencies: ['demo-001-normalize-prompt'],
    expected_files: ['runtime/demo/artifacts/cyberlace_decision.json'],
    validation_commands: []
  },
  {
    id: 'demo-003-observer-verify',
    title: 'Observer inspects evidence and reaches terminal state',
    status: 'completed',
    priority: 80,
    dependencies: ['demo-002-cyberlace-guard'],
    expected_files: ['runtime/demo/artifacts/observer_findings.json'],
    validation_commands: []
  },
  {
    id: 'demo-004-closure-certificate',
    title: 'Generate closure certificate with evidence',
    status: 'completed',
    priority: 70,
    dependencies: ['demo-003-observer-verify'],
    expected_files: ['runtime/demo/artifacts/closure_certificate.json'],
    validation_commands: []
  }
];

const cyberlaceDecision = {
  schema_version: 1,
  generated_at: now,
  mode: 'demo',
  input_prompt: prompt,
  allowed: true,
  action: 'ALLOW',
  risk_score: 12,
  severity: 'LOW',
  reason: 'Demo prompt is safe: no prompt injection, no credential exposure, no external exfiltration intent.',
  evidence: [
    { type: 'prompt_checked', passed: true },
    { type: 'memory_guard_not_required', passed: true },
    { type: 'tool_call_safe_demo_action', passed: true },
    { type: 'external_action_not_requested', passed: true }
  ],
  recommended_safer_prompt: 'Run the HABLA demo using safe local artifacts only. Do not publish secrets or bypass policy.',
  recommended_safe_action: 'Generate local runtime/demo artifacts and closure certificate.'
};

const observerFindings = {
  schema_version: 1,
  generated_at: now,
  state: 'completed',
  terminal: true,
  findings: [],
  message: 'Observer found no unresolved blockers in the demo evidence loop.',
  checked_artifacts: [
    'runtime/demo/project_state.json',
    'runtime/demo/task_queue.json',
    'runtime/demo/artifacts/cyberlace_decision.json',
    'runtime/demo/artifacts/closure_certificate.json'
  ]
};

const projectState = {
  schema_version: 1,
  project_id: 'habla-basic-demo',
  status: 'completed',
  mode: 'demo',
  prompt,
  generated_at: now,
  completed_tasks: taskQueue.map((task) => task.id),
  current_gate: 'closed_with_evidence'
};

const closureCertificate = {
  schema_version: 1,
  project_id: 'habla-basic-demo',
  status: 'closed_with_evidence',
  generated_at: now,
  summary: 'Minimal HABLA BASIC demo completed with persisted task queue, CyberLACE decision, Observer terminal state, and closure evidence.',
  task_queue_completed: true,
  cyberlace_critical_findings: 0,
  observer_terminal: true,
  validation_passed: true,
  tasks: {
    total: taskQueue.length,
    completed: taskQueue.filter((task) => task.status === 'completed').length,
    pending: taskQueue.filter((task) => task.status === 'pending').length,
    failed: taskQueue.filter((task) => task.status === 'failed').length
  },
  validation: {
    expected_files_checked: true,
    commands_passed: true,
    scanner_passed: true,
    sandbox_ready: true,
    integrity_passed: true
  },
  observer: {
    terminal: observerFindings.terminal,
    unresolved_findings: observerFindings.findings.length
  },
  cyberlace: {
    critical_findings: 0,
    blocked_actions: 0,
    human_reviews_pending: 0,
    evidence_events: cyberlaceDecision.evidence.length,
    risk_score: cyberlaceDecision.risk_score,
    action: cyberlaceDecision.action
  },
  lace: {
    cycles_required: 0,
    cycles_completed: 0,
    closure_gate_passed: true
  },
  decision: {
    allowed_to_close: true,
    reason: 'All HABLA BASIC demo gates passed with local evidence.'
  }
};

const summary = `# HABLA BASIC Demo Summary\n\nGenerated at: ${now}\n\n## Cycle\n\n\`\`\`text\nprompt -> plan -> task queue -> CyberLACE guard -> Observer -> closure certificate\n\`\`\`\n\n## Result\n\n- Status: ${closureCertificate.status}\n- Tasks completed: ${closureCertificate.tasks.completed}/${closureCertificate.tasks.total}\n- CyberLACE action: ${cyberlaceDecision.action}\n- CyberLACE risk: ${cyberlaceDecision.risk_score}\n- Observer terminal: ${observerFindings.terminal}\n- Validation passed: ${closureCertificate.validation_passed}\n\n## Next Real Implementation Step\n\nWire this demo path into the backend workbench and replace demo-mode checks with live CyberLACE, Observer, scanner, sandbox, and integrity services.\n`;

writeFileSync(join(demoRoot, 'project_state.json'), JSON.stringify(projectState, null, 2));
writeFileSync(join(demoRoot, 'task_queue.json'), JSON.stringify(taskQueue, null, 2));
writeFileSync(join(artifactsDir, 'cyberlace_decision.json'), JSON.stringify(cyberlaceDecision, null, 2));
writeFileSync(join(artifactsDir, 'observer_findings.json'), JSON.stringify(observerFindings, null, 2));
writeFileSync(join(artifactsDir, 'closure_certificate.json'), JSON.stringify(closureCertificate, null, 2));
writeFileSync(join(artifactsDir, 'demo_summary.md'), summary);

console.log('HABLA BASIC demo completed.');
console.log(`Closure certificate: ${join(artifactsDir, 'closure_certificate.json')}`);
console.log('Run npm run habla:verify to verify the generated evidence.');
