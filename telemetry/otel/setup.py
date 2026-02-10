import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, ConsoleMetricExporter
from opentelemetry.sdk.resources import Resource


def setup_telemetry(service_name: str, version: str = "0.1.0"):
    """
    Initialize OpenTelemetry SDK.
    """
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": version,
        }
    )

    # TRACING
    trace_provider = TracerProvider(resource=resource)

    # In production, swap ConsoleSpanExporter with OTLPSpanExporter
    processor = BatchSpanProcessor(ConsoleSpanExporter())
    trace_provider.add_span_processor(processor)

    trace.set_tracer_provider(trace_provider)

    # METRICS
    metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])

    metrics.set_meter_provider(meter_provider)

    return trace.get_tracer(service_name), metrics.get_meter(service_name)
