# Prompting Strategy

## Objective

The system uses LLM-based processing to assist with the transformation
of application requirements into structured testing scenarios and cases.

This document describes the public-safe prompting approach. It does not
reproduce any employer-owned prompt text.

## 1. Context Preparation

Provide the model with relevant information such as:
- Feature description
- Field definitions
- Required and optional fields
- Business rules
- Constraints and validation rules
- Supporting documentation, when available

Only supply the context needed for the current task.

## 2. Scenario Generation

The model should consider relevant categories:

### Positive cases
Valid inputs and expected user journeys.

### Negative cases
Missing, malformed, invalid, or unauthorized inputs.

### Boundary cases
Values at or near defined minimums, maximums, and other limits.

### Business-rule cases
Cases that verify application-specific conditions and relationships.

Not every category applies to every feature. Avoid generating cases
that contradict the supplied requirements.

## 3. Test Case Generation

Each test case should contain a clear, reviewable structure:

- Test case identifier
- Related scenario identifier
- Objective or title
- Test type
- Preconditions
- Test steps
- Test data, where required
- Expected result

The final schema must be consistent with the public implementation.

## 4. Output Contract

Prefer machine-readable structured output over free-form prose.

After generation:
1. Parse the response.
2. Check the required fields.
3. Validate data types.
4. Check identifier uniqueness.
5. Check scenario references.
6. Reject or retry invalid output using a bounded retry policy.

Do not assume that valid JSON is necessarily a correct test case.

## 5. Reliability

Useful safeguards include:
- Clear task instructions
- Explicit output schema
- Relevant, bounded context
- Handling of empty input
- Handling of malformed output
- Automated validation
- Representative test fixtures

## 6. Evaluation

Assess output using criteria such as:
- Requirement coverage
- Correctness of expected results
- Relevance to the feature
- Positive, negative, and boundary coverage
- Duplicate-case rate
- Structural validity
- Human reviewer acceptance

## 7. Limitations

LLMs can make unsupported assumptions, miss edge cases, or generate
invalid steps and expected results. Human review and testing remain
necessary before generated cases are used in a real application.

## Intellectual Property

Only include prompts and examples that you are authorized to publish.
Use independently authored prompt templates and synthetic requirements
for the public portfolio version.