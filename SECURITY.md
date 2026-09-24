# Security Policy

## Scope

SQL Connectome parses, translates, validates, and may route SQL-family input. Security reports are
especially important when they involve:

- authorization or read/write boundary bypass;
- SQL validation or statement-shape bypass;
- unexpected query execution during parse, translation, binding, or validation;
- filesystem, network, extension, or external-access escape from embedded validators;
- secret, credential, or connection-string exposure;
- unsafe deserialization, command execution, or code injection;
- receipt/provenance tampering;
- denial-of-service paths that bypass parser, token, AST, timeout, or row-count limits;
- dependency or GitHub Actions supply-chain compromise.

## Reporting

Do **not** open a public issue containing exploit details, credentials, secrets, or a working
proof-of-concept for an unpatched vulnerability.

Use GitHub's **Report a vulnerability** / private vulnerability reporting flow when it is enabled
for this repository.

If private vulnerability reporting is not available, open a public issue titled
`Security contact requested` containing no exploit details. A private reporting channel can then
be established before technical details are exchanged.

## Handling expectations

A report should identify the affected component or endpoint, the security boundary involved, and
the smallest reproducible conditions needed to demonstrate the issue. Please avoid testing against
systems or credentials you do not own or have permission to use.

Security fixes are subject to the same source, test, review, and exact-head verification discipline
as other changes. A passing parser or transpiler test is not by itself evidence that an execution or
authorization boundary remains safe.
