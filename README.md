# AI-Powered Web Test Case Generator

An LLM-powered application designed to generate structured web application
test scenarios and test cases from feature requirements, field definitions,
business rules, constraints, and supporting documentation.

> **Project status:** Portfolio preparation in progress.
> The complete workflow must be verified after missing application
> dependencies are replaced or restored.

## Problem Statement

Writing web application test scenarios and detailed test cases manually
can be time-consuming and may lead to inconsistent test coverage.

This project explores how Large Language Models (LLMs) can assist in
converting application requirements into structured, reviewable test cases.

## Intended Solution

The application is organized around the following workflow:

1. Accept feature requirements and supporting context.
2. Extract relevant application features.
3. Identify fields, constraints, and business rules.
4. Generate positive, negative, and boundary test scenarios.
5. Expand scenarios into detailed test cases.
6. Return structured output for review and further automation.

The output is intended to assist testers. Generated cases should be
reviewed and validated before use in a real testing environment.

## Key Capabilities

- LLM-assisted feature extraction
- Field and constraint analysis
- Test scenario generation
- Detailed test case generation
- Document retrieval integration
- API-based application architecture
- Structured output and prompt design

These capabilities describe the intended workflow. Only features
verified in the published implementation should be presented as completed.

## Architecture

See [Architecture Documentation](docs/architecture.md).

## Technology Stack

- Python
- Flask
- Azure OpenAI / LangChain integration
- PostgreSQL integration
- Document processing and retrieval

The exact dependencies required to run the public version will be
documented in `requirements.txt`.

## Repository Structure

```text
src/web_testcase_gen/
├── api/          # API entry point and routes
├── database/     # Document repository interface
├── extraction/   # Feature, field, and constraint extraction
├── generation/   # Test scenario and test case generation
└── llm/          # LLM client and configuration

docs/             # Architecture and prompting documentation
examples/         # Synthetic input and illustrative output
tests/            # Automated tests
screenshots/      # Application demonstrations