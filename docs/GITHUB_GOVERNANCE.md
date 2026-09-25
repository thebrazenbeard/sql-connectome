# GitHub Repository Governance

This document separates source-controlled GitHub behavior from settings that require repository
administration.

## Source-controlled enforcement

The repository carries:

- CI on pull requests and pushes to `main`;
- immutable full-SHA GitHub Action references;
- explicit least-privilege workflow permissions;
- CodeQL security scanning;
- dependency review on pull requests;
- Dependabot version-update configuration for Python, GitHub Actions, and Docker;
- scheduled newest-allowed-dependency semantic-drift qualification;
- deterministic conformance snapshot artifacts;
- security reporting policy;
- structured issue forms;
- pull request and contribution templates.

## Required repository settings

The intended administrative configuration for `main` is:

- active branch ruleset targeting the default branch;
- require a pull request before merge;
- require required status checks before merge;
- require the persisted GitHub check contexts `test`, `dependency-review`, `CodeQL`, and `snapshot`
  once each check has reported successfully at least once;
- require the pull-request branch to be up to date with `main` before merge so required checks bind
  to the current base rather than a stale merge candidate;
- block force pushes;
- block branch deletion;
- require conversation resolution before merge;
- do not require human approval while the repository has a single maintainer;
- use CODEOWNERS for review routing, not as a substitute for exact-head checks;
- do not enable automatic merge by default;
- do not configure routine ruleset bypass actors; any future bypass must be explicitly justified as a
  recovery mechanism rather than a normal merge path;
- require full-length commit SHAs for Actions when the repository setting is available;
- set default `GITHUB_TOKEN` permissions to read-only;
- enable Dependabot alerts and security updates;
- enable secret scanning and push protection;
- enable private vulnerability reporting.

Required-check names are exact persisted GitHub contexts, not necessarily the workflow/job labels
shown in source. Current ruleset readback stores four required contexts: `test`, `dependency-review`, `CodeQL`,
and `snapshot`. If GitHub changes a context name, update both the
ruleset and this contract deliberately rather than silently weakening enforcement.

## Current administrative qualification

As of 2026-09-24, repository administration has been verified through GitHub UI/API readback:

- active ruleset `main protection` targets the default branch;
- force pushes and branch deletion are blocked;
- pull requests and conversation resolution are required;
- approving-review count is zero while the repository has one maintainer;
- no routine bypass actors are configured;
- required checks use strict/current-base evaluation;
- default `GITHUB_TOKEN` permissions are read-only;
- Actions must be pinned to full-length commit SHAs;
- Dependabot alerts and Dependabot security updates are enabled;
- secret scanning and push protection are enabled;
- private vulnerability reporting is enabled;
- automatic merge remains disabled.

This section records the qualified administrative state. Runtime settings still require live GitHub
readback when currentness matters.

## Deliberately deferred

The following features are deferred until their consumer exists:

- deployment environments and deployment protection;
- release automation;
- package/container publication;
- artifact attestations and SBOM publication;
- GitHub webhooks or a GitHub App event receiver;
- merge queue;
- GitHub Pages.

Webhooks become appropriate when an external SQL Connectome component needs GitHub events in real
time. GitHub-internal repository automation should remain in Actions.

## Licensing

The repository currently has no declared license. Choosing licensing terms is a legal/business
decision and must be made explicitly before adding a LICENSE file. GitHub automation must not infer
or invent those terms.
