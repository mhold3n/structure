from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import os


def get_tracer(name: str):
    """
    Returns a configured OpenTelemetry tracer.
    """
    # Check if a provider is already set
    if not trace.get_tracer_provider()._resource:  # simple check, might need robust check
        _setup_tracer_provider()

    return trace.get_tracer(name)


def _setup_tracer_provider():
    provider = TracerProvider()

    # Configure Exporter based on Env
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        processor = BatchSpanProcessor(OTLPSpanExporter())
    else:
        # Default to Console for local dev/test
        processor = BatchSpanProcessor(ConsoleSpanExporter())

    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
