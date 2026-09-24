export type SignalStepStatus = "current" | "attention" | "pending" | "complete";

export interface SignalStep {
  id: string;
  label: string;
  detail?: string;
  status: SignalStepStatus;
}

export function SignalLine({ steps }: { steps: readonly SignalStep[] }) {
  return (
    <ol className="ui-signal-line">
      {steps.map((step) => (
        <li
          key={step.id}
          className="ui-signal-line__step"
          data-status={step.status}
          aria-current={step.status === "current" ? "step" : undefined}
        >
          <span className="ui-signal-line__node" aria-hidden="true" />
          <div>
            <p className="ui-signal-line__label">{step.label}</p>
            {step.detail && <p className="ui-signal-line__detail">{step.detail}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
