import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const certificatePath = join(root, 'runtime', 'demo', 'artifacts', 'closure_certificate.json');
const cyberlacePath = join(root, 'runtime', 'demo', 'artifacts', 'cyberlace_decision.json');
const observerPath = join(root, 'runtime', 'demo', 'artifacts', 'observer_findings.json');
const queuePath = join(root, 'runtime', 'demo', 'task_queue.json');

function readJson(path) {
  if (!existsSync(path)) {
    throw new Error(`Missing required artifact: ${path}`);
  }
  return JSON.parse(readFileSync(path, 'utf8'));
}

const certificate = readJson(certificatePath);
const cyberlace = readJson(cyberlacePath);
const observer = readJson(observerPath);
const taskQueue = readJson(queuePath);

const failures = [];

if (certificate.status !== 'closed_with_evidence') {
  failures.push(`Expected certificate status closed_with_evidence, got ${certificate.status}`);
}

if (certificate.task_queue_completed !== true) {
  failures.push('Task queue is not marked completed in closure certificate.');
}

if (certificate.validation_passed !== true) {
  failures.push('Validation did not pass in closure certificate.');
}

if (certificate.observer_terminal !== true || observer.terminal !== true) {
  failures.push('Observer is not terminal.');
}

if ((certificate.cyberlace_critical_findings ?? 0) !== 0) {
  failures.push('CyberLACE has unresolved critical findings.');
}

if (cyberlace.severity === 'CRITICAL' && cyberlace.action === 'ALLOW') {
  failures.push('Critical CyberLACE event cannot be allowed.');
}

const incomplete = taskQueue.filter((task) => task.status !== 'completed');
if (incomplete.length > 0) {
  failures.push(`Incomplete demo tasks: ${incomplete.map((task) => task.id).join(', ')}`);
}

if (failures.length) {
  console.error('HABLA BASIC demo verification failed:');
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log('HABLA BASIC demo verification passed.');
console.log(`- Status: ${certificate.status}`);
console.log(`- Tasks: ${certificate.tasks.completed}/${certificate.tasks.total}`);
console.log(`- CyberLACE: ${cyberlace.action} risk=${cyberlace.risk_score}`);
console.log(`- Observer terminal: ${observer.terminal}`);
