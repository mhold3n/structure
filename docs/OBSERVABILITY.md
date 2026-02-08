# Observability Guide

## Tracing

We use OpenTelemetry for distributed tracing. Spans capture the lifecycle of a request from the Gateway through the Orchestrator to individual Kernels.

### Key Spans

- `gateway.request`: The incoming HTTP request.
- `orchestrator.workflow`: The execution of a full workflow.
- `orchestrator.step`: Individual steps within a workflow.
- `kernel.execute`: The execution of a specific kernel.
- `gate.check`: Policy checks.

## Metrics

(TODO: Implement metrics collection)

## Logs

Structured JSON logs are emitted to stdout and can be collected by Fluentd/Logstash.
Refer to `gateway/logging.py` for schema.
