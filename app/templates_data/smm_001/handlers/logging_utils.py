import re
import secrets
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Awaitable, Callable, ParamSpec, TypeVar

from aiogram import types

from services.logger import logger as logging

T = TypeVar("T")
P = ParamSpec("P")

FlowDecorator = Callable[[Callable[P, Awaitable[Any]]], Callable[P, Awaitable[Any]]]


def build_request_id(prefix: str, *parts: Any) -> str:
    normalized_parts: list[str] = []
    for part in parts:
        if part in (None, ""):
            continue
        value = re.sub(r"[^a-zA-Z0-9._-]+", "-", str(part)).strip("-")
        if value:
            normalized_parts.append(value[:24])

    if not normalized_parts:
        normalized_parts.append(secrets.token_hex(4))
    return f"{prefix}-{'-'.join(normalized_parts[:4])}"


@contextmanager
def log_context_scope(**context: Any):
    with logging.context(**context):
        yield


def log_duration(event_name: str, started_at: float, **fields: Any) -> None:
    logging.perf(
        event_name,
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        **fields,
    )


def _make_flow_decorator(
    service: str,
    flow: str,
    extract: Callable[[tuple, dict], tuple[tuple, dict]],
) -> FlowDecorator:
    def decorator(func: Callable[P, Awaitable[Any]]) -> Callable[P, Awaitable[Any]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> Any:
            request_id_parts, context_fields = extract(args, kwargs)
            request_id = build_request_id(f"{service}-{flow}", *request_id_parts)
            started_at = time.perf_counter()
            with logging.context(
                service=service,
                flow=flow,
                request_id=request_id,
                **context_fields,
            ):
                logging.event("flow_started", entrypoint=func.__name__)
                try:
                    result = await func(*args, **kwargs)
                    logging.event("flow_completed", entrypoint=func.__name__)
                    return result
                except Exception as exc:
                    logging.event("flow_failed", level=40, entrypoint=func.__name__, error=str(exc))
                    raise
                finally:
                    log_duration("flow_total", started_at, entrypoint=func.__name__)

        return wrapper

    return decorator


def with_message_logging(service: str, flow: str) -> FlowDecorator:
    def extract(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
        message: types.Message = args[0]  # type: ignore[assignment]
        user_id = getattr(getattr(message, "from_user", None), "id", None)
        chat = getattr(message, "chat", None)
        return (
            (user_id, chat.id if chat else None, getattr(message, "message_id", None)),
            {"user_id": user_id, "chat_type": getattr(chat, "type", None)},
        )

    return _make_flow_decorator(service, flow, extract)


def with_inline_query_logging(service: str, flow: str) -> FlowDecorator:
    def extract(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
        query: types.InlineQuery = args[0]  # type: ignore[assignment]
        user_id = getattr(getattr(query, "from_user", None), "id", None)
        return (
            (user_id, getattr(query, "id", None)),
            {"user_id": user_id, "chat_type": getattr(query, "chat_type", None)},
        )

    return _make_flow_decorator(service, flow, extract)


def with_callback_logging(service: str, flow: str) -> FlowDecorator:
    def extract(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
        call: types.CallbackQuery = args[0]  # type: ignore[assignment]
        user_id = getattr(getattr(call, "from_user", None), "id", None)
        chat = getattr(getattr(call, "message", None), "chat", None)
        return (
            (user_id, getattr(call, "id", None)),
            {
                "user_id": user_id,
                "chat_type": chat.type if chat else None,
                "inline_message_id": getattr(call, "inline_message_id", None),
            },
        )

    return _make_flow_decorator(service, flow, extract)


def with_chosen_inline_logging(service: str, flow: str) -> FlowDecorator:
    def extract(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
        result: types.ChosenInlineResult = args[0]  # type: ignore[assignment]
        user_id = getattr(getattr(result, "from_user", None), "id", None)
        return (
            (user_id, getattr(result, "result_id", None)),
            {
                "user_id": user_id,
                "inline_message_id": getattr(result, "inline_message_id", None),
            },
        )

    return _make_flow_decorator(service, flow, extract)


def with_inline_send_logging(service: str, flow: str) -> FlowDecorator:
    def extract(args: tuple, kwargs: dict) -> tuple[tuple, dict]:
        return (
            (kwargs.get("token"), kwargs.get("request_event_id")),
            {"inline_message_id": kwargs.get("inline_message_id")},
        )

    return _make_flow_decorator(service, flow, extract)
