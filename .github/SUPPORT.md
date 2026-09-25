# Support

Use GitHub Issues for reproducible SQL Connectome defects, dialect coverage gaps, semantic
divergences, engine-validation failures, and narrowly scoped feature requests.

Before opening an issue:

- search existing issues and pull requests for the same behavior;
- provide the smallest reproducible SQL statement or repository case;
- identify the source/target dialect and engine version when relevant;
- preserve the distinction between parse, bind, translate, validate, execute, and authorize;
- never include production credentials, connection strings, bearer tokens, or other secrets.

For security vulnerabilities, follow [SECURITY.md](../SECURITY.md) and do not publish exploit details
in a normal issue.

SQL Connectome does not currently publish a supported hosted service or production SLA. Questions
about an external deployment should identify that deployment explicitly rather than treating the
source repository as proof of runtime availability.
