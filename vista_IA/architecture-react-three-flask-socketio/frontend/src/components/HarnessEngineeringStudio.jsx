import { useEffect, useMemo, useState } from "react";

const SCENARIO_LABELS = {
  "obfuscated-secret": "Secretos ofuscados",
  "external-login": "Login externo",
  "prompt-injection-readme": "Prompt injection README",
  "payment-data": "Banco + CVV + PIN",
  "multi-provider-token": "Tokens multi-proveedor",
};

const INTENSITY_LABELS = {
  baseline: "Baseline",
  hard: "Hard",
  extreme: "Extreme",
};

function compactId(value) {
  return String(value || "")
    .trim()
    .replace(/[^A-Za-z0-9_.-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 90);
}

function statusText(result) {
  if (!result) return "Sin corrida";
  if (result.passed === true) return "PASSED";
  if (result.passed === false) return "FAILED";
  return "RUNNING";
}

function resultClass(result) {
  if (!result) return "is-idle";
  if (result.passed === true) return "is-passed";
  if (result.passed === false) return "is-failed";
  return "is-running";
}

function shortValue(value, fallback = "-") {
  if (value === null || value === undefined || value === "") return fallback;
  return String(value);
}

function setHarnessTrainingAutomation(active, detail = {}) {
  window.dispatchEvent(new CustomEvent("habla:harness-training-automation", {
    detail: {
      active: Boolean(active),
      autoAcceptSafeAlternative: Boolean(active),
      ...detail,
    },
  }));
}

export default function HarnessEngineeringStudio({ socketUrl = "", onClose }) {
  const [scenario, setScenario] = useState("obfuscated-secret");
  const [caseId, setCaseId] = useState("");
  const [campaignId, setCampaignId] = useState("");
  const [cycles, setCycles] = useState(50);
  const [taskDelaySeconds, setTaskDelaySeconds] = useState(8);
  const continuous = false;
  const [autopilotRunId, setAutopilotRunId] = useState("");
  const [intensity, setIntensity] = useState("hard");
  const [objective, setObjective] = useState("Entrenamiento autonomo de seguridad operacional para agentes IA.");
  const [summary, setSummary] = useState({ scenarios: [], intensities: [], cases: [], reports: [], checkpoints: [], campaigns: [], memory: null });
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [running, setRunning] = useState(false);
  const [autopilotRunning, setAutopilotRunning] = useState(false);
  const [result, setResult] = useState(null);
  const [autopilotResult, setAutopilotResult] = useState(null);
  const [status, setStatus] = useState("");
  const [artifact, setArtifact] = useState(null);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const [learningStatus, setLearningStatus] = useState(null);
  const [learningActionStatus, setLearningActionStatus] = useState("");

  const scenarios = useMemo(() => {
    const values = Array.isArray(summary.scenarios) && summary.scenarios.length ? summary.scenarios : Object.keys(SCENARIO_LABELS);
    return values.filter(Boolean);
  }, [summary.scenarios]);

  const intensities = useMemo(() => {
    const values = Array.isArray(summary.intensities) && summary.intensities.length ? summary.intensities : Object.keys(INTENSITY_LABELS);
    return values.filter(Boolean);
  }, [summary.intensities]);

  async function loadSummary() {
    setLoadingSummary(true);
    try {
      const response = await fetch(`${socketUrl}/api/harness/training/summary`);
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "training_summary_failed");
      }
      setSummary({
        scenarios: Array.isArray(payload.scenarios) ? payload.scenarios : [],
        intensities: Array.isArray(payload.intensities) ? payload.intensities : [],
        cases: Array.isArray(payload.cases) ? payload.cases : [],
        reports: Array.isArray(payload.reports) ? payload.reports : [],
        checkpoints: Array.isArray(payload.checkpoints) ? payload.checkpoints : [],
        campaigns: Array.isArray(payload.campaigns) ? payload.campaigns : [],
        memory: payload.memory || null,
        safetyLearning: payload.safetyLearning || null,
      });
      setLearningStatus(payload.safetyLearning || null);
    } catch (error) {
      setStatus(error?.message || "No se pudo cargar Harness Engineering Studio.");
    } finally {
      setLoadingSummary(false);
    }
  }

  useEffect(() => {
    loadSummary();
  }, []);

  async function runScenario(event) {
    event.preventDefault();
    const normalizedCaseId = compactId(caseId);
    setRunning(true);
    setArtifact(null);
    setStatus("Ejecutando caso manual CyberLACE...");
    try {
      const response = await fetch(`${socketUrl}/api/harness/training/generate-run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario, caseId: normalizedCaseId || undefined }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "training_run_failed");
      }
      setResult(payload.result || payload);
      setLearningStatus(payload.safetyLearning?.status || payload.summary?.safetyLearning || payload.safetyLearning || null);
      setStatus(payload?.result?.passed ? "Caso generado y validado." : "Caso generado con fallas. Revisa el reporte.");
      await loadSummary();
    } catch (error) {
      setStatus(error?.message || "No se pudo ejecutar el entrenamiento.");
      setResult({ passed: false, failures: [error?.message || "training_run_failed"] });
    } finally {
      setRunning(false);
    }
  }

  async function wait(ms) {
    await new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function runAutopilot(event) {
    event.preventDefault();
    const requestedTasks = Math.max(1, Math.min(Number(cycles) || 1, 1000));
    const requestedDelaySeconds = Math.max(1, Math.min(Number(taskDelaySeconds) || 8, 300));
    if (autopilotRunning && autopilotRunId) {
      setStatus("Solicitando detencion del loop autonomo...");
      try {
        await fetch(`${socketUrl}/api/harness/training/autopilot-stop/${encodeURIComponent(autopilotRunId)}`, { method: "POST" });
      } catch (error) {
        setStatus(error?.message || "No se pudo solicitar la detencion.");
      }
      return;
    }
    setAutopilotRunning(true);
    setHarnessTrainingAutomation(true, { campaignId: compactId(campaignId) || "auto" });
    setArtifact(null);
    setStatus("Preparando loop autonomo y agente generador...");
    setAutopilotResult({
      status: "queued",
      phase: "queued",
      message: "Preparando agente generador, memoria y cola de ciclos.",
      campaignId: compactId(campaignId) || "auto",
      cycles: requestedTasks,
      requestedTasks,
      taskDelaySeconds: requestedDelaySeconds,
      delayRemainingSeconds: 0,
      continuous: false,
      results: [],
      steps: [
        { phase: "queued", message: "Campana creada en UI; esperando aceptacion del backend.", status: "running" },
      ],
    });
    try {
      const response = await fetch(`${socketUrl}/api/harness/training/autopilot-start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          campaignId: compactId(campaignId) || undefined,
          cycles: requestedTasks,
          taskDelaySeconds: requestedDelaySeconds,
          continuous: false,
          intensity,
          objective,
        }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "training_autopilot_start_failed");
      }

      let currentRun = payload.run;
      setAutopilotRunId(currentRun?.runId || "");
      setHarnessTrainingAutomation(true, { runId: currentRun?.runId, campaignId: currentRun?.campaignId });
      setAutopilotResult(currentRun);
      setStatus(currentRun?.message || "Loop autonomo iniciado.");

      for (let poll = 0; poll < 10000; poll += 1) {
        if (["completed", "failed", "stopped"].includes(currentRun?.status)) break;
        await wait(900);
        const statusResponse = await fetch(`${socketUrl}/api/harness/training/autopilot-status/${encodeURIComponent(currentRun.runId)}`);
        const statusPayload = await statusResponse.json();
        if (!statusResponse.ok || statusPayload?.ok === false) {
          throw new Error(statusPayload?.message || statusPayload?.error || "training_autopilot_status_failed");
        }
        currentRun = statusPayload.run;
        setAutopilotResult(currentRun);
        if (currentRun?.learningStatus) setLearningStatus(currentRun.learningStatus);
        setStatus(currentRun?.message || "Loop autonomo activo.");
      }

      if (currentRun?.status === "completed") {
        setStatus(currentRun?.passed ? "Campana autonoma completada sin fallas." : "Campana autonoma dejo evidencia de fallas. Revisa el reporte.");
      } else if (currentRun?.status === "stopped") {
        setStatus("Loop autonomo detenido por el usuario. Evidencia y memoria guardadas.");
      } else if (currentRun?.status === "failed") {
        setStatus(currentRun?.error || "Campana autonoma fallida. Revisa evidencia.");
      } else {
        setStatus("El loop sigue en proceso; consulta el estado o reportes generados.");
      }
      await loadSummary();
    } catch (error) {
      setStatus(error?.message || "No se pudo ejecutar el loop autonomo.");
      setAutopilotResult({ passed: false, status: "failed", failures: [error?.message || "training_autopilot_failed"] });
    } finally {
      setHarnessTrainingAutomation(false);
      setAutopilotRunning(false);
      setAutopilotRunId("");
    }
  }

  async function refreshSafetyLearning() {
    try {
      const response = await fetch(`${socketUrl}/api/harness/safety-learning/status`);
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "safety_learning_status_failed");
      }
      setLearningStatus(payload);
      setLearningActionStatus("Safety Learning Core actualizado.");
    } catch (error) {
      setLearningActionStatus(error?.message || "No se pudo actualizar Safety Learning Core.");
    }
  }

  async function sendSafetyFeedback(label) {
    const experienceId = learningStatus?.lastExperience?.id || learningStatus?.model?.lastExperienceId || "";
    setLearningActionStatus("Registrando feedback humano...");
    try {
      const response = await fetch(`${socketUrl}/api/harness/safety-learning/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ experienceId, label, source: "harness-ui" }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "safety_feedback_failed");
      }
      setLearningStatus(payload.status || null);
      setLearningActionStatus(`Feedback registrado: ${label}`);
    } catch (error) {
      setLearningActionStatus(error?.message || "No se pudo registrar feedback.");
    }
  }

  async function queueSafetyRepair() {
    setLearningActionStatus("Registrando solicitud de reparacion gobernada...");
    try {
      const response = await fetch(`${socketUrl}/api/harness/safety-learning/repair-request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          instruction: "Reparacion gobernada: revisar experiencia, parchear con worker autorizado, ejecutar build/tests/harness y dejar checkpoint.",
        }),
      });
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "safety_repair_request_failed");
      }
      setLearningStatus(payload.status || null);
      setLearningActionStatus(`Reparacion en cola: ${payload.repairRequest?.id || "registrada"}`);
    } catch (error) {
      setLearningActionStatus(error?.message || "No se pudo registrar reparacion.");
    }
  }

  async function loadArtifact(path) {
    if (!path) return;
    setArtifactLoading(true);
    try {
      const response = await fetch(`${socketUrl}/api/harness/training/artifact?path=${encodeURIComponent(path)}`);
      const payload = await response.json();
      if (!response.ok || payload?.ok === false) {
        throw new Error(payload?.message || payload?.error || "artifact_load_failed");
      }
      setArtifact(payload);
    } catch (error) {
      setArtifact({ path, content: error?.message || "No se pudo cargar el artefacto." });
    } finally {
      setArtifactLoading(false);
    }
  }

  const latestReports = summary.reports || [];
  const latestCheckpoints = summary.checkpoints || [];
  const latestCases = summary.cases || [];
  const latestCampaigns = summary.campaigns || [];
  const campaignResults = Array.isArray(autopilotResult?.results) ? autopilotResult.results : [];
  const autopilotSteps = Array.isArray(autopilotResult?.steps) ? autopilotResult.steps : [];
  const learningRecommendation = learningStatus?.recommendation || learningStatus?.model?.lastRecommendation || null;
  const learningLast = learningStatus?.lastExperience || null;

  return (
    <section className="harness-studio-panel" aria-label="Harness Engineering Studio">
      <header className="harness-studio-header">
        <div>
          <span>HARNESS ENGINEERING STUDIO</span>
          <h2>CyberLACE Autonomous Security Training Loop</h2>
        </div>
        <button type="button" onClick={onClose}>Cerrar</button>
      </header>

      <div className="harness-studio-autopilot">
        <form className="harness-studio-runner" onSubmit={runAutopilot}>
          <label>
            <span>Campana ID opcional</span>
            <input value={campaignId} onChange={(event) => setCampaignId(event.target.value)} placeholder="campana-red-team-001" disabled={autopilotRunning} />
          </label>
          <label>
            <span>Tareas end-to-end del loop</span>
            <input
              type="number"
              min="1"
              max="1000"
              value={cycles}
              onChange={(event) => setCycles(event.target.value)}
              disabled={autopilotRunning}
              placeholder="50"
            />
          </label>
          <label>
            <span>Pausa entre tareas (segundos)</span>
            <input
              type="number"
              min="1"
              max="300"
              value={taskDelaySeconds}
              onChange={(event) => setTaskDelaySeconds(event.target.value)}
              disabled={autopilotRunning}
              placeholder="8"
            />
          </label>
          <div className="harness-studio-loop-note">
            El boton ejecuta exactamente este numero de tareas, espera la pausa configurada entre una y otra, y se detiene solo.
          </div>
          <label>
            <span>Intensidad</span>
            <select value={intensity} onChange={(event) => setIntensity(event.target.value)} disabled={autopilotRunning}>
              {intensities.map((item) => <option key={item} value={item}>{INTENSITY_LABELS[item] || item}</option>)}
            </select>
          </label>
          <label className="harness-studio-wide-field">
            <span>Objetivo del agente generador</span>
            <textarea value={objective} onChange={(event) => setObjective(event.target.value)} rows={3} disabled={autopilotRunning} />
          </label>
          <button type="submit" disabled={running}>{autopilotRunning ? "Detener loop autonomo" : "Iniciar loop autonomo"}</button>
          <small>Un agente fabrica cada caso, lo pasa al runtime real, evalua resultado, guarda evidencia y usa la memoria para el siguiente ciclo.</small>
          <small className="harness-studio-autoaccept-note">Durante el loop, HABLA autoacepta solo la alternativa segura; la accion peligrosa permanece bloqueada.</small>
        </form>

        <div className={`harness-studio-result ${resultClass(autopilotResult)}`}>
          <span>Autopilot</span>
          <strong>{statusText(autopilotResult)}</strong>
          <p>{status || "Listo para iniciar entrenamiento autonomo."}</p>
          <div className="harness-studio-metrics">
            <code>campaign={shortValue(autopilotResult?.campaignId)}</code>
            <code>tasks={shortValue(autopilotResult?.requestedTasks || autopilotResult?.cycles, 0)}</code>
            <code>pause={shortValue(autopilotResult?.delayRemainingSeconds ?? autopilotResult?.taskDelaySeconds, 0)}s</code>
            <code>passed={campaignResults.filter((item) => item.passed).length}/{campaignResults.length}</code>
            <code>memory={shortValue(autopilotResult?.memory || summary.memory?.path)}</code>
          </div>
          {autopilotSteps.length ? (
            <ol className="harness-studio-step-list">
              {autopilotSteps.slice(-10).map((item, index) => (
                <li key={`${item.at || index}-${item.phase}`}>
                  <strong>{item.cycle ? `Ciclo ${item.cycle}` : "Sistema"} · {item.phase}</strong>
                  <span>{item.message}</span>
                </li>
              ))}
            </ol>
          ) : null}
          {campaignResults.length ? (
            <ol className="harness-studio-cycle-list">
              {campaignResults.map((item) => (
                <li key={`${item.cycle}-${item.case}`}>
                  <strong>{item.cycle}. {item.scenario}</strong>
                  <span>{item.passed ? "PASSED" : "FAILED"} · {item.status} · {item.runtimeAction}</span>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      </div>

      <div className="harness-studio-grid is-secondary">
        <form className="harness-studio-runner" onSubmit={runScenario}>
          <label>
            <span>Caso manual</span>
            <select value={scenario} onChange={(event) => setScenario(event.target.value)} disabled={running || autopilotRunning}>
              {scenarios.map((item) => (
                <option key={item} value={item}>{SCENARIO_LABELS[item] || item}</option>
              ))}
            </select>
          </label>
          <label>
            <span>Case ID opcional</span>
            <input value={caseId} onChange={(event) => setCaseId(event.target.value)} placeholder="auto-ui-case-001" disabled={running || autopilotRunning} />
          </label>
          <button type="submit" disabled={running || autopilotRunning}>{running ? "Ejecutando..." : "Generar y ejecutar caso"}</button>
          <small>Herramienta puntual para repetir un escenario conocido sin lanzar campana.</small>
        </form>

        <div className={`harness-studio-result ${resultClass(result)}`}>
          <span>Caso manual</span>
          <strong>{statusText(result)}</strong>
          <p>{result ? "Resultado del ultimo caso manual." : "Sin caso manual ejecutado."}</p>
          <div className="harness-studio-metrics">
            <code>status={shortValue(result?.status, "idle")}</code>
            <code>action={shortValue(result?.runtimeAction, "none")}</code>
            <code>time={shortValue(result?.elapsedSeconds)}s</code>
            <code>session={shortValue(result?.sessionId, "none")}</code>
          </div>
          {result?.failures?.length ? (
            <ul>{result.failures.map((failure) => <li key={failure}>{failure}</li>)}</ul>
          ) : null}
        </div>
      </div>

      <section className="harness-learning-panel" aria-label="Safety Learning Core">
        <div className="harness-learning-head">
          <div>
            <span>SAFETY LEARNING CORE V1</span>
            <h3>Inteligencia operativa explicable</h3>
          </div>
          <button type="button" onClick={refreshSafetyLearning}>Actualizar</button>
        </div>
        <div className="harness-learning-grid">
          <div>
            <strong>Memoria</strong>
            <code>experiences={shortValue(learningStatus?.totalExperiences || learningStatus?.model?.totalExperiences, 0)}</code>
            <code>score={shortValue(learningStatus?.model?.score, 0)}</code>
            <code>repairs={shortValue(learningStatus?.repairCount, 0)}</code>
          </div>
          <div>
            <strong>Ultima experiencia</strong>
            <code>diagnosis={shortValue(learningLast?.diagnosis, "none")}</code>
            <code>scenario={shortValue(learningLast?.scenario, "none")}</code>
            <code>action={shortValue(learningLast?.runtimeAction, "none")}</code>
          </div>
          <div className="harness-learning-wide">
            <strong>Proxima decision sugerida</strong>
            <p>{learningRecommendation?.reason || "Sin recomendacion todavia. Ejecuta un caso o campana para crear memoria."}</p>
            <div className="harness-learning-chips">
              <code>next={shortValue(learningRecommendation?.nextScenario, "none")}</code>
              <code>action={shortValue(learningRecommendation?.action, "none")}</code>
              <code>priority={shortValue(learningRecommendation?.priority, "none")}</code>
              <code>route={shortValue(learningRecommendation?.repairRoute, "none")}</code>
            </div>
          </div>
        </div>
        <div className="harness-learning-actions">
          <button type="button" onClick={() => sendSafetyFeedback("blocked_correctly")}>Bloqueo correcto</button>
          <button type="button" onClick={() => sendSafetyFeedback("false_positive")}>Falso positivo</button>
          <button type="button" onClick={() => sendSafetyFeedback("false_negative")}>Falso negativo</button>
          <button type="button" onClick={() => sendSafetyFeedback("runtime_bug")}>Bug runtime/UI</button>
          <button type="button" onClick={queueSafetyRepair}>Cola reparacion</button>
        </div>
        {learningActionStatus ? <small>{learningActionStatus}</small> : null}
      </section>

      <div className="harness-studio-artifacts">
        <section>
          <h3>Campanas</h3>
          {loadingSummary ? <p>Cargando...</p> : null}
          {latestCampaigns.slice(0, 6).map((item) => (
            <button key={item.path} type="button" onClick={() => loadArtifact(item.path)}>
              <strong>{item.name}</strong>
              <small>{item.updatedAt}</small>
            </button>
          ))}
          {summary.memory?.exists ? (
            <button type="button" onClick={() => loadArtifact(summary.memory.path)}>
              <strong>memory.json</strong>
              <small>{summary.memory.updatedAt}</small>
            </button>
          ) : null}
        </section>
        <section>
          <h3>Reportes</h3>
          {latestReports.slice(0, 6).map((item) => (
            <button key={item.path} type="button" onClick={() => loadArtifact(item.path)}>
              <strong>{item.name}</strong>
              <small>{item.updatedAt}</small>
            </button>
          ))}
        </section>
        <section>
          <h3>Checkpoints</h3>
          {latestCheckpoints.slice(0, 6).map((item) => (
            <button key={item.path} type="button" onClick={() => loadArtifact(item.path)}>
              <strong>{item.name}</strong>
              <small>{item.updatedAt}</small>
            </button>
          ))}
        </section>
        <section>
          <h3>Casos</h3>
          {latestCases.slice(0, 6).map((item) => (
            <button key={item.path} type="button" onClick={() => loadArtifact(item.path)}>
              <strong>{item.name}</strong>
              <small>{item.updatedAt}</small>
            </button>
          ))}
        </section>
      </div>

      {artifact ? (
        <section className="harness-studio-preview">
          <div>
            <strong>{artifact.path}</strong>
            <button type="button" onClick={() => setArtifact(null)}>Ocultar</button>
          </div>
          <pre>{artifactLoading ? "Cargando..." : artifact.content}</pre>
        </section>
      ) : null}
    </section>
  );
}
