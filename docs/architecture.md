# Architecture

## Overview

The project is organized into API, extraction, retrieval, LLM, and
test-generation components.

The following diagram describes the intended logical workflow.
It should be updated to match the final, verified implementation.

## Logical Workflow

```mermaid
flowchart TD
    A[Feature Requirements and Documents]
    B[Flask API]
    C[Document Retrieval]
    D[Feature Extraction]
    E[Field and Constraint Extraction]
    F[Test Scenario Generation]
    G[Test Case Generation]
    H[Structured Output]
    L[LLM Client]
    DB[(Document Store)]

    A --> B
    B --> C
    DB --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H

    L -. model requests .-> D
    L -. model requests .-> E
    L -. model requests .-> F
    L -. model requests .-> G