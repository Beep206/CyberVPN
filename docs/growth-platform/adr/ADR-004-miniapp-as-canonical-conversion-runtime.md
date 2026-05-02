# ADR-004: Mini App as Canonical Conversion Runtime

## Status

Accepted

## Context

CyberVPN already has a Mini App baseline and wants both platform and partner-branded customer journeys to converge on one low-friction conversion surface.

## Decision

The Telegram Mini App becomes the canonical conversion runtime for CyberVPN and partner-branded Telegram entry points.

## Consequences

- Mini App must be tenant-aware from the start;
- partner-branded Mini App flows reuse the same core runtime;
- routing, payments, config delivery, and analytics must be designed for reuse.

## Alternatives Considered

- Separate CyberVPN and partner Mini App codebases
- Web-first checkout with Mini App as a thin wrapper

These were rejected because they increase fragmentation and weaken Telegram-native conversion.
